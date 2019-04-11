#include <time.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "mpr121.h"
#include <hiredis.h>

#define MPR121_ELE0_FILTDATA_REG 0x04     // filtered

// Local version of the sensor configuration for grasp
upm_result_t mpr121_configure(mpr121_context dev){
    // Configure the mpr121 chip (mostly) as recommended in the AN3944 MPR121
    // Quick Start Guide
    // First, turn off all electrodes by zeroing out the Electrode Configuration
    // register.
    // If this one fails, it's unlikely any of the others will succeed.
    uint8_t eleConf = 0x00;
    if (mpr121_write_bytes(dev, 0x5e, &eleConf, 1) != UPM_SUCCESS){
        printf("write to electrode configuration register failed\n");
        return UPM_ERROR_OPERATION_FAILED;
    }



    // Section A // AN3891
    // Filtering when data is greater than baseline
    // regs 0x2b-0x2e

//    uint8_t sectA[] = {0x01, 0x01, 0x00, 0x00}; // original
    uint8_t sectA[] = {0x01, 0x01, 0x01, 0x01}; // AN3891
    if (mpr121_write_bytes(dev, 0x2b, sectA, 4) != UPM_SUCCESS){
        printf("write to section a failed\n");
        return UPM_ERROR_OPERATION_FAILED;
    }

    // Section B // AN3891
    // Filtering when data is less than baseline
    // regs 0x2f-0x32

    uint8_t sectB[] = {0x01, 0x01, 0xff, 0x02};
    if (mpr121_write_bytes(dev, 0x2f, sectB, 4) != UPM_SUCCESS){
        printf("write to section b failed\n");
        return UPM_ERROR_OPERATION_FAILED;
    }



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

    if (mpr121_write_bytes(dev, 0x41, sectC, 24) != UPM_SUCCESS){
        printf("failed to configure touch threshold/release regs\n");
        return UPM_ERROR_OPERATION_FAILED;
    }



    // Filter configuration (added)
    // reg 0x5c
//      uint8_t filterConfc = 0x00; // 6 samples, disable electrode charing
      uint8_t filterConfc = 0x50; // 10 samples, 16ua electrode charging
    if (mpr121_write_bytes(dev, 0x5c, &filterConfc, 1) != UPM_SUCCESS){
        printf("unable to configure filters\n");
        return UPM_ERROR_OPERATION_FAILED;
    }


    // Section D
    // Filter configuration
    // reg 0x5d
//    uint8_t filterConf = 0x04; //original
//    uint8_t filterConf = 0x24; // default on data sheet
    uint8_t filterConf = 0x41; // 1 us charge/discharge time, 4 samples for 2nd folter, 2ms sample interval
//      uint8_t filterConf = 0x00; // no electrode charging, 4 samples for 2nd filter, 1 ms period
    if (mpr121_write_bytes(dev, 0x5d, &filterConf, 1) != UPM_SUCCESS){
        printf("unable to configure filters\n");
        return UPM_ERROR_OPERATION_FAILED;
    }

    // Section F
    // Autoconfiguration control registers
    // regs 0x7b-0x7f
//    uint8_t sectF0 = 0x0b; // does autoconfig
    uint8_t sectF0 = 0x08; //doesnt do autoconfig  (I think this is the option that fixed the flaky starts)
    if (mpr121_write_bytes(dev, 0x7b, &sectF0, 1) != UPM_SUCCESS){
        printf("unable to configure auto config regs\n");
        return UPM_ERROR_OPERATION_FAILED;
    }

    // Autoconfiguration target settings
    uint8_t sectF1[] = {0x9c, 0x65, 0x8c};
    if (mpr121_write_bytes(dev, 0x7d, sectF1, 3) != UPM_SUCCESS){
        return UPM_ERROR_OPERATION_FAILED;
    }

    // Section E - this one must be set last, and switches to run mode
    // Enable all 6 electrodes, and set a pre-calibration to avoid
    // excessive calibration delay on startup.
    // reg 0x5e
    eleConf = 0x86;
    if (mpr121_write_bytes(dev, 0x5e, &eleConf, 3) != UPM_SUCCESS){
        return UPM_ERROR_OPERATION_FAILED;
    }

    return UPM_SUCCESS;
}




