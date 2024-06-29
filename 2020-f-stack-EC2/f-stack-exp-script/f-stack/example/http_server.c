#include <sys/types.h>
#include <sys/socket.h>
#include <sys/epoll.h>
#include <netinet/in.h>

#include <fcntl.h>
#include <signal.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define MAX_EVENTS 10
#define MAXBUF  1024

#define handle_error(msg) \
           do { perror(msg); exit(EXIT_FAILURE); } while (0)

char *reply =
"HTTP/1.1 200 OK\n"
"Date: Thu, 19 Feb 2009 12:27:04 GMT\n"
"Server: Apache/2.2.3\n"
"Last-Modified: Wed, 18 Jun 2003 16:05:58 GMT\n"
"ETag: \"56d-9989200-1132c580\"\n"
"Content-Type: text/html\n"
"Content-Length: 15\n"
"Accept-Ranges: bytes\n"
"Connection: close\n"
"\n"
"sdfkjsdnbfkjbsf";

int setnonblocking(int fd)
{
    int flags;
    if (-1 == (flags = fcntl(fd, F_GETFL, 0)))
        flags = 0;
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

void do_use_fd(int epoll_fd, int fd)
{
    char buffer[MAXBUF];
    int len = strlen(reply);
    send(fd, reply, len, 0);

    if (epoll_ctl(epoll_fd, EPOLL_CTL_DEL, fd, NULL) == -1)
       handle_error("epoll delete");

    close(fd);
}

void run()
{
    struct epoll_event ev, events[MAX_EVENTS];
    struct sockaddr_in my_addr;
    struct sockaddr_in peer_addr;
    char buffer[MAXBUF];
    int listen_sock, conn_sock, nfds, epoll_fd;
    int n = 0;


    listen_sock = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_sock == -1)
        handle_error("socket");

    memset(&peer_addr, 0, sizeof(struct sockaddr_in));
    memset(&my_addr, 0, sizeof(struct sockaddr_in));
    int addrlen= sizeof(peer_addr);

    my_addr.sin_family = AF_INET;
    my_addr.sin_port = htons(9001);
    my_addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(listen_sock , (struct sockaddr*)&my_addr,
         sizeof my_addr) != 0)
        handle_error("bind");

    if(listen(listen_sock, 20) != 0)
        handle_error("listen");

    /* Initialize the epoll */
    epoll_fd = epoll_create(10);
    if (epoll_fd == -1) {
        handle_error("epoll_create");
    }

    ev.events = EPOLLIN;
    ev.data.fd = listen_sock;

    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, listen_sock, &ev) == -1)
        handle_error("epoll_ctl: listen_sock");

    for (;;) {

        nfds = epoll_wait(epoll_fd, events, MAX_EVENTS, -1);
        if (nfds == -1)
            handle_error("epoll_wait");

         for (n = 0; n < nfds ; ++n) {
             if (events[n].data.fd == listen_sock) {
                 conn_sock = accept(listen_sock,
                     (struct sockaddr*) &peer_addr, &addrlen);
             if (conn_sock == -1)
                 handle_error("accept");
             setnonblocking(conn_sock);
             printf("%s:%d connected\n",
                 inet_ntoa(peer_addr.sin_addr), ntohs(peer_addr.sin_port));
             ev.events = EPOLLIN | EPOLLET;
             ev.data.fd = conn_sock;
             if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, conn_sock,
                 &ev) == -1)
                 handle_error("epoll_ctl: conn_sock");
             } else {
                 do_use_fd(epoll_fd, events[n].data.fd);
             }
         }
    }
}

int main()
{
    signal(SIGPIPE, SIG_IGN);
    run();
    exit (0);
}
