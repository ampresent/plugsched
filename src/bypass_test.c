#include <linux/kconfig.h>
#include <linux/stop_machine.h>
#include <linux/kallsyms.h>
#include "helper.h"
#include "tainted.h"

#ifdef SCHEDMOD_BYPASS_TEST
const char *white_list[] = {
	"unregister_sched_domain_sysctl",
	"register_sched_domain_sysctl",
	"set_rq_offline",
	"set_rq_online",
	NULL,
};

#ifdef CONFIG_X86_64
static inline void install_bypass_checker(unsigned long addr, struct tainted_function *tf)
{
	u8 *insns = addr;

	if (insns[0] == 0xe9)
		return;

	tf->store_header[0] = insns[0];
	tf->store_header[1] = insns[1];
	insns[0] = 0xf;
	insns[1] = 0xb;
}

static inline void uninstall_bypass_checker(unsigned long addr, struct tainted_function *tf)
{
	u8 *insns = addr;

	if (insns[0] == 0xe9)
		return;

	insns[0] = tf->store_header[0];
	insns[1] = tf->store_header[1];
}
#endif

static int handle_bypass_checkers(void *args)
{
	bool ignore, install = args;
	u8 *new_addr, *old_addr;
	struct tainted_function *tf;
	unsigned long text_flag;
	const char **wl;

	text_flag = prepare_modify_text();
	for (tf=tainted_functions; tf->name; tf++) {
		new_addr = module_kallsyms_lookup_name(tf->mod_name);
		old_addr = kallsyms_lookup_name(tf->plain_name);

		for (wl=white_list;*wl;wl++) {
			if (!strcmp(tf->plain_name, *wl)) {
				ignore = true;
				break;
			}
		}

		if (ignore)
			continue;

		if (old_addr == new_addr)
			panic("Failed to find function %s in vmlinux.", tf->plain_name);

		if (install)
			install_bypass_checker(old_addr, tf);
		else
			uninstall_bypass_checker(old_addr, tf);
	}
	finish_modify_text(text_flag);
	printk("%s bypass checker done\n", install?"Installing":"Uninstalling", tf->plain_name);
}

void install_bypass_checkers(void)
{
	stop_machine(handle_bypass_checkers, true, NULL);
}

void uninstall_bypass_checkers(void)
{
	stop_machine(handle_bypass_checkers, false, NULL);
}
#endif