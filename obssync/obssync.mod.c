#include <linux/module.h>
#include <linux/vermagic.h>
#include <linux/compiler.h>

MODULE_INFO(vermagic, VERMAGIC_STRING);
MODULE_INFO(name, KBUILD_MODNAME);

__visible struct module __this_module
__attribute__((section(".gnu.linkonce.this_module"))) = {
	.name = KBUILD_MODNAME,
	.init = init_module,
#ifdef CONFIG_MODULE_UNLOAD
	.exit = cleanup_module,
#endif
	.arch = MODULE_ARCH_INIT,
};

#ifdef RETPOLINE
MODULE_INFO(retpoline, "Y");
#endif

static const struct modversion_info ____versions[]
__used
__attribute__((section("__versions"))) = {
	{ 0xaf3a4001, "module_layout" },
	{ 0xd3903290, "param_ops_bool" },
	{ 0xa7e2d4b0, "param_ops_uint" },
	{ 0xfe990052, "gpio_free" },
	{ 0x4c99e953, "gpiod_unexport" },
	{ 0xc1514a3b, "free_irq" },
	{ 0x2072ee9b, "request_threaded_irq" },
	{ 0x7459d09c, "gpiod_to_irq" },
	{ 0x1050c9b4, "gpiod_export" },
	{ 0x1f5764f1, "gpiod_direction_input" },
	{ 0x47229b5c, "gpio_request" },
	{ 0x80e618ee, "kobject_put" },
	{ 0x49a6b535, "sysfs_create_group" },
	{ 0x44f1e7bc, "kobject_create_and_add" },
	{ 0x47848c90, "kernel_kobj" },
	{ 0x5287a977, "gpiod_get_raw_value" },
	{ 0x6c07ef16, "set_normalized_timespec" },
	{ 0x9ec6ca96, "ktime_get_real_ts64" },
	{ 0xdb7305a1, "__stack_chk_fail" },
	{ 0x27e1a049, "printk" },
	{ 0xde9ae83f, "gpiod_set_debounce" },
	{ 0xc2875a2c, "gpio_to_desc" },
	{ 0x91715312, "sprintf" },
	{ 0x20c55ae0, "sscanf" },
	{ 0xbdfb6dbb, "__fentry__" },
};

static const char __module_depends[]
__used
__attribute__((section(".modinfo"))) =
"depends=";


MODULE_INFO(srcversion, "A17562C52F3466DAEA2995E");
