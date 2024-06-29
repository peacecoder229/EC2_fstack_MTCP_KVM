/*****************XDP Related Stuff *************************/
#ifndef __XDP_MODULE_H
#define __XDP_MODULE_H

#include <unistd.h>
#include <linux/bpf.h>
#include <linux/if_xdp.h>
#include <linux/if_link.h>
#include <linux/compiler.h>
#include <asm/barrier.h>
#include <sys/resource.h>
#include <net/if.h>
#include <errno.h>
#include "bpf/libbpf.h"
#include "bpf/xsk.h"
#include <bpf/bpf.h>
#include <poll.h>
#include "./include/mtcp.h"
/*------------------------ XDP -----------------------------------------------*/
#define NUM_FRAMES (4 * 1024)
#define BATCH_SIZE 64
#define MAX_SOCKS 1
#define ETHERNET_FRAME_SIZE     1514

struct xsk_umem_info {
        struct xsk_ring_prod fq;
        struct xsk_ring_cons cq;
        struct xsk_umem *umem;
        void *buffer;
};

struct xsk_socket_info {
        struct xsk_ring_cons rx;
        struct xsk_ring_prod tx;
        struct xsk_umem_info *umem;
        struct xsk_socket *xsk;
        unsigned long rx_npkts;
        unsigned long tx_npkts;
        unsigned long prev_rx_npkts;
        unsigned long prev_tx_npkts;
        unsigned int outstanding_tx;
};

extern __u32 prog_id;


extern struct mtcp_manager *mtcp;
extern struct mtcp_thread_context ctx;
extern int queue;
extern char if_name[50];


struct xdp_private_context{

        struct xsk_socket_info *xsks_private;
        /* Variables for RX */
        __u32 idx_rx;
        __u32 idx_fq;
        __u32 rcvd;

	struct pollfd rxpfds[1]; 
	int opt_poll[1];
        /*Variables for TX */
        __u32 idx_tx;
	__u32 tx_count;

};

static struct xsk_umem_info *xsk_configure_umem(void *buffer, __u64 size);
static struct xsk_socket_info *xsk_configure_socket(struct xsk_umem_info *umem);
void xdp_init_handle(struct mtcp_thread_context *ctxt);
static void kick_tx(struct xsk_socket_info *xsk);
static inline void complete_tx_only(struct xsk_socket_info *xsk);
int xdp_send_pkts(struct mtcp_thread_context *ctxt, int ifidx);
uint8_t *xdp_get_wptr(struct mtcp_thread_context *ctxt, int ifidx, uint16_t pktsize);
int xdp_recv_pkts(struct mtcp_thread_context *ctxt, int ifidx);
uint8_t *xdp_get_rptr(struct mtcp_thread_context *ctxt, int ifidx, int index, uint16_t *len);
void xdp_release_pkt(struct mtcp_thread_context *ctxt, int ifidx, unsigned char *pkt_data, int len);
int32_t xdp_select(struct mtcp_thread_context *ctxt);
void remove_xdp_program(void);

#endif
