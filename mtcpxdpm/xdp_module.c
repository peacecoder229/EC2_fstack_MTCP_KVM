#include <stdlib.h>
#include <string.h>
#include "xdp_module.h"

#define DEBUG 1

#ifdef DEBUG
#include <pthread.h>
#include <time.h>
struct xsk_socket_info *xsks[MAX_SOCKS];

static unsigned long prev_time = 0;
static unsigned long get_nsecs(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec * 1000000000UL + ts.tv_nsec;
}
static void dump_stats(void)
{
	unsigned long now = get_nsecs();
	long dt = now - prev_time;
	int i;
	
	prev_time = now;
	
	int num_socks = 1;
	for (i = 0; i < num_socks; i++) {
		char *fmt = "%-15s %'-11.0f %'-11lu\n";
		double rx_pps, tx_pps;

		rx_pps = (xsks[i]->rx_npkts - xsks[i]->prev_rx_npkts) *
			 1000000000. / dt;
		tx_pps = (xsks[i]->tx_npkts - xsks[i]->prev_tx_npkts) *
			 1000000000. / dt;

		printf("\n sock%d@ %lu %lu %lu", i, dt, xsks[i]->tx_npkts, xsks[i]->prev_tx_npkts);
		printf("\n");

		printf("%-15s %-11s %-11s %-11.2f\n", "", "pps", "pkts",
		       dt / 1000000000.);
		printf(fmt, "rx", rx_pps, xsks[i]->rx_npkts);
		printf(fmt, "tx", tx_pps, xsks[i]->tx_npkts);
		
		xsks[i]->prev_rx_npkts = xsks[i]->rx_npkts;
		xsks[i]->prev_tx_npkts = xsks[i]->tx_npkts;
	}

}
static void *poller(void *arg)
{
	(void)arg;
	for (;;) {
		sleep(1);
		dump_stats();
	}

	return NULL;
}
#endif

static struct
xsk_umem_info *xsk_configure_umem(void *buffer, __u64 size)
{
        struct xsk_umem_info *umem;
        int ret;

        umem = calloc(1, sizeof(*umem));
        if (!umem)
                exit(EXIT_FAILURE);

        ret = xsk_umem__create(&umem->umem, buffer, size, &umem->fq, &umem->cq,
                               NULL);
        if (ret)
                exit(EXIT_FAILURE);

        umem->buffer = buffer;
        return umem;
}

static struct
xsk_socket_info *xsk_configure_socket(struct xsk_umem_info *umem)
{
        struct xsk_socket_config cfg;
        struct xsk_socket_info *xsk;
        int ret;
        __u32 idx;
        int i;


        xsk = calloc(1, sizeof(*xsk));
        if (!xsk)
                exit(EXIT_FAILURE);

        xsk->umem = umem;
        cfg.rx_size = XSK_RING_CONS__DEFAULT_NUM_DESCS;
        cfg.tx_size = XSK_RING_PROD__DEFAULT_NUM_DESCS;
        cfg.libbpf_flags = 0;
        cfg.xdp_flags = XDP_FLAGS_DRV_MODE; ///opt_xdp_flags;
        cfg.bind_flags = XDP_ZEROCOPY;//opt_xdp_bind_flags;

        ret = xsk_socket__create(&xsk->xsk, if_name, queue, umem->umem, &xsk->rx, &xsk->tx, &cfg);
        if (ret){
                printf("Socket Create Failed \n");
                exit(EXIT_FAILURE);
        }


        ret = bpf_get_link_xdp_id(if_nametoindex(if_name), &prog_id, XDP_FLAGS_DRV_MODE);
        if (ret)
                exit(EXIT_FAILURE);

        ret = xsk_ring_prod__reserve(&xsk->umem->fq,
                                     XSK_RING_PROD__DEFAULT_NUM_DESCS,
                                     &idx);
        if (ret != XSK_RING_PROD__DEFAULT_NUM_DESCS)
                exit(EXIT_FAILURE);

        for (i = 0; i < XSK_RING_PROD__DEFAULT_NUM_DESCS * XSK_UMEM__DEFAULT_FRAME_SIZE; i += XSK_UMEM__DEFAULT_FRAME_SIZE)
                *xsk_ring_prod__fill_addr(&xsk->umem->fq, idx++) = i;

        xsk_ring_prod__submit(&xsk->umem->fq,
                              XSK_RING_PROD__DEFAULT_NUM_DESCS);

        return xsk;
}

