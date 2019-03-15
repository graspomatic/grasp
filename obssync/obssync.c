/**
 * @file   obssync.c
 * @author David Sheinberg
 * @date   10 April 2019
 * @brief  A kernel module for controlling a sync line associated with the experiment
 * control system. It has support for interrupts and for sysfs entries so that an interface
 * can be created to the sync line can be configured from Linux userspace.
 * The sysfs entry appears at /sys/obsync/gpio338
 * @credit Code based on Derek Molloy's Exploring BeagleBone button driver
*/

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/gpio.h>       // Required for the GPIO functions
#include <linux/interrupt.h>  // Required for the IRQ code
#include <linux/kobject.h>    // Using kobjects for the sysfs bindings
#include <linux/time.h>       // Using the clock to measure time between obs
#define  DEBOUNCE_TIME 0      ///< The default bounce time -- 0ms

MODULE_LICENSE("GPL");
MODULE_AUTHOR("David Sheinberg");
MODULE_DESCRIPTION("A Linux GPIO LKM for tracking Obs Periods");
MODULE_VERSION("0.1");

static bool isRising = 1;                   ///< Rising edge is the default IRQ property
module_param(isRising, bool, S_IRUGO);      ///< Param desc. S_IRUGO can be read/not changed
MODULE_PARM_DESC(isRising, " Rising edge = 1 (default), Falling edge = 0");  ///< parameter description

static unsigned int gpioLine = 338;         ///< Default GPIO is 338
module_param(gpioLine, uint, S_IRUGO);      ///< Param desc. S_IRUGO can be read/not changed
MODULE_PARM_DESC(gpioLine, " GPIO line number (default=338)");  ///< parameter description

static char   gpioName[8] = "obssync";      ///< Null terminated default string -- just in case
static int    irqNumber;                    ///< Used to share the IRQ number within this file
static int    numberObs = 0;                ///< For information, store the number of obs periods
static bool   isDebounce = 0;               ///< Use to store the debounce state (on by default)

static struct timespec ts_last, ts_current, ts_diff;  ///< timespecs from linux/time.h (has nano precision)

/// Function prototype for the custom IRQ handler function -- see below for the implementation
static irq_handler_t  obssync_irq_handler(unsigned int irq, void *dev_id,
					  struct pt_regs *regs);

/** @brief A callback function to output the numberObs variable
 *  @param kobj represents a kernel object device that appears in the sysfs filesystem
 *  @param attr the pointer to the kobj_attribute struct
 *  @param buf the buffer to which to write the number of presses
 *  @return return the total number of characters written to the buffer (excluding null)
 */
static ssize_t numberObs_show(struct kobject *kobj,
			      struct kobj_attribute *attr, char *buf){
  return sprintf(buf, "%d\n", numberObs);
}

/** @brief A callback function to read in the numberObs variable
 *  @param kobj represents a kernel object device that appears in the sysfs filesystem
 *  @param attr the pointer to the kobj_attribute struct
 *  @param buf the buffer from which to read the number of obs periods (e.g., reset to 0).
 *  @param count the number characters in the buffer
 *  @return return should return the total number of characters used from the buffer
 */
static ssize_t numberObs_store(struct kobject *kobj, struct kobj_attribute *attr,
			       const char *buf, size_t count){
  sscanf(buf, "%du", &numberObs);
  return count;
}

/** @brief Displays the last time the obs line went high -- manually output the date (no localization) */
static ssize_t lastTime_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf){
  return sprintf(buf, "%lu\n", (ts_last.tv_sec*1000000)+(ts_last.tv_nsec/1000));
}

/** @brief Display the time difference in the form secs.nanosecs to 9 places */
static ssize_t diffTime_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf){
  return sprintf(buf, "%lu\n", (ts_diff.tv_sec*1000000)+(ts_diff.tv_nsec/1000));
}

/** @brief Displays if obs status is on or off */
static ssize_t inObs_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf){
   return sprintf(buf, "%d\n", gpio_get_value(gpioLine));;
}

