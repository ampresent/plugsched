#include <linux/kobject.h>

struct tainted_function {
	char *name;
#ifdef SCHEDMOD_BYPASS_TEST
	char *plain_name;
	char *mod_name;
	char store_header[2];
#endif
	struct kobject *kobj;
};

extern struct tainted_function tainted_functions[];

extern int register_tainted_functions(struct kobject *);
extern void unregister_tainted_functions(void);