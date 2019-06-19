//
// Created by David Sheinberg on 2019-04-12.
//

#include <iostream>
#include <unistd.h>
#include <csignal>
#include <thread>         // std::this_thread::sleep_for
#include <chrono>         // std::chrono::seconds
#include <vector>

#include <zmq.hpp>
#include "cxxopts.hpp"

#include <sys/stat.h>
#include <syslog.h>
#include <unistd.h>

#include "Msg.hpp"	       
#include "Datapoint.hpp"
#include "DataserverClient.hpp"
#include "ZmqServer.hpp"
#include "TclInterp.hpp"
#include "TimerFD.hpp"
#include "TouchSensor.hpp"
#include "Daemonizer.hpp"


/*****************************************************************************/
/**************************** TCL bound commands *****************************/
/*****************************************************************************/

static int shutdownCmd(ClientData clientData, Tcl_Interp *interp,
                       int argc, char *argv[])
{
    bool *done = (bool *) clientData;
    *done = true;
    std::cout << "Shutting down" << std::endl;
    Tcl_AppendResult(interp, "OK", NULL);
    return TCL_OK;
}

static int sensorValuesCmd(ClientData clientData, Tcl_Interp *interp,
                           int argc, char *argv[])
{
  int sensor_id;
  auto sensors = (std::vector<TouchSensor *> *) clientData;
  if (argc < 2) {
    Tcl_AppendResult(interp, argv[0], ": sensor", NULL);
    return TCL_ERROR;
  }

  if (Tcl_GetInt(interp, argv[1], &sensor_id) != TCL_OK) return TCL_ERROR;
  if (sensor_id < 0 || sensor_id >= sensors->size()) {
    Tcl_AppendResult(interp, argv[0], ": sensor out of range", NULL);
    return TCL_ERROR;
  }

  auto s = (*sensors)[sensor_id]->strvals();
  Tcl_AppendResult(interp, s.c_str(), NULL);
  return TCL_OK;
}

static int sensorActivateCmd(ClientData clientData, Tcl_Interp *interp,
			     int argc, char *argv[])
{
  int sensor_id;
  auto sensors = (std::vector<TouchSensor *> *) clientData;
  if (argc < 2) {
    Tcl_AppendResult(interp, argv[0], ": sensor", NULL);
    return TCL_ERROR;
  }

  if (Tcl_GetInt(interp, argv[1], &sensor_id) != TCL_OK) return TCL_ERROR;
  if (sensor_id < 0 || sensor_id >= sensors->size()) {
    Tcl_AppendResult(interp, argv[0], ": sensor out of range", NULL);
    return TCL_ERROR;
  }

  (*sensors)[sensor_id]->activate();
  return TCL_OK;
}

static int sensorDeactivateCmd(ClientData clientData, Tcl_Interp *interp,
			       int argc, char *argv[])
{
  int sensor_id;
  auto sensors = (std::vector<TouchSensor *> *) clientData;
  if (argc < 2) {
    Tcl_AppendResult(interp, argv[0], ": sensor", NULL);
    return TCL_ERROR;
  }

  if (Tcl_GetInt(interp, argv[1], &sensor_id) != TCL_OK) return TCL_ERROR;
  if (sensor_id < 0 || sensor_id >= sensors->size()) {
    Tcl_AppendResult(interp, argv[0], ": sensor out of range", NULL);
    return TCL_ERROR;
  }

  (*sensors)[sensor_id]->deactivate();
  return TCL_OK;
}

static int sensorSetEmptyBaselineCmd(ClientData clientData, Tcl_Interp *interp,
				     int argc, char *argv[])
{
  int sensor_id;
  auto sensors = (std::vector<TouchSensor *> *) clientData;
  if (argc < 2) {
    Tcl_AppendResult(interp, argv[0], ": sensor", NULL);
    return TCL_ERROR;
  }

  if (Tcl_GetInt(interp, argv[1], &sensor_id) != TCL_OK) return TCL_ERROR;
  if (sensor_id < 0 || sensor_id >= sensors->size()) {
    Tcl_AppendResult(interp, argv[0], ": sensor out of range", NULL);
    return TCL_ERROR;
  }

  (*sensors)[sensor_id]->setEmptyBaseline();
  return TCL_OK;
}

static int sensorSetObjectBaselineCmd(ClientData clientData, Tcl_Interp *interp,
				     int argc, char *argv[])
{
  int sensor_id;
  auto sensors = (std::vector<TouchSensor *> *) clientData;
  if (argc < 2) {
    Tcl_AppendResult(interp, argv[0], ": sensor", NULL);
    return TCL_ERROR;
  }

  if (Tcl_GetInt(interp, argv[1], &sensor_id) != TCL_OK) return TCL_ERROR;
  if (sensor_id < 0 || sensor_id >= sensors->size()) {
    Tcl_AppendResult(interp, argv[0], ": sensor out of range", NULL);
    return TCL_ERROR;
  }

  (*sensors)[sensor_id]->setObjectBaseline();
  return TCL_OK;
}


/****************************** SIGNAL HANDLER *****************************/

// Signal hander for terminating with ctrl-c
void signal_handler(int signal)
{
    std::cout << "Shutting down..." << std::endl;
    exit(0);
}


/************************* dataserver callback *****************************/

