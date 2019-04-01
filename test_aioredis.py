import asyncio
import aioredis


async def main():
    # Redis client bound to single connection (no auto reconnection).
    redis = await aioredis.create_redis(
        'redis://localhost')
    await redis.set('my-key', 'v')
    await redis.set('my-key', 'va')
    await redis.set('my-key', 'val')
    await redis.set('my-key', 'valu')
    await redis.set('my-key', 'value')

    # gracefully closing underlying connection
    redis.close()
    await redis.wait_closed()


async def main2():
    # Redis client bound to single connection (no auto reconnection).
    redis = await aioredis.create_redis(
        'redis://localhost')
    # await redis.set('my-key', 'vale')
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)
    val = await redis.get('my-key')
    print(val)


    # gracefully closing underlying connection
    redis.close()
    await redis.wait_closed()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_until_complete(main2())
