from urllib.parse import urlparse, parse_qs  # used for parsing input from TCP client into python dictionary
import sys
import asyncio
import numpy as np
import json
import aioredis
import atexit
import time



active_task = 0

import AppliedMotionControl
x = AppliedMotionControl.AMC(motor_ip="10.10.10.10", local_port=60649)
y = AppliedMotionControl.AMC(motor_ip="10.10.10.11", local_port=60648)

import Dynamixel2Control
dxl = Dynamixel2Control.D2C()

import MagControl
mags = MagControl.MAGS()

import path_find
pf = path_find.path_find()

# import redis
# r = redis.Redis(host='localhost', port=6379, db=0)
import aioredis
# r = aioredis.create_redis('redis://localhost')



async def return_object(side = -1):
    # Put away the object currently held on specified side in the nearest empty spot
    print("put away " + str(side))

    # error checking
    if side != 0 and side != 1:
        print('specify side=0 (left) or side=1 (right)')
        return 0

    # move both arms to 'prep_pick' position
    dxl.move_arm_to_pos(arm=0, pos='prep_pick')
    dxl.move_arm_to_pos(arm=1, pos='prep_pick')


    # figure out which object is being held on this arm
    #   if nothing, return as success
    #   if we don't know, return as fail

    # find nearest empty spot on grid

    # move x-y motors to that empty spot

    # if x and y are finished moving, move arm to 'pick' position
    await loop.create_task(wait_for_dxl())
    dxl.move_arm_to_pos(arm=side, pos='pick')
    await pub.publish_json('WebClient', {"leftarm": "prep_pick", "rightarm": "prep_pick"})


    # de-energize magnet
    await loop.create_task(wait_for_dxl())
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "pick"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "pick"})

    await loop.create_task(mags.deenergize(side))
    if side == 0:
        await pub.publish_json('WebClient', {"leftmag": "1"})
    else:
        await pub.publish_json('WebClient', {"rightmag": "1"})


    # move arm to 'prep-pick' position
    dxl.move_arm_to_pos(arm=side, pos='prep_pick')

    # ensure that object was released (i2c not showing anything)
    await loop.create_task(wait_for_dxl())

    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "prep_pick"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "prep_pick"})

    if side == 0:
        await pub.publish_json('WebClient', {"leftsensor": "0"})
    else:
        await pub.publish_json('WebClient', {"rightsensor": "0"})

async def retrieve(side=-1, objid=0):
    # Get the specified object ID on the specified arm
    print('retrieving side ' + str(side) + ' object ID ' + str(objid))

    # error checking
    if side != 0 and side != 1:
        print('specify side=0 (left) or side=1 (right)')
        return 0

    # move both arms to 'prep_pick' position

    dxl.move_arm_to_pos(arm=0, pos='prep_pick')
    dxl.move_arm_to_pos(arm=1, pos='prep_pick')

    # find x-y position of requested object

    # move x-y motors to that spot for the specified arm

    # move specified arm to 'pick' position
    await loop.create_task(wait_for_dxl())
    dxl.move_arm_to_pos(arm=side, pos='pick')
    await pub.publish_json('WebClient', {"leftarm": "prep_pick", "rightarm": "prep_pick"})

    # when arm has reached target location, energize magnet
    await loop.create_task(wait_for_dxl())
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "pick"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "pick"})

    await loop.create_task(mags.energize(side))
    if side == 0:
        await pub.publish_json('WebClient', {"leftmag": "1"})
    else:
        await pub.publish_json('WebClient', {"rightmag": "1"})

    # move specified arm to 'prep-pick' position
    dxl.move_arm_to_pos(arm=side, pos='prep_pick')

    # ensure that object was picked up
    await loop.create_task(wait_for_dxl())
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "prep_pick"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "prep_pick"})

    await pub.publish_json('WebClient', {"leftsensor": "12"})


