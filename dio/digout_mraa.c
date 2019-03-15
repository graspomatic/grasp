#include "mraa.h"
#include <stdio.h>
#include <unistd.h>

int main(int argc, char *argv[]) { 

  int val;

  if (argc < 2) {
    printf("usage: digout 0|1\n");
    return 0;
  }
  
  val = (atoi(argv[1]) != 0);
  mraa_init(); 
  mraa_gpio_context pin23 = mraa_gpio_init(23);
  mraa_gpio_dir(pin23, MRAA_GPIO_OUT); 
  mraa_gpio_write(pin23, val);
  return MRAA_SUCCESS;
} 