int main()
{
  int i, n = 1000;
  int print_output = 1;
  uint32_t states;
  unsigned char filtdata[24];
  int channels_to_read = 6;
  int left_baseline[6] = {558, 561, 559, 563, 551, 551};
  int right_baseline[6] = {558, 562, 555, 555, 556, 558};
  int left_current[6] = {0, 0, 0, 0, 0, 0};
  int right_current[6] = {0, 0, 0, 0, 0, 0};
  int left_touched[6] = {0, 0, 0, 0, 0, 0};
  int right_touched[6] = {0, 0, 0, 0, 0, 0};
  int j, m;
  int val;
  int left_connected = 0;       //keeps track of whether theres a shape attached to left magnet
  int right_connected = 0;      //keeps track of whether theres a shape attached to left magnet
  int connected_thresh = 10;    //threshold for determining if shape is attached
  int touched_thresh = 10;
  redisReply *reply;            // holds reply from redis
  char* endptr;                 // used for string to int conversion
  int calib = 0;                // holds value returned from redis about whether we're supposed to get calib values
  int cal_left[6] = {0, 0, 0, 0, 0, 0};       // holds baseline calibration for currently held shape
  int cal_right[6] = {0, 0, 0, 0, 0, 0};      // holds baseline calibration for currently held shape
  time_t current_time;
  time_t last_update_left = time(NULL);
  time_t last_update_right = time(NULL);

  redisContext *c = redisConnect("127.0.0.1", 6379);
  if (c == NULL || c->err) {
      if (c) {
          printf("Error: %s\n", c->errstr);
          // handle error
      } else {
          printf("Can't allocate redis context\n");
      }
  }


//  redisCommand(c, "PUBLISH WebClient {'rightsensor':'dc'}");  //works
//  redisCommand(c, "PUBLISH WebClient {'leftsensor':'2','rightsensor':'1'}"); //works


  mpr121_context dev = mpr121_init(MPR121_I2C_BUS, MPR121_DEFAULT_I2C_ADDR);
  mpr121_context dev2 = mpr121_init(MPR121_I2C_BUS, MPR121_DEFAULT_I2C_ADDR + 1);

  if(mpr121_configure(dev) != UPM_SUCCESS){
    printf("unable to configure device\n");
  }
  if(mpr121_configure(dev2) != UPM_SUCCESS){
    printf("unable to configure device2\n");
  }


  clock_t begin = clock();


  for (i=0; i<n || print_output; i++){
//  for (i=0; i<1000; i++){

    // see if we're supposed to grab new calibration values on this turn
    reply = redisCommand(c, "GET get_calib");
    calib = strtoimax(reply->str,&endptr,10);

    if (calib > 0) {
        redisCommand(c, "SET get_calib 0");
    }



    // read nchannels (8 bits in LB and 2 bits in high byte) all at once
    if (mpr121_read_bytes(dev, MPR121_ELE0_FILTDATA_REG, filtdata, channels_to_read*2) != UPM_SUCCESS) {
        printf("Error while reading filtered data\n");
    } else {

        // tell redis we're getting live readings for the left
        current_time = time(NULL);
        if (current_time != last_update_left) {
            redisCommand(c, "SET left_sensor_last_update %d", current_time);
            last_update_left = current_time;
        }

        // get new readings for left
        for (j = 0, m = 0; j < channels_to_read; j++, m+=2) {
            left_current[j] = filtdata[m] | (filtdata[m+1] << 8);
        }

        // keep track of whether there's an object being held or not
        if (left_connected == 1 && (left_baseline[0] - left_current[0]) < connected_thresh ) {
            left_connected = 0;
            redisCommand(c, "SET left_connected 0");
        } else if (left_connected == 0 && (left_baseline[0] - left_current[0]) >= connected_thresh ) {
            left_connected = 1;
            redisCommand(c, "SET left_connected 1");
        }

        // handle calibration
        if (calib == 1 || calib == 3) {
            memcpy(cal_left, left_current, sizeof(left_current));
        }

        // determine which pads are touched
        for (j = 0; j < 6; j++) {
            left_touched[j] = ((cal_left[j] - left_current[j]) > touched_thresh);
        }

        if (print_output) {
            for (j = 0; j < 6; j++) {
//                printf("%d \t", left_current[j]);
//                printf("\r");
                printf("%d \t", left_touched[j]);
            }
        }
    }

    if (mpr121_read_bytes(dev2, MPR121_ELE0_FILTDATA_REG, filtdata, channels_to_read*2) != UPM_SUCCESS) {
        printf("Error while reading filtered data\n");
    } else {

      // tell redis we're getting live readings for the right
        current_time = time(NULL);
        if (current_time != last_update_right) {
            redisCommand(c, "SET right_sensor_last_update %d", current_time);
            last_update_right = current_time;
        }

        // get new readings for left
        for (j = 0, m = 0; j < channels_to_read; j++, m+=2) {
            right_current[j] = filtdata[m] | (filtdata[m+1] << 8);
        }

        // keep track (internally and in redis) of whether there's an object being held or not
        if (right_connected == 1 && (right_baseline[0] - right_current[0]) < connected_thresh ) {
            right_connected = 0;
            redisCommand(c, "SET right_connected 0");
        } else if (right_connected == 0 && (right_baseline[0] - right_current[0]) >= connected_thresh ) {
            right_connected = 1;
            redisCommand(c, "SET right_connected 1");
        }

        // handle calibration
        if (calib == 1 || calib == 3) {
            memcpy(cal_right, right_current, sizeof(right_current));
        }

        // determine which pads are touched
        for (j = 0; j < 6; j++) {
            right_touched[j] = ((cal_right[j] - right_current[j]) > touched_thresh);
        }

        if (print_output) {
            for (j = 0; j < 6; j++) {
//                printf("%d \t", left_current[j]);
//                printf("\r");
                printf("%d \t", right_touched[j]);
            }
        }
    }
  }

  clock_t end = clock();
  printf("Elapsed approximately: %f seconds\n", (double)(end - begin) / CLOCKS_PER_SEC * 5);


  mpr121_close(dev);
  mpr121_close(dev2);

  return 0;
}
