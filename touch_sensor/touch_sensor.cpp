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
#include "TclZMQ.hpp"
#include "TimerFD.hpp"
#include "TouchSensor.hpp"


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

static int dservSubscribeCmd(ClientData clientData, Tcl_Interp *interp,
                             int argc, char *argv[])
{
    DataserverClient *client = (DataserverClient *) clientData;
    if (argc < 2) {
        Tcl_AppendResult(interp, argv[0], ": no subscription filter specified", NULL);
        return TCL_ERROR;
    }
    Tcl_AppendResult(interp, "OK", NULL);
    client->subscribe(argv[1]);
    return TCL_OK;
}

static int dservUnsubscribeCmd(ClientData clientData, Tcl_Interp *interp,
                              int argc, char *argv[])
{
    DataserverClient *client = (DataserverClient *) clientData;
    if (argc < 2) {
        Tcl_AppendResult(interp, argv[0], ": no unsubscribe filter specified", NULL);
        return TCL_ERROR;
    }
    Tcl_AppendResult(interp, "OK", NULL);
    client->unsubscribe(argv[1]);
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

// Called when subscribed datapoint is received
void process_datapoint(TclZMQ &tclZmq, Datapoint *dpoint)
{
    Tcl_SetVar2(tclZmq.getInterp(), "dsVals", dpoint->varname,
		dpoint->toString().c_str(), TCL_GLOBAL_ONLY);
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

    if (daemonize) {
        // Define variables
        pid_t pid, sid;

        // Fork the current process
        pid = fork();
        // The parent process continues with a process ID greater than 0
        if (pid > 0) {
            exit(EXIT_SUCCESS);
        }
            // A process ID lower than 0 indicates a failure in either process
        else if (pid < 0) {
            exit(EXIT_FAILURE);
        }
        // The parent process has now terminated
        //   and the forked child process will continue
        // (the pid of the child process was 0)

        // Since the child process is a daemon,
        //  the umask needs to be set so files and logs can be written
        umask(0);

        // Open system logs for the child process
        openlog("scheduler", LOG_NOWAIT | LOG_PID, LOG_USER);
        syslog(LOG_NOTICE, "Successfully started scheduler");

        // Generate a session ID for the child process
        sid = setsid();
        // Ensure a valid SID for the child process
        if (sid < 0) {
            // Log failure and exit
            syslog(LOG_ERR, "Could not generate session ID for child process");

            // If a new session ID could not be generated,
            //   we must terminate the child process or it will be orphaned
            exit(EXIT_FAILURE);
        }

        // Change the current working directory to one guaranteed to exist
        if ((chdir("/")) < 0) {
            // Log failure and exit
            syslog(LOG_ERR, "Could not change working directory to /");

            // If our guaranteed directory does not exist,
            //   terminate the child process to ensure
            // the daemon has not been hijacked
            exit(EXIT_FAILURE);
        }

        // A daemon cannot use the terminal, so close standard
        //   file descriptors for security reasons
        close(STDIN_FILENO);
        close(STDOUT_FILENO);
        close(STDERR_FILENO);
    }

    int pid = getpid();

    // Install a signal handler to shutdown properly
    std::signal(SIGINT, signal_handler);

    // acquire zmq context with 3 polling items
    ZmqServer server(3);

    /// Dataserver Push Socket
    DataserverClient dserv_push_client(server.getContext(),
				  DataserverClient::DS_CLIENT_PUSH);

//    DataserverClient dserv_client(server.getContext(),
//				  DataserverClient::DS_CLIENT);

    /// Dataserver Socket
    //  Socket to receive subscriptions from dataserver
    DataserverClient dserv_subscriber(server.getContext(),
				      DataserverClient::DS_CLIENT_SUB);
    int dserv_msg_id = server.addItem((void *) *dserv_subscriber.getSocket());

    /// Timer File Descriptor
    TimerFD timerfd(interval, &server);
    int timer_msg_id = timerfd.getItemId();

    /// Tcl Socket
    TclZMQ tclZmq(argv[0], &server, servername);
    int tcl_msg_id = tclZmq.getItemId();

    tclZmq.addCommand("shutdown", (Tcl_CmdProc *) shutdownCmd, &m_bDone);
    tclZmq.addCommand("dserv_subscribe", (Tcl_CmdProc *) dservSubscribeCmd,
		      &dserv_subscriber);
    tclZmq.addCommand("dserv_unsubscribe", (Tcl_CmdProc *) dservUnsubscribeCmd,
		      &dserv_subscriber);

    std::vector<TouchSensor *> sensors;
    for (auto i = 0; i < nsensors; i++) {
      TouchSensor *sensor = new TouchSensor(i);
      sensors.push_back(sensor);
    }
    
    tclZmq.addCommand("sensor_values", (Tcl_CmdProc *) sensorValuesCmd, &sensors);
    tclZmq.addCommand("sensor_activate", (Tcl_CmdProc *) sensorActivateCmd, &sensors);
    tclZmq.addCommand("sensor_deactivate", (Tcl_CmdProc *) sensorDeactivateCmd, &sensors);
    tclZmq.addCommand("sensor_setEmptyBaseline", (Tcl_CmdProc *) sensorSetEmptyBaselineCmd, &sensors);
    tclZmq.addCommand("sensor_setObjectBaseline", (Tcl_CmdProc *) sensorSetObjectBaselineCmd, &sensors);

    ///// MAIN LOOP
    while (!m_bDone) {
        server.waitForEvent();

        if (server.receivedItem(dserv_msg_id)) {
            Datapoint *dpoint = dserv_subscriber.receiveDatapoint();
            process_datapoint(tclZmq, dpoint);
        }

        if (server.receivedItem(timer_msg_id)) {
            timerfd.process();
	    int i = 0;
	    for (auto sensor : sensors) {
	      sensor->update();
	      if (push_updates_to_dataserver) {
		    std::string varstr = "sensor:" + std::to_string(i++) + ":vals";
		    Datapoint d{varstr.c_str(), (void *) sensor->vals(), sensor->nchannels(),
			    TouchSensor::DATATYPE};

            dserv_push_client.push(d);
  	      }
	    }
	}

        if (server.receivedItem(tcl_msg_id)) {
            tclZmq.process();
        }
    }

    // Release sensors
    for (auto p : sensors) delete p;
    sensors.clear();
    
    // Shutdown timer
    timerfd.shutdown();

    if (verbose) std::cout << "Shutting down" << std::endl;

    if (daemonize) {
        // Close system logs for the child process
        syslog(LOG_NOTICE, "Stopping touch_sensor");
        closelog();
    }
    
    return 0;
}
