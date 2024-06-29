# mtcpxdpmodule


Checkout and then 

cd mtcpxdpm

app.c --> Application Code
xdp_module.c and xdp_module.h --> xdp and mtcp related code

You can run the make and it should generate app

Make sure that you have installed the linux source/headers for your kernel version and you have also installed libbpf.a


## To run the application 

./app <r|t|l> <interface name> <queue number>

If you want to run in the recieve mode use the following command:

./app r ens1f1 0

The above command runs the application in receive mode over interface ens1f1 and queue 0

For transmit run the following command:

./app t ens1f1 0

