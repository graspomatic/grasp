from urllib.parse import urlparse, parse_qs  # used for parsing input from TCP client into python dictionary
import sys
import asyncio
import numpy as np
import json
import aioredis
import atexit
import time
import math

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


async def return_object(side=-1, add=[0,0]):
    # Put away the object currently held on specified side in
    print("put away " + str(side) + " at " + str(add))
    global redisfast
    xy_accel = 75

    # error checking
    if side != 0 and side != 1:
        print('specify side=0 (left) or side=1 (right)')
        return 0

    # move both arms to 'prep_pick' position
    # dxl.set_profile_accel(motor=11, accel=130)
    # dxl.set_profile_accel(motor=21, accel=130)
    dxl.move_arm_to_pos(arm=0, pos='prep_pick')
    dxl.move_arm_to_pos(arm=1, pos='prep_pick')


    # figure out which object is being held on this arm
    #   if nothing, return as success
    #   if we don't know, return as fail

    # find nearest empty spot on grid

    # move x-y motors to that empty spot
    xtarg = x.move_location(location=float(add[0]), accel=xy_accel, vel=20)
    ytarg = y.move_location(location=float(add[1]), accel=xy_accel, vel=20)

    # if x and y are finished moving, move arm to 'pick' position
    if side == 0:
        dxl.set_profile_accel(motor=11, accel=500)
    elif side == 1:
        dxl.set_profile_accel(motor=21, accel=500)

    await loop.create_task(wait_for_dxl(250))
    await loop.create_task(wait_for_xy(xtarg=xtarg, ytarg=ytarg, distance_thresh=(100+xy_accel*10)))
    dxl.move_arm_to_pos(arm=side, pos='pick')
    await pub.publish_json('WebClient', {"leftarm": "prep_pick", "rightarm": "prep_pick"})


    # de-energize magnet
    # await redisfast.set('get_left', '0')
    # await redisfast.set('get_right', '0')
    # await asyncio.sleep(0.01)
    await loop.create_task(wait_for_dxl(190))
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "pick"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "pick"})

    await loop.create_task(mags.deenergize(side))
    if side == 0:
        await pub.publish_json('WebClient', {"leftmag": "0"})
    else:
        await pub.publish_json('WebClient', {"rightmag": "0"})


    # move arm to 'prep-pick' position
    dxl.move_arm_to_pos(arm=side, pos='prep_pick')
    # await redisfast.set('get_left', '1')
    # await redisfast.set('get_right', '1')

    # ensure that object was released (i2c not showing anything)
    await loop.create_task(wait_for_dxl(180))

    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "prep_pick", "leftsensor": "0"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "prep_pick", "rightsensor": "0"})

    # if side == 0:
    #     await pub.publish_json('WebClient', {"leftsensor": "0"})
    # else:
    #     await pub.publish_json('WebClient', {"rightsensor": "0"})

