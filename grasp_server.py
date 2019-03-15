import AppliedMotionControl
x = AppliedMotionControl.AMC(motor_ip="10.10.10.10", local_port=60649)
y = AppliedMotionControl.AMC(motor_ip="10.10.10.11", local_port=60648)

import Dynamixel2Control
dxl = Dynamixel2Control.D2C()

import MagControl
import asyncio
mags = MagControl.MAGS()


# async def say(what, when):
#     await asyncio.sleep(when)
#     print(what)
#
#
# async def demag(what, when):
#     mags.deenergize('right')


async def put_away(loop, side):
    # ensure arms are responsive and torque enabled

    # move both arms to 'prep_pick' position

    # figure out which object is being held on this arm

    # find nearest empty spot on grid

    # move x-y motors to that empty spot

    # if x and y are finished moving, move arm to 'pick' position

    # de-energize magnet
    loop.create_task(mags.deenergize(side))

    # move arm to 'prep-pick' position

    # ensure that object was released (i2c not showing anything)

    print("put away " + side)

async def retrieve(side, object):
    # ensure arms are responsive and torque enabled

    # move both arms to 'prep_pick' position

    # find x-y position of requested object

    # move x-y motors to that spot for the specified arm

    # move specified arm to 'pick' position

    # energize magnet

    # move specified arm to 'prep-pick' position

    # ensure that object was picked up

    print("retrieve " + side + " " + object)

async def handle_request(reader, writer):
    data = await reader.read(100)                   # wait for data to become available
    message = data.decode()                         # decode it as utf-8 i think

    try:
        str, at = message.split('@')
        loop = asyncio.get_event_loop()
        # # loop.create_task(say(str, float(at)))
        #
        # loop.create_task(mags.deenergize(1))
        put_away(loop, 1)

    except:
        print("Bad message format (should be string@time)")

    print("Send: %r" % message)
    writer.write(data)
    await writer.drain()

    print("Close the client socket")
    writer.close()


loop = asyncio.get_event_loop()     # makes a new event loop if one doesnt exist
coro = asyncio.start_server(handle_request, '127.0.0.1', 8888, loop=loop) # start a socket server
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
