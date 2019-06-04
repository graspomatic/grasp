//
// Created by David Sheinberg on 2019-04-15.
//

#ifndef DSERV_TOUCHSENSOR_HPP
#define DSERV_TOUCHSENSOR_HPP

#include <time.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <iostream>

#ifdef __linux__
#include <mpr121.hpp>
#endif


class TouchSensor {
  
private:
  
#ifdef __linux__
  upm::MPR121 *dev;
#endif
  
  enum { ELE0_FILTDATA_REG = 0x04 };
  
  bool active = true;		// is the sensor active
  int channels_to_read = 6;
  int current[6] = {0, 0, 0, 0, 0, 0};
  int last[6];			// last values
  
  bool touched[6] = {false, false, false, false, false, false};
  bool connected = 0;       //keeps track of whether there's a shape attached to left magnet
  bool connected_changed = false;
  int connected_thresh = 20;    //threshold for determining if shape is attached
  int touched_thresh = 10;
  int object_baseline[6] = {0, 0, 0, 0, 0, 0};       // holds baseline calibration for currently held shape
  int empty_baseline[6];      // holds baseline calibration for sensor with no object

#ifdef __linux__
    // Local version of the sensor configuration for grasp
  void configure() {
    // Configure the mpr121 chip (mostly) as recommended in the AN3944 MPR121
    // Quick Start Guide
    // First, turn off all electrodes by zeroing out the Electrode Configuration
    // register.
    // If this one fails, it's unlikely any of the others will succeed.
    uint8_t eleConf = 0x00;
    dev->writeBytes(0x5e, &eleConf, 1);
    
    // Section A // AN3891
    // Filtering when data is greater than baseline
    // regs 0x2b-0x2e
    //    uint8_t sectA[] = {0x01, 0x01, 0x00, 0x00}; // original
    uint8_t sectA[] = {0x01, 0x01, 0x01, 0x01}; // AN3891
    dev->writeBytes(0x2b, sectA, 4);
    
    // Section B // AN3891
    // Filtering when data is less than baseline
    // regs 0x2f-0x32
    uint8_t sectB[] = {0x01, 0x01, 0xff, 0x02};
    dev->writeBytes(0x2f, sectB, 4);
    
    // Section C
    // Touch Threshold/Release registers, ELE0-ELE11
    // regs 0x41-0x58
    //                    __T_  __R_
    uint8_t sectC[] =  {0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a,
			0x0f, 0x0a};
    
    dev->writeBytes(0x41, sectC, 24);
    
    // Filter configuration (added)
    // reg 0x5c
    //      uint8_t filterConfc = 0x00; // 6 samples, disable electrode charging
    uint8_t filterConfc = 0x50; // 10 samples, 16ua electrode charging
    dev->writeBytes(0x5c, &filterConfc, 1);
    
    // Section D
    // Filter configuration
    // reg 0x5d
    //    uint8_t filterConf = 0x04; //original
    //    uint8_t filterConf = 0x24; // default on data sheet
    uint8_t filterConf = 0x41; // 1 us charge/discharge time, 4 samples for 2nd folter, 2ms sample interval
    //      uint8_t filterConf = 0x00; // no electrode charging, 4 samples for 2nd filter, 1 ms period
    dev->writeBytes(0x5d, &filterConf, 1);
    
    // Section F
    // Autoconfiguration control registers
    // regs 0x7b-0x7f
    //    uint8_t sectF0 = 0x0b; // does autoconfig
    uint8_t sectF0 = 0x08; //doesnt do autoconfig  (I think this is the option that fixed the flaky starts)
    dev->writeBytes(0x7b, &sectF0, 1);
    
    // Autoconfiguration target settings
    uint8_t sectF1[] = {0x9c, 0x65, 0x8c};
    dev->writeBytes(0x7d, sectF1, 3);
    
    // Section E - this one must be set last, and switches to run mode
    // Enable all 6 electrodes, and set a pre-calibration to avoid
    // excessive calibration delay on startup.
    // reg 0x5e
    eleConf = 0x86;
    dev->writeBytes(0x5e, &eleConf, 3);
  }
#endif

public:

  TouchSensor(int offset)
  {
#ifdef __linux__
    dev = new upm::MPR121(MPR121_I2C_BUS,
			  MPR121_DEFAULT_I2C_ADDR+offset);
    configure();
#endif
  }
  
  ~TouchSensor()
  {
#ifdef __linux__
    delete dev;
#endif
  }
  
  void setEmptyBaseline() {
    memcpy(empty_baseline, current, sizeof(current));
  }
  
  void setObjectBaseline() {
    memcpy(object_baseline, current, sizeof(current));
  }
  
  void activate()
  {
    active = true;
  }
  
  void deactivate()
  {
    active = false;
  }
  
  bool update()
  {
    unsigned char filtdata[24];
    
    if (!active) {
      memset(current, 0, sizeof(current));
      memset(last, 0, sizeof(last));
      return false;
    }

    memcpy(last, current, sizeof(current));
    
#ifdef __linux__
    dev->readBytes(ELE0_FILTDATA_REG, filtdata, channels_to_read*2);
#else
    memset(filtdata, 0, sizeof(filtdata));
#endif
    
    // move new readings to current
    for (auto j = 0; j < channels_to_read; j++) {
      current[j] = filtdata[j*2] | (filtdata[j*2+1] << 8);
    }
    
    // keep track of whether there's an object being held or not
    if (connected && (object_baseline[0] - current[0]) < connected_thresh ) {
      connected = false;
      connected_changed = true;
    } else if (!connected && (object_baseline[0] - current[0]) >= connected_thresh ) {
      connected = true;
      connected_changed = true;
    } else {
      connected_changed = false;
    }
    
    // determine which pads are touched
    for (auto j = 0; j < channels_to_read; j++) {
      touched[j] = ((object_baseline[j] - current[j]) > touched_thresh);
    }
    
    return true;
  }
  
  std::string curvals()
  {
    std::string str;
    for (int i: current) {
      str += std::to_string(i) + " ";
    }
    return str;
  }
};


#endif //DSERV_TOUCHSENSOR_HPP
