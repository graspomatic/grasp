from urllib.parse import urlparse, parse_qs  # used for parsing input from TCP client intp python dictionary

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


async def put_away(side):
    print('putting away')
    print(side)

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

    print("put away " + str(side))

async def retrieve(side, object):
    loop = asyncio.get_event_loop()
    # ensure arms are responsive and torque enabled

    # move both arms to 'prep_pick' position

    # find x-y position of requested object

    # move x-y motors to that spot for the specified arm

    # move specified arm to 'pick' position

    # energize magnet
    loop.create_task(mags.energize(side))

    # move specified arm to 'prep-pick' position

    # ensure that object was picked up

    print("retrieve " + str(side) + " on side " + str(object))

fx_list = {
    'put_away': put_away,
    'retrieve': retrieve
}

async def handle_request(reader, writer):
    data = await reader.read(100)                   # wait for data to become available
    message = data.decode()                         # decode it as utf-8 i think

    try:
        req = parse_qs(urlparse(message).query)

        if "function" in req:
            # get name of function we're supposed to call and remove it from dictionary
            fx = req['function'][0].strip()
            req.pop('function')

            print(fx)
            print(fx_list[fx])

            # make sure this function is on the approved list
            # so we're not just running literally any function
            # that is sent to the server


            # assemble the rest of the key value pairs into a string
            #arg_string = ", ".join("=".join((str(k), str(v[0]))) for k, v in req.items())

            #combined it all and call it
            #command = 'loop.create_task(' + fx + '(' + arg_string + '))'



            loop.create_task(fx_list[fx](**req))

            #print(command)

        print(req.keys())
        loop = asyncio.get_event_loop()
        # # loop.create_task(say(str, float(at)))
        #
        # loop.create_task(mags.deenergize(1))
        loop.create_task(put_away(1))

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
