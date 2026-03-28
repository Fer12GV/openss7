/*
 * compat-kernel.h - Capa de compatibilidad para compilar OpenSS7 en kernels 5.x+
 *
 * Este archivo es parte de la infraestructura de deploy, NO del codigo fuente OpenSS7.
 * Se incluye automaticamente via gcc -include antes de cualquier otro header.
 *
 * Resuelve cambios de API del kernel Linux que rompen la compilacion de OpenSS7:
 * - f_dentry removido de struct file (kernel 4.18+)
 * - MODULE_SUPPORTED_DEVICE() removido (kernel 5.12+)
 * - time_t/timeval/timespec removidos de kernel headers (kernel 5.0+)
 * - getnstimeofday() removido (kernel 5.0+)
 * - proc_create_data() ahora espera struct proc_ops * (kernel 5.6+)
 * - lock_kernel()/unlock_kernel() removidos (kernel 2.6.39+)
 * - HAVE_COMPAT_IOCTL no generado por autotools (mapping de defines roto)
 * - set_task_state() usa task->state que fue renombrado a __state (kernel 5.14+)
 * - csum_and_copy_from_user() cambio de 5 a 3 argumentos (kernel 5.10+)
 * - dst_ops::negative_advice cambio de firma (kernel 5.15+)
 */
#ifndef _OPENSS7_COMPAT_KERNEL_H
#define _OPENSS7_COMPAT_KERNEL_H

#include <linux/version.h>

/*
 * Las siguientes secciones solo aplican en contexto kernel (__KERNEL__).
 * En userspace, este header es un no-op seguro.
 */
#ifdef __KERNEL__

/*
 * --- dst_ops::negative_advice cambio de firma (kernel 5.15+) ---
 *
 * DEBE estar al INICIO del bloque __KERNEL__, antes de cualquier #include.
 * Razon: linux/netdevice.h (incluido mas abajo) incluye transitivamente
 * net/dst_ops.h. Si el guard _NET_DST_OPS_H no esta definido cuando eso
 * ocurre, el real struct dst_ops (con la nueva firma) se procesa primero
 * y nuestro compat llega tarde.
 *
 * Solucion: incluir linux/percpu_counter.h (dependencia de struct dst_ops),
 * definir _NET_DST_OPS_H y nuestro struct dst_ops AQUI, para que todos los
 * includes posteriores encuentren el guard ya establecido.
 *
 * negative_advice como void*(*)(void*, ...):
 *   - API vieja (sctp2.c): *dst_p = ops->negative_advice(dst)  → compila
 *   - API nueva (sock.h):  ops->negative_advice(sk, dst)        → compila
 *   - En C, void* es implicitamente convertible a cualquier puntero.
 *   - Mismo tamano de puntero: no hay ABI mismatch en el layout del struct.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 15, 0)

#include <linux/percpu_counter.h>
#include <linux/cache.h>

/* Forward declarations (igual que en el real net/dst_ops.h) */
struct dst_entry;
struct kmem_cachep;
struct net_device;
struct sk_buff;
struct sock;
struct net;
struct neighbour;
struct kmem_cache;

/*
 * Definimos _NET_DST_OPS_H AQUI para que cualquier include posterior
 * (incluyendo los del propio compat-kernel.h) omita el real dst_ops.h.
 */
#define _NET_DST_OPS_H

struct dst_ops {
	unsigned short		family;
	unsigned int		gc_thresh;

	void			(*gc)(struct dst_ops *ops);
	struct dst_entry *	(*check)(struct dst_entry *, __u32 cookie);
	unsigned int		(*default_advmss)(const struct dst_entry *);
	unsigned int		(*mtu)(const struct dst_entry *);
	u32 *			(*cow_metrics)(struct dst_entry *, unsigned long);
	void			(*destroy)(struct dst_entry *);
	void			(*ifdown)(struct dst_entry *,
					  struct net_device *dev, int how);
	/*
	 * Puntero variadic: acepta la API vieja (1 arg, retorna void*) y
	 * la nueva (2 args, void). Mismo layout binario que cualquier fn ptr.
	 */
	void *			(*negative_advice)(void *, ...);
	void			(*link_failure)(struct sk_buff *);
	void			(*update_pmtu)(struct dst_entry *dst, struct sock *sk,
					       struct sk_buff *skb, u32 mtu,
					       bool confirm_neigh);
	void			(*redirect)(struct dst_entry *dst, struct sock *sk,
					    struct sk_buff *skb);
	int			(*local_out)(struct net *net, struct sock *sk, struct sk_buff *skb);
	struct neighbour *	(*neigh_lookup)(const struct dst_entry *dst,
						struct sk_buff *skb,
						const void *daddr);
	void			(*confirm_neigh)(const struct dst_entry *dst,
						 const void *daddr);

