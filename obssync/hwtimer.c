#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/hrtimer.h>
#include <linux/ktime.h>
 
MODULE_LICENSE("GPL");
 
static struct hrtimer hr_timer;

#define MS_TO_NS(x) (x * 1E6L)

enum hrtimer_restart my_hrtimer_callback( struct hrtimer *timer )
{
  printk( "my_hrtimer_callback called (%ld).\n", jiffies );
  hrtimer_forward(timer,hrtimer_cb_get_time(timer),
		  MS_TO_NS(2000));
  return HRTIMER_RESTART;
}
 
int init_module( void )
{
  ktime_t ktime;
  unsigned long delay_in_ms = 2000L;
 
  printk("HR Timer module installing\n");
  ktime = ktime_set( 0, MS_TO_NS(delay_in_ms) ); 
  hrtimer_init( &hr_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL );
  hr_timer.function = &my_hrtimer_callback;
  printk( "Starting timer to fire in %ldms (%ld)\n", delay_in_ms, jiffies );
  hrtimer_start( &hr_timer, ktime, HRTIMER_MODE_REL );
  return 0;
}
 
void cleanup_module( void )
{
  int ret;
 
  ret = hrtimer_cancel( &hr_timer );
  if (ret) printk("The timer was still in use...\n");
  printk("HR Timer module uninstalling\n");
  return;
}