async def present(arms='neither', hand=-1, left_angle=0, right_angle=0):
    # present objects on specified arms to specified hand
    print('Presenting objects on ' + str(arms) + ' arms to hand ' + str(hand))

    # input variables"
    # arms (list of ints) [0] for left only, [1] for right only, [0 1] for both arms
    # hand (list of single int) [0] for left, [1] for right

    # if arms is empty or -1, ask for arms
    if arms == 'neither':
        print('No arms specified.')
        return

    # if hand isn't 0 or 1, ask which hand we're supposed to present to
    if hand != 0 & hand != 1:
        print('Specify which hand to present to, 0 (left) or 1 (right)')
        return

    # move specified arms to prep_present
    if arms == 'both' or arms == 'left':
        dxl.move_arm_to_pos(arm=0, pos='prep_present', rotation=left_angle)
    if arms == 'both' or arms == 'right':
        dxl.move_arm_to_pos(arm=1, pos='prep_present', rotation=right_angle)

    # move xy to present to specified hand

    # once xy is in position, move specified arms to present
    await wait_for_xy()
    if arms == 'both' or arms == 'left':
        dxl.move_arm_to_pos(arm=0, pos='present', rotation=left_angle)
    if arms == 'both' or arms == 'right':
        dxl.move_arm_to_pos(arm=1, pos='present', rotation=right_angle)


async def wait_for_dxl():
    print('waiting for dynamixel motors to stop moving')
    distance_thresh = 20
    distance = 10000
    while distance > distance_thresh:
        a = dxl.sync_get_position()
        b = dxl.sync_get_goal_position()
        distance = max([abs(x) for x in [c - d for c, d in zip(a, b)]])
        await asyncio.sleep(0.01)

    return 1

async def wait_for_xy():
    print('waiting for x-y motors to stop moving')

    xstatus = x.get_status()
    ystatus = y.get_status()
    await asyncio.sleep(0.01)

    while xstatus[3] == 'M' or xstatus[3] == 'H' or ystatus[3] == 'M' or ystatus[3] == 'H':
        xstatus = x.get_status()
        ystatus = y.get_status()
        await asyncio.sleep(0.01)

    print('target reached')
    return 1

# async def redis_interact(req, vari, val = 0):
#     if req == 'get':
#         a = np.array(json.loads(r.get(vari)))
#         return a
#
#     elif req == 'set':
#         r.set(vari, json.dumps(val.tolist()))
#
#     await asyncio.sleep(10)








################################################

#  Functions callable from client

#################################################

async def pick_and_place(hand=[-1], left_id=[-1], right_id=[-1], left_angle=[0], right_angle=[0]):
    # put away current objects, if any, get new objects, present those objects
    # input variables:
    # hand (integer) is position where we want to present object. 0 (left) or (1) right
    # left_id (integer) object id to present using left arm
    # right_id (integer) object id to present using right arm

    hand = int(hand[0])
    left_id = int(left_id[0])
    right_id = int(right_id[0])
    left_angle = int(left_angle[0])
    right_angle = int(right_angle[0])

    if hand == -1:
        print('specify which hand to present to, 0 or 1 for left or right')
        return

    #arms that will be used for retrieving objects
    if left_id > -1 and right_id == -1:
        arms = 'left'
    elif left_id == -1 and right_id > -1:
        arms = 'right'
    elif left_id > -1 and right_id > -1:
        arms = 'both'
    else:
        arms = 'neither'

    # if holding anything in left arm
    await return_object(0)
    # if holding anything in right arm
    # await return_object(1)

    if arms == 'left':
        await retrieve(side=0, objid=left_id)
    elif arms == 'right':
        await retrieve(side=1, objid=right_id)
    else:
        # determine if its faster to get left or right first
        await retrieve(side=0, objid=left_id)
        await retrieve(side=1, objid=right_id)

    await present(arms=arms, hand=hand, left_angle=left_angle, right_angle=right_angle)


async def put_away(side=[-1]):
    # side = 0 for left, 1 for right, 2 for both
    side = int(side[0])
    print(side)
    if side == 0 or side == 2:
        print('put away left')
        await return_object(0)
    if side == 1 or side == 2:
        print('put away right')
        await return_object(1)


async def initialize_dxl(level=[1]):
    level = float(level[0])
    dxl.set_torque_all(0)
    dxl.set_moving_thresh_all()  # needs torque off
    dxl.set_torque_all(1)
    dxl.set_moving_pwms(level)

    print('dxl motors initialized')

async def enable_arms():
    print('enabling arm motors')
    dxl.set_torque_all(1)

async def disable_arms():
    print('disabling arm motors')
    dxl.set_torque_all(0)

