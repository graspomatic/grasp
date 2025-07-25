from urllib.parse import urlparse, parse_qs  # used for parsing input from TCP client into python dictionary
import sys
import asyncio
import numpy as np
import json
import redis.asyncio as redis
import atexit
import time
import math
import sqlite3
import re
import struct

active_task = 0

# Shared dictionary for controlling the motor following behavior
follow_settings = {
    "enabled": False,        # Whether to follow the dial/pattern
    "follow_mode": "dial",   # follow "dial" or "pattern"
    "offset": 0,             # Offset in degrees to apply to dial position so it is centered around displayed orientation
    "dial_motor": 1,         # Motor ID of the dial motor
    "target_arm": 0,         # Arm ID of the follower motor (0 for left, 1 for right)
    "start_time": 0          # used to keep track of when angle-following started for the pattern
}

# XY motors
from AppliedMotionControl.AppliedMotionControl import AMC
x = AMC(motor_ip="100.0.0.110", local_port=60649, belt='standard')
y = AMC(motor_ip="100.0.0.111", local_port=60648, belt='steel')

# servos
from Dynamixel2Control.Dynamixel2Control import D2C
dxl = D2C()

# magnets
from MagControl.MagControl import MAGS
mags = MAGS()

# algorithm for determining order of pickup and dropoff of objects
import path_find
pf = path_find.path_find()

# library to manage sending packets to the dataserver without expecting a response
# from send_binary import send_to_dataserver, DservType
from binary_dpoint import send_to_dataserver, DservType

# stores information about the shapes
# conn = sqlite3.connect('/home/root/grasp/shapes/objects2.db')
conn = sqlite3.connect('/shared/lab/stimuli/grasp/objects2.db')
sqlc = conn.cursor()

# connection to dserv on machine running the experiment
import socket
qnxhost = "192.168.88.40"
qnxsock = socket.create_connection((qnxhost, 4620)) # new RPi4 version of QNX
qnxsock.settimeout(0.2)



async def return_object(side=-1, add=[0, 0]):
    # Put away the object currently held on specified side in
    print("put away " + str(side) + " at " + str(add))
    # global redisfast
    xy_accel = 40

    # error checking
    if side != 0 and side != 1:
        print('specify side=0 (left) or side=1 (right)')
        return 0

    # energize the magnet just in case i forgot to do that
    await loop.create_task(mags.energize(side))

    # move both arms to 'prep_pick' position
    dxl.move_arm_to_pos(arm=0, pos='prep_pick')
    dxl.move_arm_to_pos(arm=1, pos='prep_pick')

    # move x-y motors to empty spot
    xtarg = x.move_location(location=float(add[0]), accel=xy_accel, vel=20)
    ytarg = y.move_location(location=float(add[1]), accel=xy_accel, vel=20)

    # prep dxl motor to pick
    if side == 0:
        dxl.set_profile_accel(motor=11, accel=500)
    elif side == 1:
        dxl.set_profile_accel(motor=21, accel=500)

    # once everything is in position, move arm to 'pick' position
    await loop.create_task(wait_for_xy(xtarg=xtarg, ytarg=ytarg, distance_thresh=(100 + xy_accel * 30)))
    await loop.create_task(wait_for_dxl(300))
    await pub.publish_json('WebClient', {"leftarm": "prep_pick", "rightarm": "prep_pick"})

    dxl.move_arm_to_pos(arm=side, pos='pick')
    await loop.create_task(wait_for_dxl(180))  # 190 seems too high

    # de-energize magnet
    await loop.create_task(mags.deenergize(side))
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "pick", "leftmag": "0"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "pick", "rightmag": "0"})

    # move arm to 'prep-pick' position
    dxl.move_arm_to_pos(arm=side, pos='prep_pick')

    # ensure that object was released (i2c not showing anything)
    # await loop.create_task(wait_for_dxl(195))

    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "prep_pick", "leftsensor": "0"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "prep_pick", "rightsensor": "0"})


