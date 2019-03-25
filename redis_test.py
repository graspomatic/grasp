import redis
import time

r = redis.Redis()


print('starting')
start = time.time()

for i in range(100):
    r.set('foo', 'bar')
    time.sleep(0.01)
end = time.time()
print(end-start)
