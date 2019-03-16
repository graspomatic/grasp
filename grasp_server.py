from urllib.parse import urlparse, parse_qs  # used for parsing input from TCP client into python dictionary
import sys
import asyncio

import AppliedMotionControl
x = AppliedMotionControl.AMC(motor_ip="10.10.10.10", local_port=60649)
y = AppliedMotionControl.AMC(motor_ip="10.10.10.11", local_port=60648)

import Dynamixel2Control
dxl = Dynamixel2Control.D2C()

import MagControl
mags = MagControl.MAGS()



async def put_away(side = [-1]):
    side = int(side[0])
    print("put away " + str(side))

    loop = asyncio.get_event_loop()
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


async def retrieve(side=[-1], id=[0]):
    side = int(side[0])
    id = int(id[0])
    print('retrieving side ' + str(side) + ' object ID ' + str(id))

    # ensure arms are responsive and torque enabled

    # move both arms to 'prep_pick' position

    # find x-y position of requested object

    # move x-y motors to that spot for the specified arm

    # move specified arm to 'pick' position

    # energize magnet
    loop.create_task(mags.energize(side))

    # move specified arm to 'prep-pick' position

    # ensure that object was picked up

async def pick_and_place():
    # put away current objects, if any, get new objects, present those objects
    loop.create_task(put_away(side=[0]))
    loop.create_task(retrieve(side=[0]))




async def put_away_all():
    print('Return both objects')

async def stop_moving():
    print('stopping movement')

async def disable_arms():
    print('dsiabling arm motors')

async def disable_xy():
    print('dsiabling X-Y motors')






fx_list = {
    'put_away': put_away,
    'retrieve': retrieve
}

async def handle_request(reader, writer):
    data = await reader.read(100)                   # wait for data to become available
    message = data.decode()                         # decode it as utf-8 i think

    try:
        req = parse_qs(urlparse(message).query)     # grab the key/value pairs sent after ? in the URL

        if "function" in req:
            fx = req['function'][0].strip()         # get name of function we're supposed to call
            req.pop('function')                     # remove it from dictionary
            print(fx)
            loop.create_task(fx_list[fx](**req))    # call function with requested arguments

    except:
        print("Unexpected error:", sys.exc_info()[0])


    print("Send: %r" % message)
    writer.write(data)
    await writer.drain()

    print("Close the client socket")
    writer.close()


loop = asyncio.get_event_loop()     # makes a new event loop if one doesnt exist
coro = asyncio.start_server(handle_request, '127.0.0.1', 8888, loop=loop)  # start a socket server
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