async def retrieve(side=-1, objid=0, add=[0, 0]):
    global redisslow
    xy_accel = 40
    # Get the specified object ID on the specified arm
    print('retrieving side ' + str(side) + ' object ID ' + str(objid) + ' at ' + str(add))

    # error checking
    if side != 0 and side != 1:
        print('specify side=0 (left) or side=1 (right)')
        return

    # prep dxl motor to pick
    if side == 0:
        dxl.set_profile_accel(motor=11, accel=500)
    elif side == 1:
        dxl.set_profile_accel(motor=21, accel=500)

    # move both arms to 'prep_pick' position
    dxl.move_arm_to_pos(arm=0, pos='prep_pick')
    dxl.move_arm_to_pos(arm=1, pos='prep_pick')

    # move x-y motors to location of object
    print('moving x to ' + str(add[0]) + ' and moving y to ' + str(add[1]))
    xtarg = x.move_location(location=float(add[0]), accel=xy_accel, vel=20)
    ytarg = y.move_location(location=float(add[1]), accel=xy_accel, vel=20)
    await loop.create_task(wait_for_xy(xtarg=xtarg, ytarg=ytarg, distance_thresh=(100 + xy_accel * 200)))

    # move specified arm to 'pick' position
    await loop.create_task(wait_for_dxl(200))
    dxl.move_arm_to_pos(arm=side, pos='pick')
    await pub.publish_json('WebClient',
                           {"leftarm": "prep_pick", "rightarm": "prep_pick", "xpos": str(add[0]), "ypos": str(add[1])})

    # when arm has reached target location, energize magnet
    await loop.create_task(wait_for_dxl(190))
    await loop.create_task(mags.energize(side))
    await asyncio.sleep(0.1)  # need to wait a bit for the magnet to suck in the object
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "pick", "leftmag": "1"})
    else:
        await pub.publish_json('WebClient', {"rightarm": "pick", "rightmag": "1"})

    # move specified arm to 'prep-pick' position
    dxl.move_arm_to_pos(arm=side, pos='prep_pick')
    await loop.create_task(wait_for_dxl(120))  # at 180, sometimes rips off
    if side == 0:
        await pub.publish_json('WebClient', {"leftarm": "prep_pick", "leftsensor": str(objid)})
        sendString = '%set sensor:0:objectid=' + str(objid)
    else:
        await pub.publish_json('WebClient', {"rightarm": "prep_pick", "rightsensor": str(objid)})
        sendString = '%set sensor:1:objectid=' + str(objid)

    qnxsock.sendall(bytes(sendString, 'utf-8'))
    qnxsock.recv(4096)


async def present(arms='neither', hand=-1, left_angle=180, right_angle=180, hide_panel='no', xoffset=0):
    # present objects on specified arms to specified hand
    print('Presenting objects on ' + str(arms) + ' arms to hand ' + str(hand))
    global redisslow
    xy_accel = 40

    # input variables"
    # arms (list of ints) 'left', 'right', 'both', or 'neither'
    # hand (list of single int) [0] for left, [1] for right
    # left_angle (integer) angle to rotate left arm
    # right_angle (integer) angle to rotate right arm
    # hide_panel (yes or no) after moving arms into place, do we want to move the panel down to ensure it's out of the way?
    # xoffset (integer) custom x axis offset to position arm(s) relative to standard left and right hand position

    # if arms is empty or -1, ask for arms
    if arms == 'neither':
        print('No arms specified.')
        return

    # if hand isn't 0 or 1, ask which hand we're supposed to present to
    if hand != 0 and hand != 1:
        print('Specify which hand to present to, 0 (left) or 1 (right)')
        return

    left_angle = left_angle - 180  # subtract 180 because, at zero rotation, object is actually upside-down compared to SVG and DGZ
    right_angle = right_angle - 180  # subtract 180 because, at zero rotation, object is actually upside-down compared to SVG and DGZ

    left_angle = left_angle % 360
    right_angle = right_angle % 360
    # if left_angle > 360 or left_angle < 0:
    #     print('left_angle is out of bounds!')
    #     return
    # if right_angle > 360 or right_angle < 0:
    #     print('right_angle is out of bounds!')
    #     return
    if left_angle > 180:
        left_angle = left_angle - 360
    if right_angle > 180:
        right_angle = right_angle - 360

    left_angle *= -1  # FLIP IT TO GET CLOCKWISE=POSITIVE ROTATION
    right_angle *= -1

    # move specified arms to prep_present
    if arms == 'both' or arms == 'left':
        dxl.set_profile_accel(motor=11, accel=130)
        dxl.move_arm_to_pos(arm=0, pos='prep_present', rotation=left_angle)
    if arms == 'both' or arms == 'right':
        dxl.set_profile_accel(motor=21, accel=130)
        dxl.move_arm_to_pos(arm=1, pos='prep_present', rotation=right_angle)

    # move xy to present to specified hand
    hand_xs = await redisslow.get('hand_xs')
    hand_xs = np.array(json.loads(hand_xs))

    xtarg = x.move_location(location=float(hand_xs[hand] + xoffset), accel=xy_accel, vel=20)
    if hide_panel == 'yes':
        ytarg = y.move_location(location=150, accel=25, vel=40)
    await loop.create_task(wait_for_xy(xtarg=xtarg, distance_thresh=(100 + xy_accel * 200)))

    # restart sensor readings (make sure this isnt too early)
    await toggle_touch(1)  # works here

    # once xy is in position, move specified arms to present
    if arms == 'both' or arms == 'left':
        dxl.move_arm_to_pos(arm=0, pos='present', rotation=left_angle)
        await pub.publish_json('WebClient', {"leftarm": "prep_present"})
    if arms == 'both' or arms == 'right':
        dxl.move_arm_to_pos(arm=1, pos='present', rotation=right_angle)
        await pub.publish_json('WebClient', {"rightarm": "prep_present"})

    await wait_for_dxl(300)

    if arms == 'both' or arms == 'left':
        await pub.publish_json('WebClient', {"leftarm": "present", "xpos": str(hand_xs[hand] + xoffset)})
    if arms == 'both' or arms == 'right':
        await pub.publish_json('WebClient', {"rightarm": "present", "xpos": str(hand_xs[hand] + xoffset)})


