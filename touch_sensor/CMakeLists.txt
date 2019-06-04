cmake_minimum_required(VERSION 3.1)
set(CMAKE_CXX_STANDARD 11)

project( touch_sensor )

if(WIN32)
#	set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS} -DUSE_FLIR=1")
if(CMAKE_SIZEOF_VOID_P EQUAL 8)
	set(TCLLIB tcl86t_64)
elseif(CMAKE_SIZEOF_VOID_P EQUAL 4)
	set(TCLLIB tcl86t)
	set (CMAKE_INSTALL_PREFIX c:/usr/local)
endif()
elseif(APPLE)
	set(TCLLIB tcl8.6)
	set(ZMQ zmq)
	set(LOCAL_INCLUDES /usr/local/include)
	set(CMAKE_CXX_FLAGS  "${CMAKE_CXX_FLAGS}")
	set (CMAKE_INSTALL_PREFIX /usr/local)
	link_directories(/usr/local/lib)
else()
	find_library(LIBDL dl)
	find_library(LIBPTHREAD pthread)
	set(ZMQ zmq)
	set(TCLLIB tcl8.6)
	set(TCL_INCLUDE_DIR /usr/include/tcl8.6)
	set(THREADS_PREFER_PTHREAD_FLAG ON)
	find_package(Threads REQUIRED)
	set(PTHREADLIB Threads::Threads)
	set(LOCAL_INCLUDES /usr/include/upm)
	set (CMAKE_INSTALL_PREFIX /usr/local)
	link_directories(/usr/local/lib64)
endif()

include_directories( ${LOCAL_INCLUDES} ${TCL_INCLUDE_DIR} )


if(WIN32)
	add_executable( touch_sensor touch_sensor.cpp TouchSensor.hpp )
	target_link_libraries( touch_sensor  ${PTHREADLIB} ${TCLLIB} ${ZMQ})
elseif(APPLE)
	add_executable( touch_sensor touch_sensor.cpp TouchSensor.hpp )
	target_link_libraries( touch_sensor  ${PTHREADLIB} ${TCLLIB} ${ZMQ})
else()
	set(UPMLIB upm-mpr121)
	set(MRAALIB mraa)
	add_executable( touch_sensor touch_sensor.cpp )
	target_link_libraries( touch_sensor  ${PTHREADLIB} ${TCLLIB} ${ZMQ} ${UPMLIB} ${MRAALIB})
endif()


if(WIN32)

else()
	set_target_properties(touch_sensor PROPERTIES PUBLIC_HEADER "TouchSensor.hpp")
install(TARGETS touch_sensor
        LIBRARY DESTINATION /usr/local/lib
        ARCHIVE DESTINATION /usr/local/lib
        RUNTIME DESTINATION /usr/local/bin
        PUBLIC_HEADER DESTINATION /usr/local/include
)
endif()