async def retrieve(side=-1, objid=0, add=[0,0]):
    global redisslow, redisfast
    xy_accel = 75
    # Get the specified object ID on the specified arm
    print('retrieving side ' + str(side) + ' object ID ' + str(objid) + ' at ' + str(add))

    # error checking
    if side != 0 and side != 1:
        print('specify side=0 (left) or side=1 (right)')
        return

    # move both arms to 'prep_pick' position
    dxl.move_arm_to_pos(arm=0, pos='prep_pick')
    dxl.move_arm_to_pos(arm=1, pos='prep_pick')

    # move x-y motors to location of object
    print('moving x to ' + str(add[0]))
    xtarg = x.move_location(location=float(add[0]), accel=xy_accel, vel=20)
    print('moving y to ' + str(add[1]))
    ytarg = y.move_location(location=float(add[1]), accel=xy_accel, vel=20)

    #stop reading from sensors
    # await redisfast.set('get_left', '0')
    # await redisfast.set('get_right', '0')
    # await asyncio.sleep(0.01)

    # move specified arm to 'pick' position
    await loop.create_task(wait_for_xy(xtarg=xtarg, ytarg=ytarg, distance_thresh=(100+xy_accel*10)))
    await loop.create_task(wait_for_dxl(200))
    dxl.move_arm_to_pos(arm=side, pos='pick')
    await pub.publish_json('WebClient', {"leftarm": "prep_pick", "rightarm": "prep_pick", "xpos": str(add[0]), "ypos": str(add[1])})

    # when arm has reached target location, energize magnet
    await loop.create_task(wait_for_dxl(190))
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "pick"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "pick"})

    await loop.create_task(mags.energize(side))
    # await asyncio.sleep(0.05)
    if side == 0:
        await pub.publish_json('WebClient', {"leftmag": "1"})
    else:
        await pub.publish_json('WebClient', {"rightmag": "1"})



    # move specified arm to 'prep-pick' position
    dxl.move_arm_to_pos(arm=side, pos='prep_pick')
    # await redisfast.set('get_left', '1')
    # await redisfast.set('get_right', '1')


    #
    #
    # if side == 0:
    #     fut1 = redisfast.get('left_sensor_last_update')
    #     fut2 = redisfast.get('left_connected')
    #     await pub.publish_json('WebClient', {"leftarm": "prep_pick"})
    # else:
    #     fut1 = redisfast.get('right_sensor_last_update')
    #     fut2 = redisfast.get('right_connected')
    #     await pub.publish_json('WebClient', {"rightarm": "prep_pick"})
    #
    # last_update, connected = await asyncio.gather(fut1, fut2)
    #
    # print(int(last_update))
    # print(int(connected))
    # print(int(time.time()))
    #
    # if (int(time.time()) - int(last_update)) > 3:
    #     print('not updating')
    #
    # if not int(connected):
    #     print('not picked up')


    await pub.publish_json('WebClient', {"leftsensor": str(objid)})
    # ensure that object was picked up
    await loop.create_task(wait_for_dxl(170))


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
        dxl.set_profile_accel(motor=11, accel=130)
        dxl.move_arm_to_pos(arm=0, pos='prep_present', rotation=left_angle)
    if arms == 'both' or arms == 'right':
        dxl.set_profile_accel(motor=21, accel=130)
        dxl.move_arm_to_pos(arm=1, pos='prep_present', rotation=right_angle)

    # move xy to present to specified hand

    # once xy is in position, move specified arms to present
    # await wait_for_xy()

    if arms == 'both' or arms == 'left':
        dxl.move_arm_to_pos(arm=0, pos='present', rotation=left_angle)
        await pub.publish_json('WebClient', {"leftarm": "prep_present"})
    if arms == 'both' or arms == 'right':
        dxl.move_arm_to_pos(arm=1, pos='present', rotation=right_angle)
        await pub.publish_json('WebClient', {"rightarm": "prep_present"})

    await wait_for_dxl(200)

    if arms == 'both' or arms == 'left':
        await pub.publish_json('WebClient', {"leftarm": "present"})
    if arms == 'both' or arms == 'right':
        await pub.publish_json('WebClient', {"rightarm": "present"})


async def wait_for_dxl(distance_thresh=180):
    print('waiting for dynamixel motors to stop moving')
    # distance_thresh = 180
    distance = 10000
    while distance > distance_thresh:
        a = dxl.sync_get_position()
        b = dxl.sync_get_goal_position()
        distance = max([abs(x) for x in [c - d for c, d in zip(a, b)]])
        await asyncio.sleep(0.005)

    return 1