async def wait_for_dxl(distance_thresh=180):
    print('waiting for dynamixel motors to stop moving')
    # distance_thresh = 180
    distance = 10000
    while distance > distance_thresh:
        a = dxl.sync_get_position()
        b = dxl.sync_get_goal_position()
        distance = max([abs(x) for x in [c - d for c, d in zip(a, b)]])
        # print(distance)
        await asyncio.sleep(0.001)

    return 1


async def wait_for_xy(xtarg='*', ytarg='*', distance_thresh=200):
    # print('waiting for x-y motors to stop moving')

    # 1 mm is ~300 units
    xpos = x.get_position()
    ypos = y.get_position()

    if xtarg == '*':
        distance = abs(ypos - ytarg)
    elif ytarg == '*':
        distance = abs(xpos - xtarg)
    else:
        distance = math.sqrt(abs(xpos - xtarg) ** 2 + abs(ypos - ytarg) ** 2)

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
            
    # print('target reached')
    return 1

async def set_motor_to_dial_or_pattern():
    """
    Continuously checks 'follow_settings["enabled"]'.
    If True, determines target position from motor or pattern, applies the offset,
    and commands the specified target arm motor accordingly.
    """
    try:
        while True:
            if follow_settings["enabled"]:
                if follow_settings["follow_mode"] == "dial":
                    # Read the dial motor position
                    dial_pos = dxl.get_position(follow_settings["dial_motor"])
                    
                    # Convert to degrees (assuming 4096 units = 360° with offset correction)
                    # subtract 90 because thats the center position of the dial
                    # subtract 180 because thats the center position of the object
                    dial_deg = (dial_pos / 4096) * 360 - 90 - 180
                    
                    # Compute the target angle with the specified offset
                    target_angle = dial_deg + follow_settings["offset"]
                    
                    # Move the target arm motor
                    dxl.move_arm_to_pos(arm=follow_settings["target_arm"], pos='present', rotation=target_angle)
                    send_to_dataserver(qnxsock, "grasp/left_angle", DservType.SHORT.value, int(target_angle % 360))
                elif follow_settings["follow_mode"] == "report_only":
                    dial_pos = dxl.get_position(follow_settings["dial_motor"])
                    # Convert to degrees (assuming 4096 units = 360° with offset correction)
                    # subtract 90 because thats the center position of the dial
                    # multiply by negative one to get direction we want
                    dial_angle = ((dial_pos / 4096) * 360 - 90) * -1
                    send_to_dataserver(qnxsock, "grasp/dial_angle", DservType.SHORT.value, int(dial_angle % 360))
                elif follow_settings["follow_mode"] == "pattern":
                    amplitude = 55     # will swing between +/- amplitude
                    period = 4         # time in seconds of 1 rev
                    elapsed = time.time() - follow_settings["start_time"]
                    sine_value = amplitude * math.sin(2 * math.pi * elapsed / period)

                    command = f"%set grasp/pattern_pos={sine_value}\n"
                    qnxsock.sendall(command.encode('utf-8'))
                    result = qnxsock.makefile().readline()
                    print(result)
                    qnxsock.sendall(b'%get grasp/pattern_pos\n')
                    result = qnxsock.makefile().readline()
                    print(result)
                    match = re.search(r'\{(.*?)\}', result)
                    if match:
                        sine_value_returned = float(match.group(1))
                        print(f"sine_value_returned: {sine_value_returned}")
                    else:
                        # Handle the error or set a default value
                        print("No match found, setting sine_value_returned to 0.0")
                        sine_value_returned = 0.0
                    
                    target_angle = int(sine_value_returned + follow_settings["offset"])
                    dxl.move_arm_to_pos(arm=follow_settings["target_arm"], pos='present', rotation=target_angle)
                    send_to_dataserver(qnxsock, "grasp/left_angle", DservType.SHORT.value, int(target_angle % 360))

                else:
                    print('follow_mode should be dial, report_only, or pattern')

            # Yield control to avoid blocking other tasks
            await asyncio.sleep(0.002)

    except asyncio.CancelledError:
        print("Motor follow task was cancelled.")


################################################################################################################################################################################################

#  Functions callable from client

#################################################################################################################################################################################################


