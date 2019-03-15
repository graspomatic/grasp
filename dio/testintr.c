#include "mraa.h"
#include <stdio.h>
#include <unistd.h>

void switchChange(void *pin); 

int wakeup = 0;

int main()
{ 
 mraa_init(); 
 mraa_gpio_context pin21 = mraa_gpio_init(21);
 mraa_gpio_dir(pin21, MRAA_GPIO_IN);
 mraa_gpio_input_mode(pin21, MRAA_GPIO_ACTIVE_LOW);
 mraa_gpio_isr(pin21, MRAA_GPIO_EDGE_BOTH,
	       &switchChange, pin21);
 int s = mraa_gpio_read(pin21);
 printf("Pin21: %d\n", s);
 
 for (;;) {
   if (wakeup) {
     int s = mraa_gpio_read(pin21);
     printf("Pin21: %d\n", s);
     wakeup = 0;
   }
   usleep(10000);
 };
 return MRAA_SUCCESS;
} 

void switchChange(void *pin)
{
  wakeup = 1;
}