	struct kmem_cache	*kmem_cachep;

	struct percpu_counter	pcpuc_entries ____cacheline_aligned_in_smp;
};

static inline int dst_entries_get_fast(struct dst_ops *dst)
{
	return percpu_counter_read_positive(&dst->pcpuc_entries);
}

static inline int dst_entries_get_slow(struct dst_ops *dst)
{
	return percpu_counter_sum_positive(&dst->pcpuc_entries);
}

#define DST_PERCPU_COUNTER_BATCH 32
static inline void dst_entries_add(struct dst_ops *dst, int val)
{
	percpu_counter_add_batch(&dst->pcpuc_entries, val,
				 DST_PERCPU_COUNTER_BATCH);
}

static inline int dst_entries_init(struct dst_ops *dst)
{
	return percpu_counter_init(&dst->pcpuc_entries, 0, GFP_KERNEL);
}

static inline void dst_entries_destroy(struct dst_ops *dst)
{
	percpu_counter_destroy(&dst->pcpuc_entries);
}

#endif /* LINUX_VERSION_CODE >= KERNEL_VERSION(5, 15, 0) */

/*
 * --- Suprimir warnings que el kernel 5.x trata como errores ---
 * OpenSS7 es codigo legacy con muchos switch fallthrough intencionales
 * y patterns que generan warnings en gcc moderno.
 * Sin esto, -Werror del kernel convierte warnings en errores fatales.
 */
#pragma GCC diagnostic ignored "-Wimplicit-fallthrough"
#pragma GCC diagnostic ignored "-Wstringop-overread"
#pragma GCC diagnostic ignored "-Warray-bounds"
#pragma GCC diagnostic ignored "-Wstringop-overflow"
#pragma GCC diagnostic ignored "-Wattributes"

/* --- f_dentry -> f_path.dentry (kernel 4.18+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 18, 0)
#define f_dentry f_path.dentry
#endif

/* --- MODULE_SUPPORTED_DEVICE removido (kernel 5.12+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 12, 0)
#ifndef MODULE_SUPPORTED_DEVICE
#define MODULE_SUPPORTED_DEVICE(x)
#endif
#endif

/* --- time_t removido de kernel headers (kernel 5.0+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)
#ifndef _COMPAT_TIME_TYPES
#define _COMPAT_TIME_TYPES
typedef long time_t;
#endif
#endif

/* --- struct timeval/timespec removidos (kernel 5.6+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
#ifndef _COMPAT_TIMEVAL
#define _COMPAT_TIMEVAL
struct timeval {
	long tv_sec;
	long tv_usec;
};
#endif
#ifndef _COMPAT_TIMESPEC
#define _COMPAT_TIMESPEC
struct timespec {
	long tv_sec;
	long tv_nsec;
};
#endif
#endif /* >= 5.6.0 */

/* --- getnstimeofday() removido (kernel 5.0+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)
#include <linux/ktime.h>
#define getnstimeofday(ts) do {				\
	struct timespec64 __ts64;			\
	ktime_get_real_ts64(&__ts64);			\
	(ts)->tv_sec  = (long)__ts64.tv_sec;		\
	(ts)->tv_nsec = __ts64.tv_nsec;			\
} while (0)
#endif

/* --- do_gettimeofday() removido (kernel 5.0+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 0, 0)
#define do_gettimeofday(tv) do {			\
	struct timespec64 __ts64;			\
	ktime_get_real_ts64(&__ts64);			\
	(tv)->tv_sec  = (long)__ts64.tv_sec;		\
	(tv)->tv_usec = __ts64.tv_nsec / 1000;		\
} while (0)
#endif

/* --- lock_kernel/unlock_kernel (BKL) removido (kernel 2.6.39+) --- */
#ifndef lock_kernel
#define lock_kernel()   do {} while (0)
#endif
#ifndef unlock_kernel
#define unlock_kernel() do {} while (0)
#endif

