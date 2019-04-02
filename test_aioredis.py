import asyncio
import aioredis


async def main():
    # Redis client bound to single connection (no auto reconnection).
    # redis = await aioredis.create_redis(
    #     'redis://localhost')
    await redis.set('my-key', 'v')
    await redis.set('my-key', 'va')
    await redis.set('my-key', 'val')
    await redis.set('my-key', 'valu')
    await redis.set('my-key', 'value')

    # gracefully closing underlying connection
    # redis.close()
    # await redis.wait_closed()


async def main2():
    print('main22222222')
    # Redis client bound to single connection (no auto reconnection).

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
    # redis.close()
    # await redis.wait_closed()

if __name__ == '__main__':
    redis = aioredis.create_redis('redis://localhost')

    asyncio.get_event_loop().run_until_complete(main())
    asyncio.get_event_loop().run_until_complete(main2())
    # asyncio.get_event_loop().create_task(main())
    # asyncio.get_event_loop().create_task(main2())