/** @brief Displays if obs line debouncing is on or off */
static ssize_t isDebounce_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf){
   return sprintf(buf, "%d\n", isDebounce);
}

/** @brief Stores and sets the debounce state */
static ssize_t isDebounce_store(struct kobject *kobj, struct kobj_attribute *attr, const char *buf, size_t count){
   unsigned int temp;
   sscanf(buf, "%du", &temp);                // use a temp varable for correct int->bool
   gpio_set_debounce(gpioLine,0);
   isDebounce = temp;
   if(isDebounce) { gpio_set_debounce(gpioLine, DEBOUNCE_TIME);
      printk(KERN_INFO "ObsSync: Debounce on\n");
   }
   else { gpio_set_debounce(gpioLine, 0);  // set the debounce time to 0
      printk(KERN_INFO "ObsSync: Debounce off\n");
   }
   return count;
}

/**  Use these helper macros to define the name and access levels of the kobj_attributes
 *  The kobj_attribute has an attribute attr (name and mode), show and store function pointers
 *  The count variable is associated with the numberObs variable and it is to be exposed
 *  with mode 0666 using the numberObs_show and numberObs_store functions above
 */
static struct kobj_attribute count_attr = __ATTR(numberObs, 0644, numberObs_show,
						 numberObs_store);
static struct kobj_attribute debounce_attr = __ATTR(isDebounce, 0644, isDebounce_show,
						    isDebounce_store);

/**  The __ATTR_RO macro defines a read-only attribute. There is no need to identify that the
 *  function is called _show, but it must be present. __ATTR_WO can be  used for a write-only
 *  attribute but only in Linux 3.11.x on.
 */
static struct kobj_attribute time_attr  = __ATTR_RO(lastTime);  ///< the last time pressed kobject attr
static struct kobj_attribute diff_attr  = __ATTR_RO(diffTime);  ///< the difference in time attr
static struct kobj_attribute inobs_attr = __ATTR_RO(inObs);     ///< inObs status

/**  The obssync_attrs[] is an array of attributes that is used to create the attribute group below.
 *  The attr property of the kobj_attribute is used to extract the attribute struct
 */
static struct attribute *obssync_attrs[] = {
      &count_attr.attr,                  ///< The number of obs periods
      &time_attr.attr,                   ///< Time of the last obs in HH:MM:SS:NNNNNNNNN
      &diff_attr.attr,                   ///< The difference in time between the last two obs
      &inobs_attr.attr,                  ///< The inObs status value
      &debounce_attr.attr,               ///< Is the debounce state true or false
      NULL,
};

/**  The attribute group uses the attribute array and a name, which is exposed on sysfs -- in this
 *  case it is obssync, which is automatically defined in the obsSync_init() function below
 *  using the custom kernel parameter that can be passed when the module is loaded.
 */
static struct attribute_group attr_group = {
      .name  = gpioName,                 ///< The name is generated in obsSync_init()
      .attrs = obssync_attrs,            ///< The attributes array defined just above
};

static struct kobject *obssync_kobj;

/** @brief The LKM initialization function
 *  The static keyword restricts the visibility of the function to within this C file. The __init
 *  macro means that for a built-in driver (not a LKM) the function is only used at initialization
 *  time and that it can be discarded and its memory freed up after that point. In this example this
 *  function sets up the GPIOs and the IRQ
 *  @return returns 0 if successful
 */
