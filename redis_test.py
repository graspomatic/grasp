import redis
import time

r = redis.Redis()



start = time.time()

for i in range(1000):
    r.set('foo', 'bar')

end = time.time()
print(end-start)
