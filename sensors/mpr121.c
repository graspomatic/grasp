//Modified: Abhishek Malik <abhishek.malik@intel.com>

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "mpr121.h"

#define MPR121_ELE0_FILTDATA_REG 0x04

int main()
{
  int i, n = 1000;
  int print_output = 1;
  uint32_t states;
  unsigned char filtdata[24];
  int channels_to_read = 6;
  int left_baseline[6] = {557, 560, 558, 562, 550, 550};
  int right_baseline[6] = {557, 561, 554, 553, 554, 557};


  // 45 512 49 512 46 512 50 512 38 812 51 512


  int val1;
  int val2;

  mpr121_context dev = mpr121_init(MPR121_I2C_BUS, MPR121_DEFAULT_I2C_ADDR);
  usleep(50000);
  mpr121_context dev2 = mpr121_init(MPR121_I2C_BUS, MPR121_DEFAULT_I2C_ADDR + 1);
  usleep(50000);
  
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
      if (print_output) {
        int j, m;
        printf("Left: ");
        for (j = 0, m = 0; j < channels_to_read; j++, m+=2) {
            val1 = filtdata[m];
            val2 = (filtdata[m+1] << 8);
            printf("%i \t", val1);
            printf("%i \t", val2);

         // val = filtdata[m] | (filtdata[m+1] << 8);
          //printf("%i \t", filtdata[m] | (filtdata[m+1] << 8));
          //printf("%i \t", left_baseline[j] - val);
    	}
      }
    }

    usleep(50000);

    if (mpr121_read_bytes(dev2, MPR121_ELE0_FILTDATA_REG, filtdata, channels_to_read*2) != UPM_SUCCESS) {
      printf("Error while reading filtered data\n");
    } else {
      if (print_output) {
        int j, m;
        printf("Right: ");
        for (j = 0, m = 0; j < channels_to_read; j++, m+=2) {
          val1 = filtdata[m] | (filtdata[m+1] << 8);

          printf("%i \t", right_baseline[j] - val1);
        }
      }
    }

   if (print_output) {
	 printf("\n");
     usleep(500000);
   }
  }

  mpr121_close(dev);
  mpr121_close(dev2);

  return 0;
}
