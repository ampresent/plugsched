#ifdef SCHEDMOD_BYPASS_TEST
extern void uninstall_bypass_checkers(void);
extern void install_bypass_checkers(void);
#else
static void uninstall_bypass_checkers(void) { }
static void install_bypass_checkers(void) { }
#endif