async def wait_for_xy(xtarg='*', ytarg='*', distance_thresh=200):
    print('waiting for x-y motors to stop moving')

    # 1 mm is ~300 units
    xpos = x.get_position()
    ypos = y.get_position()

    print(xpos)
    print(ypos)

    if xtarg == '*':
        distance = abs(ypos - ytarg)
    elif ytarg == '*':
        distance = abs(xpos - xtarg)
    else:
        distance = math.sqrt(abs(xpos - xtarg)**2 + abs(ypos-ytarg)**2)
    print('xy distance: ' + str(distance))

    while distance > distance_thresh:
        await asyncio.sleep(0.001)
        if xtarg == '*':
            ypos = y.get_position()
            distance = abs(ypos - ytarg)
        elif ytarg == '*':
            xpos = x.get_position()
            distance = abs(xpos - xtarg)
        else:
            xpos = x.get_position()
            ypos = y.get_position()
            distance = math.sqrt(abs(xpos - xtarg) ** 2 + abs(ypos - ytarg) ** 2)


        print('xy distance: ' + str(distance))
        print(time.time())
    #
    #
    #
    #
    #
    #
    # xstatus = x.get_status()
    # ystatus = y.get_status()
    # await asyncio.sleep(0.01)
    #
    # while xstatus[3] == 'M' or xstatus[3] == 'H' or ystatus[3] == 'M' or ystatus[3] == 'H':
    #     xstatus = x.get_status()
    #     ystatus = y.get_status()
    #     await asyncio.sleep(0.01)

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

    global redisslow, redisfast

    # tell sensors to start reading so we know what we have
    await redisfast.set('get_left', '0')
    await redisfast.set('get_right', '0')
    await asyncio.sleep(0.010)

    hand = int(hand[0])
    left_id = int(left_id[0])
    right_id = int(right_id[0])
    left_angle = int(left_angle[0])
    right_angle = int(right_angle[0])

    if hand == -1:
        print('specify which hand to present to, 0 or 1 for left or right')
        return

    ## determine arms that will be used for returning objects
    # get information from sensors
    fut1 = redisfast.get('left_sensor_last_update')
    fut2 = redisfast.get('left_connected')
    fut3 = redisfast.get('right_sensor_last_update')
    fut4 = redisfast.get('right_connected')
    left_last_update, left_connected, right_last_update, right_connected = await asyncio.gather(fut1, fut2, fut3, fut4)

    left_updated = (int(time.time()) - int(left_last_update)) < 3
    right_updated = (int(time.time()) - int(right_last_update)) < 3
    left_connected = int(left_connected)
    right_connected = int(right_connected)

    # if not left_updated:
    #     print('not updating left')
    #     return
    # if not right_updated:
    #     print('not updating right')
    #     return
    # if not left_connected:
    #     print('nothing on left')
    # if not right_connected:
    #     print('nothing on right')

    # get information from panels database
    fut1 = redisslow.get('panel')
    fut2 = redisslow.get('holding')
    fut3 = redisslow.get('arm_offset')
    panel, holding, arm_offset = await asyncio.gather(fut1, fut2, fut3)
    panel = np.array(json.loads(panel))
    holding = np.array(json.loads(holding))
    arm_offset = np.array(json.loads(arm_offset))

    # make list of objects to return, assuming that database and sensor readings agree on what we're holding
    if (left_connected and holding[0]) or (not left_connected and not holding[0]):
        returning = [holding[0]]
    else:
        print('incompatibility between what the database says and what sensors say for left')


    if (right_connected and holding[1]) or (not right_connected and not holding[1]):
        returning.append(holding[1])
    else:
        print('incompatibility between what the database says and what sensors say for right')


    #arms that will be used for retrieving objects
    if left_id > -1 and right_id == -1:
        arms = 'left'
        picking = [left_id, 0]
    elif left_id == -1 and right_id > -1:
        arms = 'right'
        picking = [0, right_id]
    elif left_id > -1 and right_id > -1:
        arms = 'both'
        picking = [left_id, right_id]

    else:
        arms = 'neither'

    print(holding)
    print(picking)
    print(panel)

    panel, orders = pf.plan_path(holding.tolist(), picking, panel, arm_offset)

    fut1 = redisslow.set('panel', json.dumps(panel.tolist()))
    fut2 = redisslow.set('holding', json.dumps(picking))
    await asyncio.gather(fut1, fut2)

    # tell sensors to stop reading
    # await redisfast.set('get_left', '0')
    # await redisfast.set('get_right', '0')



    print(panel)
    print(orders)


    print(len(orders))

    for i in range(len(orders)):
        print(i)
        print(orders[i])
        print(orders[i][0])
        print(orders[i][1])
        print(orders[i][2])
        print(orders[i][2][0])
        print(orders[i][2][1])

        order = orders[i][0][0]
        side = orders[i][1][0]
        location = orders[i][2]

        if order == 'd':
            print('dropping off with arm ' + str(side) + ' at location ' + str(location))
            await return_object(side=side, add=location)

        if order == 'p':
            print('picking up with arm ' + str(side) + ' at location ' + str(location))
            await retrieve(side=side, objid=left_id, add=location)









    # if holding anything in left arm
    # await return_object(0)
    # if holding anything in right arm
    # await return_object(1)

    # if arms == 'left':
    #     await retrieve(side=0, objid=left_id)
    # elif arms == 'right':
    #     await retrieve(side=1, objid=right_id)
    # else:
    #     # determine if its faster to get left or right first
    #     await retrieve(side=0, objid=left_id)
    #     await retrieve(side=1, objid=right_id)

    await present(arms=arms, hand=hand, left_angle=left_angle, right_angle=right_angle)
    await redisfast.set('get_left', '1')
    await redisfast.set('get_right', '1')


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
    # dxl.set_torque_all(0)
    # dxl.set_moving_thresh_all()  # needs torque off
    dxl.set_torque_all(1)
    dxl.set_moving_pwms(level)
    dxl.set_profile_accel(11, 130)
    dxl.set_profile_accel(21, 130)
    dxl.set_profile_vel(11, 400)
    dxl.set_profile_vel(21, 400)

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

    print(position)
    print(position.split(','))




    if (side != 0 and side != 1):
        print('side must be 0 (left) or 1 (right)')
        return

    if len(position.split(',')) == 1:
        print('heading to move arm to pos')

        dxl.move_arm_to_pos(arm=side, pos=position)
        await loop.create_task(wait_for_dxl(50))
        if side == 0:
            await pub.publish_json('WebClient', {"leftarm": position})
        else:
            await pub.publish_json('WebClient', {"rightarm": position})
    elif len(position.split(',')) == 3:
        print('heading to sync set position')
        if side == 0:
            motors = [11, 12, 13]
        elif side == 1:
            motors = [21, 22, 23]

        dxl.sync_set_position(motors, json.loads(position))




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
        await x.find_bound(direction, current=1.1)
    else:
        await y.find_bound(direction, current=0.8)

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
        xtarg = x.move_location(location=location, accel=accel, vel=vel)
        await loop.create_task(wait_for_xy(xtarg=xtarg))
        # await wait_for_xy()
        await pub.publish_json('WebClient', {"xpos": str(location)})
    else:
        ytarg = y.move_location(location=location, accel=accel, vel=vel)
        await loop.create_task(wait_for_xy(ytarg=ytarg))
        # await wait_for_xy
        await pub.publish_json('WebClient', {"ypos": str(location)})

