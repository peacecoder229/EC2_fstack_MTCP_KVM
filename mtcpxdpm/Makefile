# SPDX-License-Identifier: GPL-2.0
app: app.o xdp_module.o
	gcc -pthread -o app app.o xdp_module.o /usr/src/linux-`uname -r`/tools/lib/bpf/libbpf.a -lelf	

app.o: app.c
	gcc -pthread -Wall -c -O3 -I/usr/src/linux-`uname -r`/tools/lib/ -I/usr/src/linux-`uname -r`/tools/include app.c
xdp_module.o: xdp_module.c
	gcc -pthread -Wall -c -O3 -I/usr/src/linux-`uname -r`/tools/lib/ -I/usr/src/linux-`uname -r`/tools/include xdp_module.c

clean: 
	rm -rf *.o app