void
xdp_init_handle(struct mtcp_thread_context *ctxt)
{

        struct  rlimit r = {RLIM_INFINITY, RLIM_INFINITY};
        struct  xsk_umem_info *umem;
        void    *bufs;
        int     ret;
        struct xdp_private_context *xdpc;
        int i = 0;
        int timeout;

	pthread_t pt;


        ctxt->io_private_context = (void *)calloc(1, sizeof(struct xdp_private_context));
        if (ctxt->io_private_context == NULL) {
                //TRACE_ERROR("Failed to initialize ctxt->io_private_context: "
                            //"Can't allocate memory\n");
                exit(EXIT_FAILURE);
        }

        xdpc = (struct xdp_private_context *)ctxt->io_private_context;


        if (setrlimit(RLIMIT_MEMLOCK, &r)) {
                fprintf(stderr, "ERROR: setrlimit(RLIMIT_MEMLOCK) \"%s\"\n",
                        strerror(errno));
                exit(EXIT_FAILURE);
        }
        // Get a user space buffer
        ret = posix_memalign(&bufs, getpagesize(),
                             NUM_FRAMES * XSK_UMEM__DEFAULT_FRAME_SIZE);

        if(ret){
                printf("Memory alignment failed \n");
                exit(EXIT_FAILURE);
        }


         /* Create sockets...  using user  space nuffer*/
        umem = xsk_configure_umem(bufs,
                                  NUM_FRAMES * XSK_UMEM__DEFAULT_FRAME_SIZE);

        xdpc->xsks_private = xsk_configure_socket(umem);


        printf("***** Completed xdp_init_handle ***** \n");

       
        memset(xdpc->rxpfds, 0, sizeof(xdpc->rxpfds));
        for (i = 0; i < 1; i++) {
                xdpc->rxpfds[i].fd = xsk_socket__fd(xdpc->xsks_private->xsk);
                xdpc->rxpfds[i].events = POLLIN;
        }
	xdpc->opt_poll[0] = 1;
#ifdef DEBUG
        xsks[0] = xdpc->xsks_private;
	xsks[0]->tx_npkts = 0;
        xsks[0]->prev_rx_npkts = 0;
	ret = pthread_create(&pt, NULL, poller, NULL);
	if (ret){
		printf("Warning: Cannot debug correctly \n"); // still continue to run code
	}
        prev_time = get_nsecs();
#endif
}


static void kick_tx(struct xsk_socket_info *xsk)
{
        int ret;
        //printf("kick \n");
        ret = sendto(xsk_socket__fd(xsk->xsk), NULL, 0, MSG_DONTWAIT, NULL, 0);
        if (ret >= 0 || errno == ENOBUFS || errno == EAGAIN || errno == EBUSY)
                return;
        exit(0);
}

static inline void complete_tx_only(struct xsk_socket_info *xsk)
{
        unsigned int rcvd;
        __u32 idx;

        if (!xsk->outstanding_tx)
                return;

        kick_tx(xsk);

        rcvd = xsk_ring_cons__peek(&xsk->umem->cq, BATCH_SIZE, &idx);
        if (rcvd > 0) {
                xsk_ring_cons__release(&xsk->umem->cq, rcvd);
                xsk->outstanding_tx -= rcvd;
                xsk->tx_npkts += rcvd;
	        xsks[0]->tx_npkts += rcvd; 
		//printf("%d \n", rcvd);
        }
}


int
xdp_send_pkts(struct mtcp_thread_context *ctxt, int ifidx)
{
	struct xdp_private_context *xdpc;

	xdpc = (struct xdp_private_context *) ctxt->io_private_context;
	
	if(xdpc->tx_count > 0){
		xsk_ring_prod__submit(&xdpc->xsks_private->tx, xdpc->tx_count);
		xdpc->xsks_private->outstanding_tx += xdpc->tx_count;
		xdpc->tx_count = 0;
	}
	complete_tx_only(xdpc->xsks_private);
	
        return 0;
}

