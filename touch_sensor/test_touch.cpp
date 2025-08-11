// Minimal stub so TouchSensor.hpp compiles without the full project headers
// compile with lab@grasp2:~/grasp/touch_sensor $ g++ -std=gnu++14 test_touch.cpp -I . $(pkg-config --cflags mraa) $(pkg-config --libs mraa) -o test_touch

namespace Datapoint { enum DataType { DS_SHORT = 0 }; }

#include "TouchSensor.hpp"
#include <exception>
#include <iostream>
#include <thread>
#include <chrono>

static TouchSensor* makeSensor(int offset, int start, int count) {
  try { return new TouchSensor(1, offset, start, count); }
  catch (...) { return new TouchSensor(0, offset, start, count); }
}

int main() {
  // Read ch 0-5 and 6-11 for both addresses to verify mapping
  TouchSensor* sA_lo = nullptr; // 0x5A, 0-5
  TouchSensor* sA_hi = nullptr; // 0x5A, 6-11
  TouchSensor* sB_lo = nullptr; // 0x5B, 0-5
  TouchSensor* sB_hi = nullptr; // 0x5B, 6-11

  try { sA_lo = makeSensor(0, 0, 6); } catch (const std::exception& e) { std::cerr << "0x5A(0-5) init failed: " << e.what() << "\n"; }
  try { sA_hi = makeSensor(0, 6, 6); } catch (const std::exception& e) { std::cerr << "0x5A(6-11) init failed: " << e.what() << "\n"; }
  try { sB_lo = makeSensor(1, 0, 6); } catch (const std::exception& e) { std::cerr << "0x5B(0-5) init failed: " << e.what() << "\n"; }
  try { sB_hi = makeSensor(1, 6, 6); } catch (const std::exception& e) { std::cerr << "0x5B(6-11) init failed: " << e.what() << "\n"; }

  if (!(sA_lo || sA_hi || sB_lo || sB_hi)) {
    std::cerr << "No sensors initialized" << std::endl;
    return 1;
  }

  for (int i = 0; i < 10; ++i) {
    if (sA_lo) { sA_lo->update(); std::cout << "0x5A[0-5]:  " << sA_lo->strvals() << "\n"; }
    if (sA_hi) { sA_hi->update(); std::cout << "0x5A[6-11]: " << sA_hi->strvals() << "\n"; }
    if (sB_lo) { sB_lo->update(); std::cout << "0x5B[0-5]:  " << sB_lo->strvals() << "\n"; }
    if (sB_hi) { sB_hi->update(); std::cout << "0x5B[6-11]: " << sB_hi->strvals() << "\n"; }
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
  }

  delete sA_lo; delete sA_hi; delete sB_lo; delete sB_hi;
  return 0;
}