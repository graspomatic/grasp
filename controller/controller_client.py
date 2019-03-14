import sys
import asyncio


async def tcp_echo_client(message, loop):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888, loop=loop)

    print('Send: %r' % message)
    writer.write(message.encode())

    data = await reader.read(100)
    print('Received: %r' % data.decode())

    print('Close the socket')
    writer.close()


if len(sys.argv) != 3:
    print("usage: python controller_client.py message delay")
    exit(0)

# Create command by combining argv[1] and argv[2] into "argv[1]@argv[2]"
cmd = "@".join(sys.argv[1:3])
loop = asyncio.get_event_loop()
loop.run_until_complete(tcp_echo_client(cmd, loop))
loop.close()