async def magnets(left_status = [-1], right_status = [-1]):
    # left_status = 0 means turn off that magnet, 1 turn on
    global redisfast

    left_status = int(left_status[0])
    right_status = int(right_status[0])

    if left_status == 0:
        await redisfast.set('get_left', '0')
        await redisfast.set('get_right', '0')
        await asyncio.sleep(0.01)
        await loop.create_task(mags.deenergize(0))
        await redisfast.set('get_left', '1')
        await redisfast.set('get_right', '1')
        await pub.publish_json('WebClient', {"leftmag": "0"})

    elif left_status == 1:
        await redisfast.set('get_left', '0')
        await redisfast.set('get_right', '0')
        await asyncio.sleep(0.01)
        await loop.create_task(mags.energize(0))
        await redisfast.set('get_left', '1')
        await redisfast.set('get_right', '1')
        await pub.publish_json('WebClient', {"leftmag": "1"})

    if right_status == 0:
        await redisfast.set('get_left', '0')
        await redisfast.set('get_right', '0')
        await asyncio.sleep(0.01)
        await loop.create_task(mags.deenergize(1))
        await redisfast.set('get_left', '1')
        await redisfast.set('get_right', '1')
        await pub.publish_json('WebClient', {"rightmag": "0"})
    elif right_status == 1:
        await redisfast.set('get_left', '0')
        await redisfast.set('get_right', '0')
        await asyncio.sleep(0.01)
        await loop.create_task(mags.energize(1))
        await redisfast.set('get_left', '1')
        await redisfast.set('get_right', '1')
        await pub.publish_json('WebClient', {"rightmag": "1"})

async def find_address(shapeid=0):
    global redisslow

    if shapeid <= 1:
        print('need a number >1')
        return -1

    panel = await redisslow.get('panel')
    panel = np.array(json.loads(panel))
    add = np.where(panel[:, :, 2] == shapeid)

    if len(add[0]) == 0:
        print('object not found on panel')
        return -1
    elif len(add[0]) > 1:
        print('object on panel multiple times')
        return -1

    x = panel[add[0][0], add[1][0], 0]
    y = panel[add[0][0], add[1][0], 1]

    return x, y



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


# function=pick_and_place&hand=0&right_id=4

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
    await redisfast.set('get_left', '1')
    await redisfast.set('get_right', '1')



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