async def pick_and_place(hand=[-1], left_id=[-1], right_id=[-1], left_angle=[180], right_angle=[180],
                         return_duplicates=[1], dont_present=[-1], xoffset=[0], reset_dial=[0], dial_following=[0], pattern_following=[0], use_dummy=[0], dummy_ids=[2024, 2036]):
    # put away current objects, if any, get new objects, present those objects
    # input variables:
    # hand (integer) is position where we want to present object. 0 (left) or (1) right
    # left_id (integer) object id to present using left arm
    # right_id (integer) object id to present using right arm
    # left_angle (integer) rotation in degrees for left object. positive angle is counter-clockwise rotation
    # return_duplicates (integer) If we want an object on same arm thats already holding it, do we return it (1) or not (0)?
    # dont_present (integer) -1 for neither, 0 for left, 1 for right. For cases where we want to grab a shape but not present it
    # xoffset (integer) custom x axis offset from default left hand or right hand position
    # reset_dial (integer 0 or 1) if 1, will reset the dial (chan 1) to 1024 and disable the torque at the end
    # dial_following (integer 0 or 1) if 1, will turn on dial following. left arm will follow motor 1 with offset left_angle until instructed to stop                             
    # pattern_following (integer 0 or 1) if 1, will turn on pattern following. left arm will follow sine wave with offset left_angle until instructed to stop                             
    # use_dummy (integer 0 or 1) for conditions where you need to ensure the user cant tell if the shape changed or not, use a dummy on the right arm
    # dummy_ids (list of two integers) if use_dummy, right arm will toggle between these two shapes when the left_id is the same as holding(0)

    print('Picking and Placing')

    global redisslow
    # qnxsock.sendall(b'%set grasp/available=0')
    send_to_dataserver(qnxsock, "grasp/available", DservType.STRING.value, "0")
                                 
    await follow_dial_or_pattern(follow=["False"])

    starttime = time.time()

    hand = int(hand[0])
    left_id = int(left_id[0])
    right_id = int(right_id[0])
    left_angle = int(round(float(left_angle[0])))  # convert from string to float, round it, convert to int
    right_angle = int(round(float(right_angle[0])))
    return_duplicates = int(round(float(return_duplicates[0])))
    dont_present = int(round(float(dont_present[0])))
    xoffset = int(round(float(xoffset[0])))
    reset_dial = int(round(float(reset_dial[0])))
    dial_following = int(round(float(dial_following[0])))
    pattern_following = int(round(float(pattern_following[0])))
    use_dummy = int(round(float(use_dummy[0])))
                             
    # Ensure dummy_ids is a proper list of integers
    if isinstance(dummy_ids, list) and len(dummy_ids) == 1 and isinstance(dummy_ids[0], str):
        # If dummy_ids is a single-element list with a string like "2032,2062", split it
        dummy_ids = list(map(int, dummy_ids[0].split(",")))
    elif isinstance(dummy_ids, str):
        dummy_ids = list(map(int, dummy_ids.split(",")))
    elif isinstance(dummy_ids, (tuple, set)):
        dummy_ids = list(dummy_ids)
    
    # Now perform validation
    if len(dummy_ids) == 2:
        dummy_ids = [int(dummy_ids[0]), int(dummy_ids[1])]
        if dummy_ids[0] == dummy_ids[1]:
            raise ValueError("dummy_ids must contain two different values!")
    else:
        raise ValueError("dummy_ids must contain exactly two values!")
                             

    if hand == -1:
        print('specify which hand to present to, 0 or 1 for left or right')
        return

    # get information from panels database
    fut1 = redisslow.get('panel')
    fut2 = redisslow.get('holding')
    fut3 = redisslow.get('arm_offset')
    panel, holding, arm_offset = await asyncio.gather(fut1, fut2, fut3)
    panel = np.array(json.loads(panel))
    holding = np.array(json.loads(holding))
    arm_offset = np.array(json.loads(arm_offset))
           
    returning = [holding[0]]
    returning.append(holding[1])

    # make list of objects to return, assuming that database and sensor readings agree on what we're holding
    # first, if we're using a dummy object to throw off the user, check if its needed here
    if use_dummy == 1:
        # first, confirm that the client has sent a reasonable request regarding use_dummy
        if right_id > -1:
            print('if youre using a dummy, you cant request something with the right id!')
            return
        if return_duplicates == 1:
            print('if youre using a dummy, you shouldnt also return the duplicate. it defeats the purpose!')
            return
        if dont_present < 1:
            print('if youre using a dummy, you need to set dont_present=1 so we dont present the dummy!')
            return

        # second, check if we need to swap the dummy shape
        # if we want the object on the left arm that is already there, swap the right arm
        if holding[0] == left_id:
            right_id = dummy_ids[0] if dummy_ids[0] != holding[1] else dummy_ids[1]
        # if we arent holding anything with the right arm yet, get the first dummy object
        elif holding[1] == 0:
            right_id = dummy_ids[0]
        # otherwise we already have a dummy object and we dont need to change the right object
        else:
            right_id = int(holding[1])

    await toggle_touch(0)

    # arms that will be used for retrieving objects
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

    holding_list = holding.tolist()
    print('This is what Im holding: ', holding_list)
    print('Will be updating holding to: ', picking)
                             
    picking_list = picking.copy()
    if return_duplicates == 0:
        if picking_list[0] == holding_list[0]:
            holding_list[0] = 0
            picking_list[0] = 0
        if picking_list[1] == holding_list[1]:
            holding_list[1] = 0
            picking_list[1] = 0

    # now we know what we're holding and what we need, lets plan the path of how we're going to get it
    panel, orders = pf.plan_path(holding_list, picking_list, panel, arm_offset)

    # make sure we're still communicating with the dynamixel arms. sometimes the USB craps out and the XY motors still move, causing havoc
    try:
        stats = dxl.sync_error_status()
        if sum(stats) != 0:
            print('dynamixel motors in error state')
            return
    except:
        print('dynamixel motors incommunicado? try resetting USB connection and restarting grasp_server.py')

    # reset the dial if requested
    if (reset_dial):
        dxl.set_torque(1,1)
        dxl.set_position(1, 1024)
                             
    # step through the plan
    for i in range(len(orders)):
        order = orders[i][0][0]
        side = orders[i][1][0]
        location = orders[i][2]

        if order == 'd':
            print('dropping off with arm ' + str(side) + ' at location ' + str(location))
            await return_object(side=side, add=location)

        if order == 'p':
            print('picking up with arm ' + str(side) + ' at location ' + str(location))
            if side == 0:
                await retrieve(side=side, objid=left_id, add=location)
            else:
                await retrieve(side=side, objid=right_id, add=location)

    # restart sensor readings (i think this one doesnt actually work because something in present undoes it
    await toggle_touch(1)

    # move arms to present
    if dont_present == -1:
        print("presenting both")
        await present(arms=arms, hand=hand, left_angle=left_angle, right_angle=right_angle, hide_panel='yes',
                      xoffset=xoffset)
        send_to_dataserver(qnxsock, "grasp/left_angle", DservType.SHORT.value, int(left_angle % 360))
        send_to_dataserver(qnxsock, "grasp/right_angle", DservType.SHORT.value, int(right_angle % 360))
    elif dont_present == 0:
        print("presenting right only")
        await present(arms='right', hand=hand, right_angle=right_angle, hide_panel='yes', xoffset=xoffset)
        send_to_dataserver(qnxsock, "grasp/right_angle", DservType.SHORT.value, int(right_angle % 360))
    elif dont_present == 1:
        print("presenting left only")
        await present(arms='left', hand=hand, left_angle=left_angle, hide_panel='yes', xoffset=xoffset)
        send_to_dataserver(qnxsock, "grasp/left_angle", DservType.SHORT.value, int(left_angle % 360))

    # turn off torque on dial if using
    if (reset_dial):
        dxl.set_torque(1,0)

    print('Updating holding to: ', picking)

    # update redis with what the panel looks like
    fut1 = redisslow.set('panel', json.dumps(panel.tolist()))
    fut2 = redisslow.set('holding', json.dumps(picking))
    await asyncio.gather(fut1, fut2)

    # if we're supposed to turn on dial following, do that now
    if dial_following and not pattern_following:
        await follow_dial_or_pattern(follow=["True"], mode=["dial"], offset=[left_angle])
    elif pattern_following and not dial_following:
        await follow_dial_or_pattern(follow=["True"], mode=["pattern"], offset=[left_angle+180])
    elif pattern_following and dial_following:
        print('cant do both dial and pattern following')

    # send message to qnx to store this time as the "stimulus onset time"
    # qnxsock.sendall(b'%set grasp/available=1')
    send_to_dataserver(qnxsock, "grasp/available", DservType.STRING.value, "1")
    follow_settings["start_time"] = time.time()

    print(f"pick_and_place took {time.time() - starttime:.2f} seconds")


