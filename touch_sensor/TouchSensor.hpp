//
// Created by David Sheinberg on 2019-04-15.
//

#ifndef DSERV_TOUCHSENSOR_HPP
#define DSERV_TOUCHSENSOR_HPP

#include <ctime>
#include <cinttypes>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unistd.h>

#include <iostream>
#include <vector>
#include <stdexcept>

#ifdef __linux__
#include <mraa/i2c.h>
#endif


class TouchSensor {
public:
  
  static const Datapoint::DataType  DATATYPE = Datapoint::DS_SHORT;

private:
  
#ifdef __linux__
  struct RawMPR121 {
    mraa_i2c_context i2c;
    uint8_t addr;
    RawMPR121(int bus, uint8_t address)
      : i2c(mraa_i2c_init_raw(bus)), addr(address)
    {
      if (!i2c) throw std::invalid_argument("Invalid i2c bus");
      if (mraa_i2c_address(i2c, addr) != MRAA_SUCCESS)
        throw std::runtime_error("Failed to set i2c address");
    }
    ~RawMPR121() {
      if (i2c) mraa_i2c_stop(i2c);
    }
    void writeBytes(uint8_t reg, const uint8_t* data, int len) {
      std::vector<uint8_t> buf(static_cast<size_t>(len) + 1);
      buf[0] = reg;
      if (len > 0 && data) std::memcpy(&buf[1], data, static_cast<size_t>(len));
      if (mraa_i2c_write(i2c, buf.data(), buf.size()) != MRAA_SUCCESS)
        throw std::runtime_error("i2c write failed");
    }
    void readBytes(uint8_t reg, unsigned char* data, int len) {
      if (mraa_i2c_read_bytes_data(i2c, reg, data, len) != len) {
        throw std::runtime_error("i2c read_bytes_data failed");
      }
    }
  };
  RawMPR121 *dev;
#endif
  
  enum { ELE0_FILTDATA_REG = 0x04 };

  bool active = true;		// is the sensor active
  int updatecount = 0;      // reset with each activate
  int electrode_start_index = 0; // starting electrode to read
  int channels_to_read = 6;      // number of electrodes to read
  short current[12] = {0};
  short last[12];		// last values
  short mins[12];
  short maxs[12];
  bool update_maxs, update_mins;
  bool touched[12] = {false, false, false, false, false, false, false, false, false, false, false, false};
  bool connected = false;       //keeps track of whether there's a shape attached to left magnet
  bool connected_changed = false;
  int connected_thresh = 20;    //threshold for determining if shape is attached
  int touched_thresh = 10;
  short object_baseline[12] = {0};       // holds baseline calibration for currently held shape
  short empty_baseline[12];      // holds baseline calibration for sensor with no object

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
    dev->writeBytes(0x2F, sectB, 4);
    
    // Section C
    // Touch Threshold/Release registers, ELE0-ELE11
    // regs 0x41-0x58
    //                    __T_  __R_
    for (int i=0; i<12; i++) {
        uint8_t sectC_pair[] = {0x0f, 0x0a};
        dev->writeBytes(static_cast<uint8_t>(0x41 + i * 2), sectC_pair, 2);
    }
    
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
    eleConf = 0x8C; // Enable all 12 electrodes in run mode
    dev->writeBytes(0x5e, &eleConf, 1);
  }
#endif

public:

  // New constructor allowing explicit I2C bus selection
  TouchSensor(int i2cBus, int offset)
  {
#ifdef __linux__
    dev = new RawMPR121(i2cBus,
                        static_cast<uint8_t>(0x5a + offset));
    configure();
#endif
  }

  // Constructor allowing explicit read window (start electrode and count)
  TouchSensor(int i2cBus, int offset, int startElectrode, int count)
  {
#ifdef __linux__
    dev = new RawMPR121(i2cBus,
                        static_cast<uint8_t>(0x5a + offset));
    configure();
#endif
    if (startElectrode < 0) startElectrode = 0;
    if (startElectrode > 11) startElectrode = 11;
    if (count < 1) count = 1;
    if (startElectrode + count > 12) count = 12 - startElectrode;
    electrode_start_index = startElectrode;
    channels_to_read = count;
  }

  // Existing constructor now delegates to bus 1 by default (Raspberry Pi)
  TouchSensor(int offset)
    : TouchSensor(0, offset)
  {
  }
  
  ~TouchSensor()
  {
#ifdef __linux__
    delete dev;
#endif
  }
  
  void setEmptyBaseline() {
    memcpy(empty_baseline, current, channels_to_read * sizeof(short));
  }
  
  void setObjectBaseline() {
    memcpy(object_baseline, current, channels_to_read * sizeof(short));
  }
  
  void activate()
  {
    active = true;
    updatecount = 0;
  }
  
  void deactivate()
  {
    active = false;
  }
  
  bool update()
  {
    unsigned char filtdata[24];
    update_maxs = update_mins = false;

    if (!active) {
      memset(current, 0, channels_to_read * sizeof(short));
      memset(last, 0, channels_to_read * sizeof(short));
      return false;
    }

    memcpy(last, current, channels_to_read * sizeof(short));
    
#ifdef __linux__
    dev->readBytes(static_cast<uint8_t>(ELE0_FILTDATA_REG + electrode_start_index*2),
                   filtdata, channels_to_read*2);
    // move new readings to current
    for (auto i = 0; i < channels_to_read; i++) {
      current[i] = filtdata[i*2] | (filtdata[i*2+1] << 8);
    }
#else
    for (auto i = 0; i < channels_to_read; i++)
      current[i] = i;
#endif
    
    // track mins and maxs
    if (updatecount < 2) {
        memcpy(maxs, current, channels_to_read * sizeof(short));
        memcpy(mins, current, channels_to_read * sizeof(short));
        update_maxs = update_mins = true;
    }

    if (updatecount >= 2) {
        for (auto i = 0; i < channels_to_read; i++)
            if (current[i] < mins[i]) {
                mins[i] = current[i];
                update_mins = true;
            }
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

    updatecount++;

    return true;
  }

    const bool isActive()
    {
        return active;
    }

    const short *curvals()
  {
    return &current[0];
  }

  const short *minvals()
  {
        return &mins[0];
  }

  const short *maxvals()
  {
      return &maxs[0];
  }

  const bool updateMaxs()
  {
      return update_maxs;
  }

  const bool updateMins()
  {
      return update_mins;
  }

  const int nchannels()
  {
    return channels_to_read;
  }
  
  std::string strvals()
  {
    std::string str;
    for (int i = 0; i < channels_to_read; i++) {
      str += std::to_string(current[i]) + " ";
    }
    return str;
  }
};


#endif //DSERV_TOUCHSENSOR_HPP