// Called when subscribed control command is received
void process_control_command(TclInterp &tclInterp, Datapoint *dpoint)
{
    //Tcl_SetVar2(tclInterp.getInterp(), "dsVals", dpoint->varname,
	//	dpoint->toString().c_str(), TCL_GLOBAL_ONLY);
	std::string script{dpoint->varname};
	script += " ";
	script += dpoint->data;

	Tcl_EvalEx(tclInterp.getInterp(), script.c_str(), script.size(), 0);
}


/******************************************************************************/
/********************************** Main Line *********************************/
/******************************************************************************/

int main(int argc, char *argv[]) {
    std::string servername = "tcp://*:5689";
    bool push_updates_to_dataserver = true;
    bool help = false;
    int interval = 1000;
    bool daemonize = false;
    bool verbose = false;
    int nsensors = 2;		// number of sensors connected
    const char *sensor_control_prefix = "sensor:control:";

    // Control main loop
    bool m_bDone = false;

    // Parse command line options
    try {
        cxxopts::Options options("touch_sensor", "MPR121 Touch Sensor Server");
        options.add_options()
                ("h,help", "Print help", cxxopts::value<bool>(help))
                ("d,daemon", "Daemonize", cxxopts::value<bool>(daemonize))
                ("s,server", "Server name",
		 cxxopts::value<std::string>(servername))
                ("i,interval", "Interval between alarms (ms)",
		 cxxopts::value<int>(interval))
                ("n,nsensors", "Number of sensors",
		 cxxopts::value<int>(nsensors))
                ("v,verbose", "Verbose", cxxopts::value<bool>(verbose));

        auto result = options.parse(argc, argv);

        if (help) {
            std::cout << options.help({"", "Group"}) << std::endl;
            exit(0);
        }
    }
    catch (const cxxopts::OptionException &ex) {
        std::cerr << ex.what() << '\n';
        exit(0);
    }

    Daemonizer daemonizer;
    if (daemonize) daemonizer.start();

    // Install a signal handler to shutdown properly
    std::signal(SIGINT, signal_handler);

    // acquire zmq context with 3 polling items
    ZmqServer server(2);

    /// Dataserver Push Socket
    DataserverClient dserv_push_client(server.getContext(),
				  DataserverClient::DS_CLIENT_PUSH);

    /// Dataserver Socket
    //  Socket to receive subscriptions from dataserver
    DataserverClient dserv_subscriber(server.getContext(),
				      DataserverClient::DS_CLIENT_SUB);
    int dserv_msg_id = server.addItem((void *) *dserv_subscriber.getSocket());
    dserv_subscriber.subscribe(sensor_control_prefix);

    /// Timer File Descriptor
    TimerFD timerfd(interval, &server);
    int timer_msg_id = timerfd.getItemId();


    std::vector<TouchSensor *> sensors;
    for (auto i = 0; i < nsensors; i++) {
      auto sensor = new TouchSensor(i);
      sensors.push_back(sensor);
    }

    /// Tcl Interpreter
    TclInterp tclInterp(argv[0]);

    tclInterp.addCommand("sensor:control:shutdown", (Tcl_CmdProc *) shutdownCmd, &m_bDone);
    tclInterp.addCommand("sensor:control:activate", (Tcl_CmdProc *) sensorActivateCmd, &sensors);
    tclInterp.addCommand("sensor:control:deactivate", (Tcl_CmdProc *) sensorDeactivateCmd, &sensors);
    tclInterp.addCommand("sensor:control:setEmptyBaseline", (Tcl_CmdProc *) sensorSetEmptyBaselineCmd, &sensors);
    tclInterp.addCommand("sensor:control:setObjectBaseline", (Tcl_CmdProc *) sensorSetObjectBaselineCmd, &sensors);

    ///// MAIN LOOP
    while (!m_bDone) {
        server.waitForEvent();

        if (server.receivedItem(dserv_msg_id)) {
            Datapoint *controlCmd = dserv_subscriber.receiveDatapoint();
            process_control_command(tclInterp, controlCmd);
        }

        if (server.receivedItem(timer_msg_id)) {
            timerfd.process();
            int i = 0;
            for (auto sensor : sensors) {
                sensor->update();
                if (push_updates_to_dataserver) {
                    // Always push current vals
                    std::string varstr = "sensor:" + std::to_string(i) + ":vals";
                    Datapoint d{varstr.c_str(), (void *) sensor->curvals(), sensor->nchannels(),
                                TouchSensor::DATATYPE};

                    dserv_push_client.push(d);

                    // Push maxs if set to update
                    if (sensor->updateMaxs()) {
                        std::string varstr = "sensor:" + std::to_string(i) + ":maxs";
                        Datapoint d{varstr.c_str(), (void *) sensor->maxvals(), sensor->nchannels(),
                                    TouchSensor::DATATYPE};

                        dserv_push_client.push(d);
                    }

                    // Push mins if set to update
                    if (sensor->updateMins()) {
                        std::string varstr = "sensor:" + std::to_string(i) + ":mins";
                        Datapoint d{varstr.c_str(), (void *) sensor->minvals(), sensor->nchannels(),
                                    TouchSensor::DATATYPE};

                        dserv_push_client.push(d);
                    }
                i++;
                }
            }
        }
    }

    // Release sensors
    for (auto p : sensors) delete p;
    sensors.clear();
    
    // Shutdown timer
    timerfd.shutdown();

    if (verbose) std::cout << "Shutting down" << std::endl;

    if (daemonize) daemonizer.end("Closing touch_sensor");

    return 0;
}