async def put_away(side=[-1], left_id=[-1], right_id=[-1], get_next=[0]):
    # put away currently held objects
    # input variables:
    # side (integer) is sides we want to put away. 0 (left) or (1) right or (2) for both
    # left_id (integer). if specified, overrules whatever the redis database says we're holding
    # right_id (integer). if specified, overrules whatever the redis database says we're holding
    # get_next (binary). if 1, that means we need to extend the arm to prepare to put another object away

    global redisslow

    # qnxsock.sendall(b'%set grasp/available=0')
    send_to_dataserver(qnxsock, "grasp/available", DservType.STRING.value, "0")
    await follow_dial_or_pattern(follow=["False"])

    side = int(side[0])
    left_id = int(left_id[0])
    right_id = int(right_id[0])
    get_next = int(get_next[0])

    if side == -1:
        print('specify which sides to put away. 0 (left), 1 (right), 2 (both)')
        return

    # get information from panels database
    fut1 = redisslow.get('panel')
    fut2 = redisslow.get('holding')
    fut3 = redisslow.get('arm_offset')
    panel, holding, arm_offset = await asyncio.gather(fut1, fut2, fut3)
    panel = np.array(json.loads(panel))
    holding = np.array(json.loads(holding))
    arm_offset = np.array(json.loads(arm_offset))

    # if we're told what we're holding, change redis to match
    if left_id > -1:
        holding[0] = left_id
    if right_id > -1:
        holding[1] = right_id

    await toggle_touch(0)  # stop reading from touch sensors

    # make list of objects to return, assuming that database and sensor readings agree on what we're holding
    if holding[0]:
        if side == 0 or side == 2:
            returning = [holding[0]]
            remaining = [0]
        else:
            returning = [0]
            remaining = [holding[0]]
    elif not holding[0]:
        returning = [0]
        remaining = [holding[0]]
    else:
        returning = [0]
        remaining = [0]
        print('incompatibility between what the database says and what sensors say for left')
        # return

    if holding[1]:
        if side == 1 or side == 2:
            returning.append(holding[1])
            remaining.append(0)
        else:
            returning.append(0)
            remaining.append(holding[1])
    elif not holding[1]:
        returning.append(0)
        remaining.append(holding[1])
    else:
        returning.append(0)
        print('incompatibility between what the database says and what sensors say for right')
        # return

    # now we know what we're holding and what we need, lets plan the path of how we're going to get it
    panel, orders = pf.plan_path(returning, [0, 0], panel, arm_offset)

    for i in range(len(orders)):
        order = orders[i][0][0]
        side = orders[i][1][0]
        location = orders[i][2]

        if order == 'd':
            print('dropping off with arm ' + str(side) + ' at location ' + str(location))
            await return_object(side=side, add=location)

    await toggle_touch(1)  # resume reading from touch sensors

    # if we need to get another object from the user, extend the arm
    if get_next:
        # at this point, the arm is probably not even started to move out from pick position. wait a bit.
        await loop.create_task(wait_for_dxl(100))  #
        await present(arms='left', hand=1)
        await loop.create_task(mags.energize(0))
        if side == 0 or side == 2:
            await pub.publish_json('WebClient', {"leftmag": "1"})
        if side == 1 or side == 2:
            await pub.publish_json('WebClient', {"rightmag": "1"})

    # update redis with what the panel looks like
    fut1 = redisslow.set('panel', json.dumps(panel.tolist()))
    fut2 = redisslow.set('holding', str(remaining))
    await asyncio.gather(fut1, fut2)


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
    pos = dxl.sync_get_position()
    print('positions of all 6 dxl motors: ', pos)


