#include <time.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "mpr121.h"
#include <hiredis.h>


//#define MPR121_ELE0_FILTDATA_REG 0x1E     // baseline
#define MPR121_ELE0_FILTDATA_REG 0x04     // filtered



int main()
{
  int i, n = 1000;
  int print_output = 1;
  uint32_t states;
  unsigned char filtdata[24];
  int channels_to_read = 12;
  int left_baseline[6] = {557, 560, 558, 562, 550, 550};
  // from arduino         271  282  273  301  294  303  426  424  416  402  390  374
  int right_baseline[6] = {557, 561, 554, 553, 554, 557};
  int val;
  int left_connected = 0;       //keeps track of whether theres a shape attached to left magnet
  int right_connected = 0;      //keeps track of whether theres a shape attached to left magnet
  int connected_thresh = 10;    //threshold for determining if shape is attached
  time_t current_time;

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

  if(mpr121_config_an3944(dev) != UPM_SUCCESS){
    printf("unable to configure device\n");
  }
  if(mpr121_config_an3944(dev2) != UPM_SUCCESS){
    printf("unable to configure device2\n");
  }

  for (i=0; i<n || print_output; i++){
    // read nchannels (8 bits in LB and 2 bits in high byte) all at once
    if (mpr121_read_bytes(dev, MPR121_ELE0_FILTDATA_REG, filtdata, channels_to_read*2) != UPM_SUCCESS) {
      printf("Error while reading filtered data\n");
    } else {

      current_time = time(NULL);
      redisCommand(c, "SET left_sensor_last_update %d", current_time);


      if (print_output) {
        int j, m;
        printf("Left: ");
        for (j = 0, m = 0; j < channels_to_read; j++, m+=2) {
          val = filtdata[m] | (filtdata[m+1] << 8);

          // keep track of whether there's an object being held or not
          if (m == 0 && left_connected == 1 && (left_baseline[0] - val) < connected_thresh ) {
            left_connected = 0;
            redisCommand(c, "SET left_connected 0");
          } else if (m == 0 && left_connected == 0 && (left_baseline[0] - val) >= connected_thresh ) {
            left_connected = 1;
            redisCommand(c, "SET left_connected 1");
          }

          printf("%d \t", val);
    	}
      }
    }

    if (mpr121_read_bytes(dev2, MPR121_ELE0_FILTDATA_REG, filtdata, channels_to_read*2) != UPM_SUCCESS) {
      printf("Error while reading filtered data\n");
    } else {
      if (print_output) {
        int j, m;
        printf("Right: ");
        for (j = 0, m = 0; j < channels_to_read; j++, m+=2) {
          val = filtdata[m] | (filtdata[m+1] << 8);

          // keep track of whether there's an object being held or not
          if (m == 0 && right_connected == 1 && (right_baseline[0] - val) < connected_thresh ) {
            right_connected = 0;
            redisCommand(c, "SET right_connected 0");
          } else if (m == 0 && right_connected == 0 && (right_baseline[0] - val) >= connected_thresh ) {
            right_connected = 1;
            redisCommand(c, "SET right_connected 1");
          }

          printf("%d \t", val);
        }
      }
    }

   if (print_output) {
	 printf("\n");
     usleep(100000);
   }
  }

  mpr121_close(dev);
  mpr121_close(dev2);

  return 0;
}
