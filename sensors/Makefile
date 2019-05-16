:%s/^[ ]\+/^I/

mpr121:	mpr121.o
	$(CC) -g -o $@ $< -lhiredis -lupmc-mpr121

mpr121.o:	mpr121.c
	$(CC) -g -I/usr/include/upm -I/usr/include/hiredis -c $<

clean:
    rm mpr121.o mpr121

