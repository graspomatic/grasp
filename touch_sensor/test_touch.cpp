#include "Datapoint.hpp"
#include "touch_sensor/TouchSensor.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
  TouchSensor sensor(0); // if your MPR121 is at 0x5A; use 1 for 0x5B, etc.
  for (int i = 0; i < 10; ++i) {
    sensor.update();
    std::cout << sensor.strvals() << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }
  return 0;
}