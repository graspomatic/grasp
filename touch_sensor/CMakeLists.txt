cmake_minimum_required(VERSION 3.14)
project(touch_sensor)

set(CMAKE_CXX_STANDARD 14)
if(WIN32)
    include_directories(. "/usr/local/include")
    link_directories("/usr/local/lib")
    link_libraries(zmq tcl86 )
elseif(APPLE)
    include_directories(. "/usr/local/include")
    link_directories("/usr/local/lib")
    link_libraries(zmq tcl8.6 )
else()
    set(UPMLIB upm-mpr121)
    set(MRAALIB mraa)
    include_directories(. "/usr/local/include" "/usr/include/tcl8.6" "/usr/include/upm" "/usr/include/mraa")
    link_directories("/usr/local/lib")
    link_libraries(zmq tcl8.6 ${UPMLIB} ${MRAALIB})
endif()


add_executable(touch_sensor
        CMakeLists.txt
        touch_sensor.cpp
        TouchSensor.hpp)
