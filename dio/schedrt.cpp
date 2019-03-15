#include <iostream>
#include <unistd.h>
#include <csignal>
#include <thread>         // std::this_thread::sleep_for
#include <chrono>         // std::chrono::seconds
#include "Scheduler.hpp"
#include "Datapoint.h"
#include <zmq.hpp>
#include "cxxopts.hpp"

#include <gpiod.h>

void signal_handler(int signal)
{
  std::cout << "Shutting down" << std::endl;
  exit(0);
}

struct callback_info
{
  std::string s;
  long long first_time;
  int value = 0;
  const char *chip = "/dev/gpiochip2";
  unsigned int line = 1;
  struct gpiod_chip *gpiochip;
  struct gpiod_line *gpioline;
};

void callback(AlarmMsg *msg)
{
  auto cbinfo = (callback_info *) msg->userdata;
  gpiod_line_set_value(cbinfo->gpioline, cbinfo->value);
  cbinfo->value = !cbinfo->value;
  //  std::cout << cbinfo->s << " (" << ((msg->getTimestamp()-(cbinfo->first_time))/1000) << ")" << std::endl;
}

int main(int argc, char *argv[]) {
  std::string server_name = "ipc:///tmp/sched";
  std::string filter = "myvar";
  bool help = false;
  int interval = 1000;


  // Parse command line options
  try {
    cxxopts::Options options("scheduler_client", "Test client for scheduler");
    options.add_options()
            ("h,help", "Print help", cxxopts::value<bool>(help))
            ("s,servername", "Server name", cxxopts::value<std::string>(server_name))
            ("f,filter", "Filter string", cxxopts::value<std::string>(filter))
            ("i,interval", "Interval between alarms (ms)", cxxopts::value<int>(interval));

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

  bool m_bDone = false;
  int pid = getpid();
  std::string our_pull_name = server_name + "-" + std::to_string(pid);
  std::string our_push_name = server_name + "-hb";
  zmq::context_t context(1);

  // Socket for our scheduler requests
  zmq::socket_t alarm_sock(context, ZMQ_PULL);
  alarm_sock.bind(our_pull_name);

  // Push to this if we receive a heartbeat request
  zmq::socket_t heartbeat_sock(context, ZMQ_PUSH);
  heartbeat_sock.connect(our_push_name);

  // Some sample data to attach to our callback
  callback_info cbinfo = {std::string{"Callback"}, Msg::getTime()};
  cbinfo.gpiochip = gpiod_chip_open("/dev/gpiochip2");
  if (!cbinfo.gpiochip) {
    return -1;
  }

  cbinfo.gpioline = gpiod_chip_get_line(cbinfo.gpiochip, 1);
  if (!cbinfo.gpioline) {
    gpiod_chip_close(cbinfo.gpiochip);
    return -1;
  }
  
  int rv = gpiod_line_request_output(cbinfo.gpioline, "schedrt", 0);
  if (rv) {
    gpiod_chip_close(cbinfo.gpiochip);
    return -1;
  }
  
  try {
    zmq::socket_t sched_sock(context, ZMQ_REQ);
    sched_sock.connect(server_name);

    // Register our communication channel
    SchedMsg reg{pid, our_pull_name.c_str()};
    reg.zmqsend(sched_sock);
    SchedMsg *rep = SchedMsg::zmqrecv(sched_sock);

    // Send request for alarm
    SchedMsg alarm{pid, interval, true, (FUNC) callback, (void *) &cbinfo};
    cbinfo.first_time = Msg::getTime();
    alarm.zmqsend(sched_sock);
    rep = SchedMsg::zmqrecv(sched_sock);
  }
  catch (const std::exception &ex) {
    std::cerr << "error connecting to scheduler: " << ex.what() << std::endl;
    exit(0);
  }

  // Install a signal handler to shutdown properly
  std::signal(SIGINT, signal_handler);

  //  Initialize poll set
  zmq::pollitem_t items [] = {
          { alarm_sock, 0, ZMQ_POLLIN, 0 }
  };


  while (!m_bDone) {
    zmq::message_t request;
    zmq::poll(&items[0], 1, -1);

    if (items[0].revents & ZMQ_POLLIN) {
      alarm_sock.recv(&request);

      Msg *msg = (Msg *) request.data();
      switch (msg->getType()) {
        case Msg::DS_CLOSE_MESSAGE:
          m_bDone = true;
              break;
        case Msg::DS_PING: {
          PingMsg m{pid};
          zmq::message_t r(sizeof(m));
          memcpy(r.data(), &m, sizeof(m));
          heartbeat_sock.send(r);
          break;
        }
        case Msg::DS_SCHEDULER_ALARM: {
          AlarmMsg *amsg = (AlarmMsg *) msg;
          amsg->sched_callback(amsg);
        }
              break;
        default:
          break;
      }
    }
  }
  return 1;
}
