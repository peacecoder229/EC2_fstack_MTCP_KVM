
default:	build

clean:
	rm -rf Makefile objs

build:
	$(MAKE) -f objs/Makefile

install:
	$(MAKE) -f objs/Makefile install

modules:
	$(MAKE) -f objs/Makefile modules

upgrade:
	/pnpdata/2020-f-stack-muktadir/nginx_vanilla/sbin/nginx -t

	kill -USR2 `cat /pnpdata/2020-f-stack-muktadir/nginx_vanilla/logs/nginx.pid`
	sleep 1
	test -f /pnpdata/2020-f-stack-muktadir/nginx_vanilla/logs/nginx.pid.oldbin

	kill -QUIT `cat /pnpdata/2020-f-stack-muktadir/nginx_vanilla/logs/nginx.pid.oldbin`