async def get_dxl_positions():
    print('getting positions of all 6 dxl motors')
    pos = dxl.sync_get_position()
    print(pos)

async def set_dxl_positions(side=[-1], position=['blah']):
    print('setting positions of one arm')
    side = int(side[0])
    position = str(position[0])

    if (side != 0 and side != 1):
        print('side must be 0 (left) or 1 (right)')
        return

    if len(position.split()) == 1:
        dxl.move_arm_to_pos(arm=side, pos=position)
        await loop.create_task(wait_for_dxl())
        if side == 0:
            await pub.publish_json('WebClient', {"leftarm": position})
        else:
            await pub.publish_json('WebClient', {"rightarm": position})




async def check_dxl_errors():
    print('checking for dxl errors')
    errs = dxl.sync_error_status()
    print(errs)

async def enable_xy():
    print('enabling x-y motors')

async def disable_xy():
    print('disabling X-Y motors')



async def find_bounds(axis = ['a'], direction = [-1]):
    axis = str(axis[0])
    direction = int(direction[0])
    print('finding bounds for axis ' + axis + ' in direction ' + str(direction))

    if axis != 'x' and axis != 'y':
        print('axis must be "x" or "y"')
        return

    if direction != 0 and direction != 1:
        print('direction must be 0 (ccw) or 1 (cw)')
        return

    if axis == 'x':
        await x.find_bound(direction)
    else:
        await y.find_bound(direction)

async def move_xy_distance_mm(axis = ['a'], distance = [0]):
    axis = str(axis[0])
    distance = float(distance[0])
    print('moving ' + axis + ' distance ' + str(distance))

    if axis != 'x' and axis != 'y':
        print('axis must be "x" or "y"')
        return

    if distance == 0:
        print('distance must be non-zero')
        return

    if axis == 'x':
        await x.move_distance_mm(distance)
    else:
        await y.move_distance_mm(distance)

async def move_xy_to_location(axis = ['a'], location = [-1], accel = [25], vel = [3]):
    axis = str(axis[0])
    location = float(location[0])
    accel = float(accel[0])
    vel = float(vel[0])

    if axis != 'x' and axis != 'y':
        print('axis must be "x" or "y"')
        return
    if location < 0:
        print('distance must be positive int or float')
        return
    if accel < 0:
        print('accel must be positive int or float')
        return
    if vel < 0:
        print('vel must be positive int or float')
        return

    if axis == 'x':
        x.move_location(location=location, accel=accel, vel=vel)
        await loop.create_task(wait_for_xy())
        # await wait_for_xy()
        await pub.publish_json('WebClient', {"xpos": str(location)})
    else:
        y.move_location(location=location, accel=accel, vel=vel)
        await loop.create_task(wait_for_xy())
        # await wait_for_xy
        await pub.publish_json('WebClient', {"ypos": str(location)})

async def magnets(left_status = [-1], right_status = [-1]):
    # left_status = 0 means turn off that magnet, 1 turn on

    left_status = int(left_status[0])
    right_status = int(right_status[0])

    if left_status == 0:
        await loop.create_task(mags.deenergize(0))
        await pub.publish_json('WebClient', {"leftmag": "0"})
    elif left_status == 1:
        await loop.create_task(mags.energize(0))
        await pub.publish_json('WebClient', {"leftmag": "1"})

    if right_status == 0:
        await loop.create_task(mags.deenergize(1))
        await pub.publish_json('WebClient', {"rightmag": "0"})
    elif right_status == 1:
        await loop.create_task(mags.energize(1))
        await pub.publish_json('WebClient', {"rightmag": "1"})


async def change_address(row, col, shapeid):
    # changes the address of a specified shape on the panel
    global redisslow
    row = int(row[0])               # row where shape is going
    col = int(col[0])               # col where shape is going
    shapeid = int(shapeid[0])       # shape id being placed

    # get the panel values from redis
    panel = await redisslow.get('panel')
    panel = np.array(json.loads(panel))

    # find if object is already on panel and remove it if so
    add = np.where(panel[:, :, 2] == shapeid)
    for i in range(len(add[0])):
        panel[add[0][i], add[1][i], 2] = 0

    # put shape at new address
    panel[row, col, 2] = shapeid

    # update redis
    await redisslow.set('panel', json.dumps(panel.tolist()))


async def ping():
    return 'pong'