static int __init obsSync_init(void){
   int result = 0;
   unsigned long IRQflags = IRQF_TRIGGER_RISING;    // The default is a rising-edge interrupt
   
   printk(KERN_INFO "ObsSync: Initializing the ObsSync LKM\n");
   
   // create the kobject sysfs entry at /sys/ess
   obssync_kobj = kobject_create_and_add("ess", kernel_kobj->parent); // kernel_kobj points to /sys/kernel
   if(!obssync_kobj){
     printk(KERN_ALERT "ObsSync: failed to create kobject mapping\n");
     return -ENOMEM;
   }
   // add the attributes to /sys/obssync/ -- for example, /sys/ess/obssync/numberObs
   result = sysfs_create_group(obssync_kobj, &attr_group);
   if(result) {
     printk(KERN_ALERT "ObsSync: failed to create sysfs group\n");
     kobject_put(obssync_kobj);	                      // clean up -- remove the kobject sysfs entry
     return result;
   }
   getnstimeofday(&ts_last);                          // set the last time to be the current time
   ts_diff = timespec_sub(ts_last, ts_last);          // set the initial time difference to be 0
   
   gpio_request(gpioLine, "sysfs");       // Set up the gpioLine
   gpio_direction_input(gpioLine);        // Set the obs GPIO to be an input
   gpio_set_debounce(gpioLine, DEBOUNCE_TIME); // Debounce the obsline with a delay of 200ms
   gpio_export(gpioLine, false);          // Causes gpio338 to appear in /sys/class/gpio
      		                          // the bool argument prevents the direction from being changed

   // Perform a quick test to see that the button is working as expected on LKM load
   printk(KERN_INFO "ObsSync: The obssync state is currently: %d\n", gpio_get_value(gpioLine));

   /// GPIO numbers and IRQ numbers are not the same! This function performs the mapping for us
   irqNumber = gpio_to_irq(gpioLine);
   printk(KERN_INFO "ObsSync: The line is mapped to IRQ: %d\n", irqNumber);

   if(!isRising){                           // If the kernel parameter isRising=0 is supplied
      IRQflags = IRQF_TRIGGER_FALLING;      // Set the interrupt to be on the falling edge
   }
   // This next call requests an interrupt line
   result = request_irq(irqNumber,             // The interrupt number requested
                        (irq_handler_t) obssync_irq_handler, // The pointer to the handler function below
                        IRQflags,              // Use the custom kernel param to set interrupt type
                        "obssync_button_handler",  // Used in /proc/interrupts to identify the owner
                        NULL);                 // The *dev_id for shared interrupt lines, NULL is okay
   return result;
}

/** @brief The LKM cleanup function
 *  Similar to the initialization function, it is static. The __exit macro notifies that if this
 *  code is used for a built-in driver (not a LKM) that this function is not required.
 */
static void __exit obsSync_exit(void){
  printk(KERN_INFO "ObsSync: The button was pressed %d times\n", numberObs);
   kobject_put(obssync_kobj);               // clean up -- remove the kobject sysfs entry
   free_irq(irqNumber, NULL);               // Free the IRQ number, no *dev_id required in this case
   gpio_unexport(gpioLine);               // Unexport the Button GPIO
   gpio_free(gpioLine);                   // Free the Button GPIO
   printk(KERN_INFO "ObsSync: Goodbye from the ObsSync LKM!\n");
}

/** @brief The GPIO IRQ Handler function
 *  This function is a custom interrupt handler that is attached to the GPIO above. The same interrupt
 *  handler cannot be invoked concurrently as the interrupt line is masked out until the function is complete.
 *  This function is static as it should not be invoked directly from outside of this file.
 *  @param irq    the IRQ number that is associated with the GPIO -- useful for logging.
 *  @param dev_id the *dev_id that is provided -- can be used to identify which device caused the interrupt
 *  Not used in this example as NULL is passed.
 *  @param regs   h/w specific register values -- only really ever used for debugging.
 *  return returns IRQ_HANDLED if successful -- should return IRQ_NONE otherwise.
 */
static irq_handler_t obssync_irq_handler(unsigned int irq, void *dev_id, struct pt_regs *regs){
   getnstimeofday(&ts_current);         // Get the current time as ts_current
   ts_diff = timespec_sub(ts_current, ts_last);   // Determine the time difference between last 2 presses
   ts_last = ts_current;                // Store the current time as the last time ts_last
   printk(KERN_INFO "ObsSync: The button state is currently: %d\n", gpio_get_value(gpioLine));
   numberObs++;                     // Global counter, will be outputted when the module is unloaded
   return (irq_handler_t) IRQ_HANDLED;  // Announce that the IRQ has been handled correctly
}

// This next calls are  mandatory -- they identify the initialization function
// and the cleanup function (as above).
module_init(obsSync_init);
module_exit(obsSync_exit);
