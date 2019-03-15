all:	schedrt digout_periodic

schedrt:	schedrt.cpp
	g++ -I ~/src/dataserver schedrt.cpp -o schedrt -lzmq -lgpiod

digout_periodic:	digout_periodic.c
	cc -g digout_periodic.c -o digout_periodic -lgpiod
