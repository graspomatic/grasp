cmake_minimum_required(VERSION 3.14)
project(touch_sensor)

set(CMAKE_CXX_STANDARD 14)

include_directories(. "/usr/local/include")
link_directories("/usr/local/lib")
link_libraries(zmq tcl8.6 )

add_executable(touch_sensor
        CMakeLists.txt
        touch_sensor.cpp
        TouchSensor.hpp)
