// Minimal stub so TouchSensor.hpp compiles without the full project headers
namespace Datapoint { enum DataType { DS_SHORT = 0 }; }

#include "TouchSensor.hpp"
#include <exception>
#include <iostream>
#include <thread>
#include <chrono>

int main() {
  TouchSensor* sensor = nullptr;
  try {
    sensor = new TouchSensor(0, 0);
  } catch (const std::exception& e) {
    try {
      sensor = new TouchSensor(1, 0);
    } catch (const std::exception& e2) {
      std::cerr << "Failed to initialize TouchSensor on bus 0 and 1: " << e2.what() << std::endl;
      return 1;
    }
  }

  for (int i = 0; i < 10; ++i) {
    sensor->update();
    std::cout << sensor->strvals() << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }

  delete sensor;
  return 0;
}