// Minimal stub so TouchSensor.hpp compiles without the full project headers
namespace Datapoint { enum DataType { DS_SHORT = 0 }; }

#include "TouchSensor.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
  TouchSensor sensor(0);
  for (int i = 0; i < 10; ++i) {
    sensor.update();
    std::cout << sensor.strvals() << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }
  return 0;
}