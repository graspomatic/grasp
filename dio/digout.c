#include <stdio.h>
#include <gpiod.h>

int main(int argc, char *argv[])
{
  int value;
  int offset = 1;
  int status;
  
  if (argc < 2) {
    printf("usage: digout 0|1\n");
    return 0;
  }

  value = (atoi(argv[1]) != 0);

  status = gpiod_ctxless_set_value_multiple("/dev/gpiochip2", &offset, &value,
					    1, false,
					    "gpioset", NULL, NULL);

  if (status < 0) {
    printf("error setting the GPIO line values");
    exit(0);
  }
}