uint8_t *
xdp_get_wptr(struct mtcp_thread_context *ctxt, int ifidx, uint16_t pktsize)
{
        struct xdp_private_context *xdpc;
        __u32 idx;

        xdpc = (struct xdp_private_context *) ctxt->io_private_context;

	if(xdpc->tx_count > BATCH_SIZE)
		return NULL;
		

        if (xsk_ring_prod__reserve(&xdpc->xsks_private->tx, 1, &idx) == 1){

                xsk_ring_prod__tx_desc(&xdpc->xsks_private->tx, idx)->len = pktsize;
        	xdpc->tx_count += 1;
	        return xsk_umem__get_data(xdpc->xsks_private->umem->buffer, xsk_ring_prod__tx_desc(&xdpc->xsks_private->tx, idx)->addr);
        
	}
		
        return NULL;

}

int
xdp_recv_pkts(struct mtcp_thread_context *ctxt, int ifidx)
{

        int rcvd;
        __u32 idx_rx = 0;
        __u32 idx_fq = 0;
        int rtrn = 0;

        struct xdp_private_context *xdpc;

        xdpc = (struct xdp_private_context *) ctxt->io_private_context;

        rcvd = xsk_ring_cons__peek(&xdpc->xsks_private->rx, BATCH_SIZE, &idx_rx);
        if (!rcvd){
                return 0;
        }

        rtrn = xsk_ring_prod__reserve(&xdpc->xsks_private->umem->fq, rcvd, &idx_fq);
        while (rtrn != rcvd) {
                if (rtrn < 0)
                        exit(0);
                rtrn = xsk_ring_prod__reserve(&xdpc->xsks_private->umem->fq, rcvd, &idx_fq);
        }

        xdpc->idx_fq = idx_fq;
        xdpc->idx_rx = idx_rx;
        xdpc->rcvd   = rcvd;
	xsks[0]->rx_npkts += rcvd; 
        return rcvd; // Return the number of packets to the mtcp thread

}

uint8_t *
xdp_get_rptr(struct mtcp_thread_context *ctxt, int ifidx, int index, uint16_t *len)
{


        struct xdp_private_context *xdpc;
	
        xdpc = (struct xdp_private_context *) ctxt->io_private_context;

        __u64 addr = xsk_ring_cons__rx_desc(&xdpc->xsks_private->rx, xdpc->idx_rx)->addr;
        *len = xsk_ring_cons__rx_desc(&xdpc->xsks_private->rx, xdpc->idx_rx++)->len;

        *xsk_ring_prod__fill_addr(&xdpc->xsks_private->umem->fq, xdpc->idx_fq++) = addr;

        
        return (uint8_t *)xsk_umem__get_data(xdpc->xsks_private->umem->buffer, addr);
}

void
xdp_release_pkt(struct mtcp_thread_context *ctxt, int ifidx, unsigned char *pkt_data, int len)
{
        /*
         * do nothing over here - memory reclamation
         * will take place in dpdk_recv_pkts
         */
        struct xdp_private_context *xdpc;

        xdpc = (struct xdp_private_context *) ctxt->io_private_context;

        xsk_ring_prod__submit(&xdpc->xsks_private->umem->fq, xdpc->rcvd);//
        xsk_ring_cons__release(&xdpc->xsks_private->rx, xdpc->rcvd);//

        xdpc->idx_fq = 0;
        xdpc->idx_rx = 0;
        xdpc->rcvd   = 0;

}

int32_t
xdp_select(struct mtcp_thread_context *ctxt)
{
	int timeout = 1000;
	int nfds = 1;
	int ret = 10;
	
	struct xdp_private_context *xdpc;

	xdpc = (struct xdp_private_context *) ctxt->io_private_context;

        if(xdpc->opt_poll[0]){
                ret = poll(xdpc->rxpfds, nfds, timeout);
        }

        return ret;
}


void remove_xdp_program(void)
{
        __u32 curr_prog_id = 0;

        if (bpf_get_link_xdp_id(if_nametoindex("ens1f1"), &curr_prog_id, XDP_FLAGS_DRV_MODE)) {
                printf("bpf_get_link_xdp_id failed\n");
                exit(EXIT_FAILURE);
        }
        if (prog_id == curr_prog_id)
                bpf_set_link_xdp_fd(if_nametoindex("ens1f1"), -1, XDP_FLAGS_DRV_MODE);
        else if (!curr_prog_id)
                printf("couldn't find a prog id on a given interface\n");
        else
                printf("program on interface changed, not removing\n");
}