async def set_dxl_positions(side=[-1], position=['blah'], rotation=[0]):
    # Works to set position explicitly using triplet for an arm (e.g., 50, 100, 1050) or prescribed settings (e.g., prep_pick)
    print('setting positions of one arm')
    side = int(side[0])
    position = str(position[0])
    rotation = rotation[0]  # Keep as string to check for "m1"

    print(position)
    print(position.split(','))

    if side not in [0, 1]:
        print('side must be 0 (left) or 1 (right)')
        return

    # Check if rotation is in the form "m1-<angle>"
    match = re.match(r"m1-(\d+)", str(rotation))
    if rotation == "m1" or match:
        motor1_pos = dxl.get_position(1)  # Read motor 1 position
        if 0 <= motor1_pos <= 4096:
            motor1_deg = (motor1_pos / 4096) * 360 - 270  # Convert to degrees in range -180 to 180
            if match:
                base_angle = int(match.group(1))
                rotation = base_angle + motor1_deg
            else:
                rotation = motor1_deg  # Standard "m1" case
        else:
            print(f'Invalid motor 1 position: {motor1_pos}')
            return

    rotation = int(rotation)  # Convert to integer after processing

    if len(position.split(',')) == 1:
        print('heading to move arm to pos')
        dxl.move_arm_to_pos(arm=side, pos=position, rotation=rotation)
        if position != 'present':
            # qnxsock.sendall(b'%set grasp/available=0')
            send_to_dataserver(qnxsock, "grasp/available", DservType.STRING.value, "0")
            await follow_dial_or_pattern(follow=["False"])
        
        await loop.create_task(wait_for_dxl(50))
        
        if side == 0:
            await pub.publish_json('WebClient', {"leftarm": position})
        else:
            await pub.publish_json('WebClient', {"rightarm": position})
    
    elif len(position.split(',')) == 3:
        print('heading to sync set position')
        motors = [11, 12, 13] if side == 0 else [21, 22, 23]
        dxl.sync_set_position(motors, json.loads(position))


async def check_dxl_errors():
    print('checking for dxl errors')
    errs = dxl.sync_error_status()
    print(errs)

async def reset_dial(dial_motor=[1]):
    dxl.set_torque(int(dial_motor[0]),1)
    dxl.set_position(int(dial_motor[0]), 1024)

# call it dial_angle

async def follow_dial_or_pattern(follow=['True'], mode=['dial'], offset=[0], dial_motor=[1], target_arm=[0]):
    # mode="report_only" means dont do anything except read the dial_angle and send it to dserv
    # Turns on dial following carried out by set_motor_to_dial_or_pattern()
    enable = follow[0].lower() == "true"
    
    if enable:
        dxl.set_torque(int(dial_motor[0]), 0)                  # disable motor torque so you can turn it
        follow_settings["offset"] = int(-1 * offset[0] + 360)
        follow_settings["dial_motor"] = int(dial_motor[0])
        follow_settings["target_arm"] = int(target_arm[0])
        follow_settings["follow_mode"] = mode[0]
    
    follow_settings["enabled"] = enable         # enables or disables according to follow setting

    print(f"Updated follow settings: {follow_settings}")



