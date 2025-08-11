// Minimal stub so TouchSensor.hpp compiles without the full project headers
// compile with lab@grasp2:~/grasp/touch_sensor $ g++ -std=gnu++14 test_touch.cpp -I . $(pkg-config --cflags mraa) $(pkg-config --libs mraa) -o test_touch

namespace Datapoint { enum DataType { DS_SHORT = 0 }; }

#include "TouchSensor.hpp"
#include <exception>
#include <iostream>
#include <thread>
#include <chrono>

static TouchSensor* makeSensor(int offset) {
  // Prefer bus 1 on Raspberry Pi, then fall back to 0
  try { return new TouchSensor(1, offset); }
  catch (...) {
    try { return new TouchSensor(0, offset); }
    catch (...) { return nullptr; }
  }
}

int main() {
  TouchSensor* sA = nullptr; // 0x5A
  TouchSensor* sB = nullptr; // 0x5B

  sA = makeSensor(0);
  sB = makeSensor(1);

  if (!sA && !sB) {
    std::cerr << "No sensors initialized on bus 1 or 0 at 0x5A/0x5B" << std::endl;
    return 1;
  }

  for (int i = 0; i < 10; ++i) {
    if (sA) { sA->update(); std::cout << "0x5A: " << sA->strvals() << "\n"; }
    if (sB) { sB->update(); std::cout << "0x5B: " << sB->strvals() << "\n"; }
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }

  delete sA;
  delete sB;
  return 0;
}