/**
 * Copyright 2019-2022 Alibaba Group Holding Limited.
 * SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause
 *
 * Main source code only support 4.19 and later kernels.
 * This file backports plugsched to very old kernels (3.10).
 * This avoids main source code messing up with a long span of kernels.
 */

#ifndef _H_FUTURE
#define _H_FUTURE
#include <linux/version.h>

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0)
#define smp_cond_load_relaxed(ptr, cond_expr) ({		\
	typeof(ptr) __PTR = (ptr);				\
	typeof(*ptr) VAL;					\
	for (;;) {						\
		VAL = READ_ONCE(*__PTR);			\
		if (cond_expr)					\
			break;					\
		cpu_relax();					\
	}							\
	VAL;							\
})

#define atomic_cond_read_relaxed(v, c)	smp_cond_load_relaxed(&(v)->counter, (c))
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 18, 0)
#define proc_create_seq proc_create
#define __mod_sched_debug_fops __mod_sched_debug_sops
#define __mod_schedstat_fops __mod_schedstat_sops
#define __orig_sched_debug_fops __orig_sched_debug_sops
#define __orig_schedstat_fops __orig_schedstat_sops
extern const struct file_operations __mod_sched_debug_fops;
extern const struct file_operations __mod_schedstat_fops;
extern struct file_operations __orig_schedstat_fops;
extern struct file_operations  __orig_sched_debug_fops;
#else
extern const struct seq_operations __mod_sched_debug_sops;
extern const struct seq_operations __mod_schedstat_sops;
extern struct seq_operations __orig_schedstat_sops;
extern struct seq_operations  __orig_sched_debug_sops;
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 4, 0)
extern void __orig___schedule(void);
#else
extern void __orig___schedule(bool);
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 11, 0)
/* These two functions haven't changed since 2.6.29 through out 4.19
 * But since 4.11, these two functions become public, and we don't need to
 * redefine them.
 */

#define __orig_set_rq_online vmlinux_set_rq_online
#define __orig_set_rq_offline vmlinux_set_rq_offline
static void vmlinux_set_rq_online(struct rq *rq)
{
	if (!rq->online) {
		const struct sched_class *class;

		cpumask_set_cpu(rq->cpu, rq->rd->online);
		rq->online = 1;

		for_each_class(class) {
			if (class->rq_online)
				class->rq_online(rq);
		}
	}
}

static void vmlinux_set_rq_offline(struct rq *rq)
{
	if (rq->online) {
		const struct sched_class *class;

		for_each_class(class) {
			if (class->rq_offline)
				class->rq_offline(rq);
		}

		cpumask_clear_cpu(rq->cpu, rq->rd->online);
		rq->online = 0;
	}
}
#else
extern void __orig_set_rq_offline(struct rq*);
extern void __orig_set_rq_online(struct rq*);
#endif

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 6, 0)
static void __mod_register_sched_domain_sysctl(void) { }
static void __mod_unregister_sched_domain_sysctl(void) { }
static void __orig_register_sched_domain_sysctl(void) { }
static void __orig_unregister_sched_domain_sysctl(void) { }
#else
extern void __mod_register_sched_domain_sysctl(void);
extern void __mod_unregister_sched_domain_sysctl(void);
extern void __orig_register_sched_domain_sysctl(void);
extern void __orig_unregister_sched_domain_sysctl(void);
#endif
#endif /* _H_FUTURE */