async def enable_xy():
    print('enabling x-y motors')


async def disable_xy():
    print('disabling X-Y motors')


async def find_bounds(axis=['a'], direction=[-1]):
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
        await x.find_bound(direction, current=1.0)
    else:
        if direction == 1:
            await y.find_bound(direction, current=0.1)
        else:
            await y.find_bound(direction, current=1.5)


async def move_xy_distance_mm(axis=['a'], distance=[0]):
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


async def move_xy_to_location(axis=['a'], location=[-1], accel=[25], vel=[3]):
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
        print(xtarg)
        print(int(xtarg))
        await loop.create_task(wait_for_xy(xtarg=xtarg))
        # await wait_for_xy()
        await pub.publish_json('WebClient', {"xpos": str(location)})
    else:
        ytarg = y.move_location(location=location, accel=accel, vel=vel)
        await loop.create_task(wait_for_xy(ytarg=ytarg))
        # await wait_for_xy
        await pub.publish_json('WebClient', {"ypos": str(location)})


async def magnets(left_status=[-1], right_status=[-1]):
    # left_status = 0 means turn off that magnet, 1 turn on

    left_status = int(left_status[0])
    right_status = int(right_status[0])

    if left_status == 0:
        await toggle_touch(0)  # off
        await asyncio.sleep(0.01)
        await loop.create_task(mags.deenergize(0))
        await toggle_touch(1)  # left on
        await pub.publish_json('WebClient', {"leftmag": "0"})

    elif left_status == 1:
        await toggle_touch(0)  # left off
        await asyncio.sleep(0.01)
        await loop.create_task(mags.energize(0))
        await toggle_touch(1)  # left on
        await pub.publish_json('WebClient', {"leftmag": "1"})

    if right_status == 0:
        await toggle_touch(0)  # right off
        await asyncio.sleep(0.01)
        await loop.create_task(mags.deenergize(1))
        await toggle_touch(1)  # right on
        await pub.publish_json('WebClient', {"rightmag": "0"})
    elif right_status == 1:
        await toggle_touch(0)  # right off
        await asyncio.sleep(0.01)
        await loop.create_task(mags.energize(1))
        await toggle_touch(1)  # right on
        await pub.publish_json('WebClient', {"rightmag": "1"})

async def toggle_touch(status):
    if status:
        qnxsock.sendall(b'%set sensor:control:activate=0\n')
        qnxsock.sendall(b'%set sensor:control:activate=1\n')
    else:
        qnxsock.sendall(b'%set sensor:control:deactivate=0\n')
        qnxsock.sendall(b'%set sensor:control:deactivate=1\n')

   


    b = qnxsock.recv(8192)
    print(b.decode().strip())


async def change_address(row, col, shapeid):
    # changes the address of a specified shape on the panel
    global redisslow
    row = int(row[0])  # row where shape is going
    col = int(col[0])  # col where shape is going
    shapeid = int(shapeid[0])  # shape id being placed

    # get the panel values from redis
    panel = await redisslow.get('panel')
    panel = np.array(json.loads(panel))

    # find if object is already on panel and remove it if so
    add = np.where(panel[:, :, 0] == shapeid)
    for i in range(len(add[0])):
        panel[add[0][i], add[1][i], 0] = 0

    # put shape at new address
    panel[row, col, 0] = shapeid

    # update redis
    await redisslow.set('panel', json.dumps(panel.tolist()))


async def remove_object(shapeid):
    # user specifies an object id which they have manually pulled off the panel
    shapeid = int(shapeid[0])  # shape id being placed
    global redisslow
    panel = await redisslow.get('panel')
    panel = np.array(json.loads(panel))
    panel = pf.remove_from_panel(panel, shapeid)
    if type(panel) is np.ndarray:  # should either return a numpy array of the panel or a zero
        await redisslow.set('panel', json.dumps(panel.tolist()))


async def return_inventory():
    # returns current inventory of shapes as reply to socket request
    global redisslow
    panel = await redisslow.get('panel')
    panel = np.array(json.loads(panel))
    holding = await redisslow.get('holding')
    holding = np.array(json.loads(holding))

    # grab shape ids, convert to linear array, append holding, convert to integer
    ids = np.reshape(panel[:, :, 0], -1)
    ids = np.append(ids, holding)
    ids = ids.astype(int)
    # remove zeros and 99999
    ids = ids[np.nonzero(ids)]
    ids = ids[ids < 99999]

    # return string
    return np.array2string(ids, separator=' ')


