import asyncio

async def say(what, when):
    await asyncio.sleep(when)
    print(what)


#async def stop_after(loop, when):
#    await asyncio.sleep(when)
#    loop.stop()

async def handle_request(reader, writer):
    data = await reader.read(100)
    message = data.decode()

    try:
        str, at = message.split('@')
        loop = asyncio.get_event_loop()
        loop.create_task(say(str, float(at)))
    except:
        print("Bad message format (should be string@time)")

    print("Send: %r" % message)
    writer.write(data)
    await writer.drain()

    print("Close the client socket")
    writer.close()


loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_request, '127.0.0.1', 8888, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()