/*
 * --- HAVE_COMPAT_IOCTL no generado por autotools ---
 * El configure detecta struct file_operations.compat_ioctl como
 * HAVE_KMEMB_STRUCT_FILE_OPERATIONS_COMPAT_IOCTL, pero el codigo
 * fuente busca HAVE_COMPAT_IOCTL. Definimos el mapping.
 * En kernel 2.6.11+ compat_ioctl siempre existe.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(2, 6, 11)
#ifndef HAVE_COMPAT_IOCTL
#define HAVE_COMPAT_IOCTL 1
#endif
#endif

/*
 * --- set_task_state() / task->state renombrado a __state (kernel 5.14+) ---
 * OpenSS7 sth.c define su propio set_task_state usando (tsk)->state.
 * Definimos HAVE_KMACRO_SET_TASK_STATE para que sth.c salte su definicion,
 * y proveemos una version que usa __state.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 14, 0)
#include <linux/sched.h>
#define HAVE_KMACRO_SET_TASK_STATE 1
#define set_task_state(tsk, state_value) \
	WRITE_ONCE((tsk)->__state, (state_value))
#endif

/*
 * --- csum_and_copy_from_user() cambio de firma (kernel 5.10+) ---
 * Antes: __wsum csum_and_copy_from_user(src, dst, len, sum, err_ptr) — 5 args
 * Ahora: __wsum csum_and_copy_from_user(src, dst, len) — 3 args
 * OpenSS7 usa la version de 5 args. Proveemos un wrapper.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
#include <net/checksum.h>
static inline __wsum
__compat_csum_and_copy_from_user(const void __user *src, void *dst,
				 int len, __wsum sum, int *err_ptr)
{
	__wsum result = csum_and_copy_from_user(src, dst, len);
	if (err_ptr)
		*err_ptr = 0;
	return csum_add(result, sum);
}
#undef csum_and_copy_from_user
#define csum_and_copy_from_user __compat_csum_and_copy_from_user
#endif

/*
 * --- net_device.queue_lock removido (kernel 4.x+) ---
 * ldl.c usa START_BH_ATOMIC/END_BH_ATOMIC con dev->queue_lock.
 * Redirigimos a addr_list_lock que es un spinlock existente en net_device.
 */
#include <linux/netdevice.h>
#if LINUX_VERSION_CODE >= KERNEL_VERSION(4, 0, 0)
#define queue_lock addr_list_lock
#endif

/*
 * --- get_fs/set_fs/KERNEL_DS removidos (kernel 5.10+, CONFIG_SET_FS) ---
 * Codigo legacy usa set_fs(KERNEL_DS) para acceder buffers kernel via
 * funciones de socket. En kernels modernos, las funciones kernel_sendmsg/
 * kernel_recvmsg manejan esto internamente. No-ops como compat.
 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 10, 0)
#include <linux/thread_info.h>
#ifndef KERNEL_DS
/* mm_segment_t puede existir en thread_info pero get_fs/set_fs no */
#define KERNEL_DS	((mm_segment_t){0})
#define USER_DS		((mm_segment_t){0})
#define get_fs()	(KERNEL_DS)
#define set_fs(x)	do { (void)(x); } while (0)
#endif
#endif

/* --- proc_ops reemplazo file_operations para /proc (kernel 5.6+) --- */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)

#include <linux/proc_fs.h>
#include <linux/string.h>

/*
 * proc_create_data() ahora espera struct proc_ops * en vez de
 * struct file_operations *. Como no podemos modificar el codigo fuente,
 * interceptamos la llamada y convertimos automaticamente.
 *
 * Usamos un array estatico de proc_ops para almacenar las conversiones.
 * OpenSS7 registra ~15 entradas proc, 32 es suficiente margen.
 */
#define _COMPAT_MAX_PROC_OPS 32

static struct proc_ops _compat_proc_ops_arr[_COMPAT_MAX_PROC_OPS];
static int _compat_proc_ops_idx;

/* Guardamos referencia a la funcion real antes de redefinir el nombre */
static inline struct proc_dir_entry *
__real_proc_create_data(const char *name, umode_t mode,
                        struct proc_dir_entry *parent,
                        const struct proc_ops *ops,
                        void *data)
{
	return proc_create_data(name, mode, parent, ops, data);
}

/* Ahora redefinimos proc_create_data para interceptar las llamadas */
#undef proc_create_data
#define proc_create_data _compat_proc_create_data

static inline struct proc_dir_entry *
_compat_proc_create_data(const char *name, umode_t mode,
                         struct proc_dir_entry *parent,
                         const struct file_operations *fops,
                         void *data)
{
	struct proc_ops *pops;

	if (_compat_proc_ops_idx >= _COMPAT_MAX_PROC_OPS)
		return NULL;

	pops = &_compat_proc_ops_arr[_compat_proc_ops_idx++];
	memset(pops, 0, sizeof(*pops));

	if (fops) {
		pops->proc_open    = fops->open;
		pops->proc_read    = fops->read;
		pops->proc_write   = fops->write;
		pops->proc_lseek   = fops->llseek;
		pops->proc_release = fops->release;
		pops->proc_poll    = fops->poll;
	}

	return __real_proc_create_data(name, mode, parent, pops, data);
}

#endif /* KERNEL_VERSION >= 5.6.0 */

#endif /* __KERNEL__ */

#endif /* _OPENSS7_COMPAT_KERNEL_H */
