#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include "./include/mtcp.h"
#include <signal.h>
#include "xdp_module.h"

int queue;
char if_name[50];

//unsigned char tx_buf[62] = {60, -3, -2, -91, 67, 91, 60, -3, -2, -91, 82, 17, 8, 0, 69, 16, 0, 48, -44, 49, 0, 0, 10, 17, 89, -113, -64, -88, 0, -44, -64, -88, 0, -56, 16, -110, 16, -110, 0, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -34, -83, -66, -17, -34, -83, -66, -17}; 

static const char tx_buf[] =
	"\x3c\xfd\xfe\x9e\x7f\x71\xec\xb1\xd7\x98\x3a\xc0\x08\x00\x45\x00"
	"\x00\x2e\x00\x00\x00\x00\x40\x11\x88\x97\x05\x08\x07\x08\xc8\x14"
	"\x1e\x04\x10\x92\x10\x92\x00\x1a\x6d\xa3\x34\x33\x1f\x69\x40\x6b"
	"\x54\x59\xb6\x14\x2d\x11\x44\xbf\xaf\xd9\xbe\xaa";

/*-----------------------------------------------------------------------------------------*/
/* total cpus detected in the mTCP stack*/
int num_queues;
int num_devices;

int num_devices_attached;

__u32 prog_id;
/*struct mtcp_config CONFIG = {
			     .multi_process = 0,
			     .multi_process_is_master = 0		     .num_cores = 1,
			     .max_concurrency = 8192
};*/
static void int_exit(int sig)
{
   
   remove_xdp_program();

   exit(EXIT_SUCCESS);
}


uint8_t *pkt = NULL; 
struct mtcp_manager *mtcp;
struct mtcp_thread_context ctx;
unsigned char dst[1600];


/*-----------------------------------------------------------------------------------------*/
int
main(int argc, char **argv)
{
  
  int total_cnt = 0;
  int rcv_cnt = 0;
  ctx.thread  = pthread_self();
  ctx.cpu = 1;

  if (argc != 4) {
    fprintf(stderr, "Usage: %s <rx|tx|loopback> <device> <queue number> \n", argv[0]);
    exit(EXIT_FAILURE);
  }
  
  signal(SIGINT, int_exit);
  signal(SIGTERM, int_exit);
  signal(SIGABRT, int_exit);
	

  mtcp = calloc(1, sizeof(struct mtcp_manager));
  if (mtcp == NULL) {
    fprintf(stderr, "Can't allocat memory for mtcp!\n");
    exit(EXIT_FAILURE);
  }

  ctx.mtcp_manager = mtcp;
  ctx.thread = pthread_self();
    
  num_queues = 1;

  //fprintf(stderr, "# of devices attached: %d\n", num_devices_attached);

  queue = atoi(argv[3]);
  strcpy(if_name, argv[2]);	 	



  xdp_init_handle(&ctx);
 
  

  if (argv[1][0] == 'r') {

    while (1) {
      
      int i, j;
      uint16_t len;
            
      if(xdp_select(&ctx) <= 0)
	continue;
      rcv_cnt = xdp_recv_pkts(&ctx, 0);
     

      for (i = 0; i < rcv_cnt; i++) {
	pkt = (uint8_t *)xdp_get_rptr(&ctx, 0, i, &len);
	if(pkt == NULL){
		printf("Did not read any data \n");
		exit(0);
	}
	//fprintf(stderr, "%d: Got a pkt of %u size \n", total_cnt, len);
	//print received data 
	/*for (j = 0; j < len; j++){
		fprintf(stderr, "%02X ", pkt[j]);
	}
	printf("\n");*/
        total_cnt += 1;
      }
      if (rcv_cnt > 0){
	xdp_release_pkt(&ctx, 0, NULL, 0);
      }
      
    }
  } else if (argv[1][0] == 't') {
    	uint8_t *pkt;
	int i = 0;
        //xdp_send_pkts(&ctx, 0);
	for (;;){
		pkt = xdp_get_wptr(&ctx, 0, 60);
		if(pkt != NULL){ // if there is space write the packet
			// copy first few times and then keep transmitting whatever we have	
			if( i < 4){
    				memcpy(pkt, tx_buf , sizeof(tx_buf) - 1 );
    				i++;
			}
		}else{ // else send the packets trigger tx
			xdp_send_pkts(&ctx, 0); 
		}	
		
	}
 
  } else if (argv[1][0] == 'l') {
	uint8_t *rx_pkt;
	uint8_t *tx_pkt;
	int i = 0;
	uint16_t len = 0;
	while (1){
		
      		if(xdp_select(&ctx) <= 0)
			continue;	
		rcv_cnt = xdp_recv_pkts(&ctx, 0);
 
 		for (i = 0; i < rcv_cnt; i++) {
          		rx_pkt = (uint8_t *)xdp_get_rptr(&ctx, 0, i, &len);
          		if(rx_pkt == NULL){
                  		printf("Did not read any data \n");
                  		exit(0);
          		}
			tx_pkt = xdp_get_wptr(&ctx, 0, len);
			if(tx_pkt == NULL){
				do{
					xdp_send_pkts(&ctx, 0);
					tx_pkt = xdp_get_wptr(&ctx, 0, len);
				} while(tx_pkt == NULL);
			}
			memcpy(tx_pkt, rx_pkt, len);
		}
		if(rcv_cnt > 0){
			xdp_release_pkt(&ctx, 0, NULL, 0);
			xdp_send_pkts(&ctx, 0);
		}

	}	

  }

  remove_xdp_program();

  return EXIT_SUCCESS;
  
}
/*-----------------------------------------------------------------------------------------*/
