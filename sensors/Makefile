mpr121:	mpr121.o
	$(CC) -o $@ $< -lhiredis -lupmc-mpr121

mpr121.o:	mpr121.c
	$(CC) -I/usr/include/upm -I/usr/local/include/hiredis -c $<