async def publish_inventory():
    global redisslow
    panel = await redisslow.get('panel')
    panel = np.array(json.loads(panel))
    holding = await redisslow.get('holding')
    holding = np.array(json.loads(holding))

    pshape = panel.shape
    pstring = panel.astype('U256')
    hstring = holding.astype('U256')

    # loop through all objects on the panel and holding and replace id number with filename
    for r in range(pshape[0]):
        for c in range(pshape[1]):
            if panel[r][c][0] > 0 and panel[r][c][0] < 99999:
                id = (str(panel[r][c][0]),)
                sqlc.execute('SELECT SVG FROM objectsTable WHERE objectID=?', id)
                svg = sqlc.fetchall()
                if len(svg) == 1:
                    pstring[r][c][0] = svg[0][0]

    for i in range(2):
        if holding[i] > 0 and holding[i] < 99999:
            id = (str(holding[i]),)
            sqlc.execute('SELECT SVG FROM objectsTable WHERE objectID=?', id)
            svg = sqlc.fetchall()
            if len(svg) == 1:
                hstring[i] = svg[0][0]

    await pub.publish_json('WebClientInventory',
                           {"panel": json.dumps(pstring[:, :, 0].tolist()), "holding": json.dumps(hstring.tolist())})


async def get_touch_status():
    # one shot retrieve all relevant information from dserv about the touch sensor status
    qnxsock.sendall(b'%set sensor:0:id=2012')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the first')

    qnxsock.sendall(b'%set sensor:1:id=2013')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the second')

    qnxsock.sendall(b'%get sensor:0:id')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the third')

    qnxsock.sendall(b'%get sensor:1:id')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the fourth')

    qnxsock.sendall(b'%get sensor:control:activate')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the fifth')

    qnxsock.sendall(b'%get sensor:control:deactivate')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the sixth')

    qnxsock.sendall(b'%get sensor:0:vals')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the seventh')

    qnxsock.sendall(b'%get sensor:1:vals')
    b = qnxsock.recv(4096)
    print(b.decode().strip())
    print('that was the eighth')


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
    'follow_dial_or_pattern': follow_dial_or_pattern,
    'reset_dial': reset_dial,

    'enable_xy': enable_xy,
    'disable_xy': disable_xy,
    'find_bounds': find_bounds,
    'move_xy_distance_mm': move_xy_distance_mm,
    'move_xy_to_location': move_xy_to_location,

    'magnets': magnets,

    'change_address': change_address,
    'remove_object': remove_object,
    'return_inventory': return_inventory,
    'publish_inventory': publish_inventory,

    'get_touch_status': get_touch_status,

    'ping': ping,
    'abort': abort
}


async def handle_request(reader, writer):
    result = '101'
    data = await reader.read(200)  # wait for data to become available
    message = data.decode()  # decode it as utf-8 i think
    global active_task

    try:
        print('message: ' + message)

        message = message.split(' ')[1]  # message is usually "GET blagblahblah HTTP/1.1"
        req = parse_qs(urlparse(message).query)  # grab the key/value pairs sent after ? in the URL

        if "function" in req:
            fx = req['function'][0].strip()  # get name of function we're supposed to call
            req.pop('function')  # remove it from dictionary
            print(req)

            if fx == 'abort':
                loop.create_task(abort())
                result = 'aborted'  # 200 ok
            else:
                if len(asyncio.all_tasks(loop)) > 4:  # if we're already doing something
                    print('busy')
                    result = 'busy'  # 504 timeout
                elif fx == 'ping':
                    result = 'pong'  # 100 continue
                elif fx == 'return_inventory':
                    active_task = loop.create_task(fx_list[fx](**req))  # call function with requested arguments
                    result = await active_task
                else:
                    active_task = loop.create_task(fx_list[fx](**req))  # call function with requested arguments
                    result = 'accepted'  # 200 ok
        else:
            result = 'invalid'  # 418 im a teapot

    except:
        print("Unexpected error:", sys.exc_info()[0])
        result = 'error'  # 500 internal server error

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


async def reader(ch):
    while (await ch.wait_message()):
        msg = await ch.get_json()
        print("Got Message:", msg)


async def connect_redis():
    global redisslow, pub

    # Create Redis connections (no loop needed)
    redisslow = redis.Redis(host='localhost', port=6380)
    pub = redis.Redis(host='localhost', port=6379)

    # Publish a JSON message
    await pub.publish('WebClient', redis.client.JsonEncoder().encode({"leftmag": "0", "rightmag": "0"}))


async def disconnect_redis():
    global redisslow, pub
    # redisfast.close()
    # await redisfast.wait_closed()

    redisslow.close()
    await redisslow.wait_closed()

    pub.close()
    await pub.wait_closed()


loop = asyncio.get_event_loop()  # makes a new event loop if one doesnt exist
loop.create_task(connect_redis())
loop.create_task(set_motor_to_dial_or_pattern()) # loop that runs continuosly and can be used to follow a dial with follow_settings["enabled"] = True  

coro = asyncio.start_server(handle_request, '192.168.88.84', 8888, loop=loop)  # start a socket server
# coro = asyncio.start_server(handle_request, '100.0.0.84', 8888, loop=loop)  # start a socket server
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
# sock.close()
qnxsock.close()
