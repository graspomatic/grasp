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
    # Put away the object currently held on specified side

    side = int(side[0])
    print("put away " + str(side))

    loop = asyncio.get_event_loop()
    # ensure arms are responsive and torque enabled

    # make sure we know what this arm is holding before putting it back

    # move both arms to 'prep_pick' position

    # figure out which object is being held on this arm
    #   if nothing, return as success
    #   if we don't know, return as fail

    # find nearest empty spot on grid

    # move x-y motors to that empty spot





    # if x and y are finished moving, move arm to 'pick' position

    # de-energize magnet
    loop.create_task(mags.deenergize(side))

    # move arm to 'prep-pick' position

    # ensure that object was released (i2c not showing anything)


async def retrieve(side=[-1], id=[0]):
    # Get the specified object ID on the specified arm

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

async def present(arms=[-1], hand=[-1]):
    # present objects on specified arms to specified hand
    print('Presenting objects on arms ' + str(arms) + ' to hand ' + str(hand))

    # input variables"
    # arms (list of ints) [0] for left only, [1] for right only, [0 1] for both arms
    # hand (list of single int) [0] for left, [1] for right

    # if arms is empty or -1, ask for arms
    if len(arms) == 0 | arms[0] == -1:
        print('No arms specified. give me a 0 or 1 or both')
        return

    # if hand isn't 0 or 1, ask which hand we're supposed to present to
    if hand[0] < 0 | hand[0] > 1:
        print('Specify which hand to present to, 0 (left) or 1 (right)')








################################################

#  Functions callable from client

#################################################

async def pick_and_place(hand=[-1], left_id=[-1], right_id=[-1]):
    # put away current objects, if any, get new objects, present those objects
    # input variables:
    # hand (integer) is position where we want to present object. 0 (left) or (1) right
    # left_id (integer) object id to present using left arm
    # right_id (integer) object id to present using right arm

    arms=[]

    loop.create_task(put_away(side=[0]))
    loop.create_task(put_away(side=[1]))
    if left_id[0] > -1:
        loop.create_task(retrieve(side=[0], id=left_id))
        arms.append(0)
    if right_id[0] > -1:
        loop.create_task(retrieve(side=[1], id=right_id))
        arms.append(1)
    loop.create_task(present(arms=arms, hand=hand))







async def put_away_all():
    print('Return both objects')

async def stop_moving():
    print('stopping movement')

async def disable_arms():
    print('dsiabling arm motors')

async def disable_xy():
    print('dsiabling X-Y motors')






fx_list = {
    'pick_and_place': pick_and_place,
    'put_away_all': put_away_all,
    'stop_moving': stop_moving,
    'disable_arms': disable_arms,
    'disable_xy': disable_xy
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