async def abort():
    global active_task
    print('canceling')
    print(active_task)
    try:
        active_task.cancel()
    except:
        print('we dont have anything to cancel!')




fx_list = {
    'pick_and_place': pick_and_place,
    'put_away': put_away,

    'initialize_dxl': initialize_dxl,
    'enable_arms': enable_arms,
    'disable_arms': disable_arms,
    'get_dxl_positions': get_dxl_positions,
    'set_dxl_positions': set_dxl_positions,
    'check_dxl_errors': check_dxl_errors,

    'enable_xy': enable_xy,
    'disable_xy': disable_xy,
    'find_bounds': find_bounds,
    'move_xy_distance_mm': move_xy_distance_mm,
    'move_xy_to_location': move_xy_to_location,

    'magnets': magnets,

    'change_address': change_address,

    'ping': ping,
    'abort': abort
}

async def handle_request(reader, writer):
    result = '101'
    data = await reader.read(100)                   # wait for data to become available
    message = data.decode()                         # decode it as utf-8 i think
    global active_task

    try:
        print('message: ' + message)

        message = message.split(' ')[1]    # message is usually "GET blagblahblah HTTP/1.1"
        req = parse_qs(urlparse(message).query)     # grab the key/value pairs sent after ? in the URL

        if "function" in req:
            fx = req['function'][0].strip()         # get name of function we're supposed to call
            req.pop('function')                     # remove it from dictionary
            print(req)

            if fx == 'abort':
                loop.create_task(abort())
                result = 'aborted'  # 200 ok
            else:
                if len(asyncio.all_tasks(loop)) > 4:  # if we're already doing something
                    print('busy')
                    result = 'busy'   # 504 timeout
                elif fx == 'ping':
                    result = 'pong'  # 100 continue
                else:
                    active_task = loop.create_task(fx_list[fx](**req))    # call function with requested arguments
                    result = 'accepted'  # 200 ok
        else:
            result = 'invalid'    # 418 im a teapot

    except:
        print("Unexpected error:", sys.exc_info()[0])
        result = 'error'   # 500 internal server error


    query = (
        f"HTTP/1.1 200 {result}\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Content-type: text/plain\r\n"
        "Hello, world!\r\n"
        "\r\n"
    )

    writer.write(query.encode('latin-1'))
    writer.close()
    await writer.wait_closed()






# check redis for panel variable and initialize it if it doesn't exist
def init_panel():
    global redisslow
    w = 2   # columns in panel
    h = 1   # rows
    d = 3   # depth (should be 3 for x, y, and ID

    panel = np.zeros((h, w, d))
    panel[0, 0, 0] = 11.1
    panel[0, 0, 1] = 11.2
    panel[0, 0, 2] = 73
    panel[0, 1, 0] = 21.1
    panel[0, 1, 1] = 21.2
    panel[0, 1, 2] = 74

    panelJSON = json.dumps(panel.tolist())
    redisslow.set('panel', panelJSON)

    # to retrieve:
    # np.array(json.loads(r.get('panel')))


async def reader(ch):
    while (await ch.wait_message()):
        msg = await ch.get_json()
        print("Got Message:", msg)

async def connect_redis():
    global redisfast, redisslow, pub
    redisfast = await aioredis.create_redis(('localhost', 6379), loop=loop)
    redisslow = await aioredis.create_redis(('localhost', 6380), loop=loop)
    pub = await aioredis.create_redis(('localhost', 6379), loop=loop)



async def disconnect_redis():
    global redisfast, redisslow, pub
    redisfast.close()
    await redisfast.wait_closed()

    redisslow.close()
    await redisslow.wait_closed()

    pub.close()
    await pub.wait_closed()



# verify redis connection
# if r.ping():
#     if not r.exists('panel'):
#         init_panel()
#     print('redis connected')
# else:
#     print('redis not connected')


loop = asyncio.get_event_loop()     # makes a new event loop if one doesnt exist
loop.create_task(connect_redis())
coro = asyncio.start_server(handle_request, '128.148.110.89', 8888, loop=loop)  # start a socket server
# coro = asyncio.start_server(handle_request, '127.0.0.1', 8888, loop=loop)  # start a socket server
server = loop.run_until_complete(coro)
initialize_dxl(level=1)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
loop.run_until_complete(disconnect_redis())
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
