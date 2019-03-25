import numpy as np
import dynamixel_sdk as dxlfx                    # Uses Dynamixel SDK library
import dynamixel_constants as dxlcx
import time
from datetime import datetime
import atexit


class D2C(object):
    def __init__(self):
        atexit.register(self.exit_handler)       # register the function to run on exit

        self.port_handler = dxlfx.PortHandler(dxlcx.DEVICENAME)
        self.packet_handler = dxlfx.PacketHandler(dxlcx.PROTOCOL)

        # Open port
        if self.port_handler.openPort():
            print("Opened port", dxlcx.DEVICENAME)
        else:
            print("Failed to open the port!")

        # Set baud rate
        if self.port_handler.setBaudRate(dxlcx.BAUDRATE):
            print("Set baud rate to", dxlcx.BAUDRATE)
        else:
            print("Failed to change the baud rate!")

        # Set up groups for sync reads and writes
        self.groupMoving = dxlfx.GroupSyncRead(self.port_handler, self.packet_handler, dxlcx.ADDR_MOVING, 1)
        for i in range(0, len(dxlcx.IDs)):                          # for each arm
            for ii in range(0, len(dxlcx.IDs[0])):                  # for each motor in each arm
                self.groupMoving.addParam(dxlcx.IDs[i][ii])         # add this motor to list

        self.groupGetPosition = dxlfx.GroupSyncRead(self.port_handler, self.packet_handler, dxlcx.ADDR_PRESENT_POSITION, 4)
        for i in range(0, len(dxlcx.IDs)):                          # for each arm
            for ii in range(0, len(dxlcx.IDs[0])):                  # for each motor in each arm
                self.groupGetPosition.addParam(dxlcx.IDs[i][ii])    # add this motor to list

        self.groupGetGoalPosition = dxlfx.GroupSyncRead(self.port_handler, self.packet_handler, dxlcx.ADDR_GOAL_POSITION,4)
        for i in range(0, len(dxlcx.IDs)):  # for each arm
            for ii in range(0, len(dxlcx.IDs[0])):  # for each motor in each arm
                self.groupGetGoalPosition.addParam(dxlcx.IDs[i][ii])  # add this motor to list

        self.groupSetPosition = dxlfx.GroupSyncWrite(self.port_handler, self.packet_handler, dxlcx.ADDR_GOAL_POSITION, 4)

        # check connection to motors
        result = self.sync_get_position()
        if sum(result):
            print("Communicating with servos")
        else:
            print("Failed to connect to servos, 12v power missing?")


    #
    #
    # def move_present_to_neutral(self, side):
    #     # side=0 for left, side=1 for right
    #     # sleeptimes = [0.2, 0.1, 0.2, 0.1]
    #     init_time = datetime.now()
    #     for i in range(1, len(dxlcx.P2N[side])):  # if length=4, counts 1 2 3
    #         self.sync_set_position(dxlcx.IDs[side], dxlcx.P2N[side][i].tolist())
    #         a = datetime.now()
    #         time.sleep(.05)
    #         lets_wait = 1
    #         while lets_wait:
    #             moving = self.sync_get_moving()
    #             if moving[3] == 0 & moving[4] == 0:
    #                 b = datetime.now()
    #                 lets_wait = 0
    #
    #         print(b - a)
    #
    #     print(datetime.now() - init_time)
    #
    #
    #
    # def move_neutral_to_present(self, side):
    #     # sleeptimes = [0.2, 0.1, 0.2, 0.1]
    #     init_time = datetime.now()
    #     for i in range(len(dxlcx.P2N[side])-2, -1, -1):  # if length=4, counts 2 1 0
    #         self.sync_set_position(dxlcx.IDs[side], dxlcx.P2N[side][i].tolist())
    #         a = datetime.now()
    #         time.sleep(.05)
    #         lets_wait = 1
    #         while lets_wait:
    #             moving = self.sync_get_moving()
    #             if moving[0] == 0 & moving[1] == 0:
    #                 b = datetime.now()
    #                 lets_wait = 0
    #
    #         print(b - a)
    #
    #     print(datetime.now() - init_time)
    #
    #
    # def move_neutral_to_change(self, side):
    #     # side=0 for left, side=1 for right
    #     # sleeptimes = [0.2, 0.1, 0.2, 0.1]
    #     init_time = datetime.now()
    #     for i in range(1, len(dxlcx.N2C[side])):  # if length=4, counts 1 2 3
    #         self.sync_set_position(dxlcx.IDs[side], dxlcx.N2C[side][i].tolist())
    #         a = datetime.now()
    #         time.sleep(.05)
    #         lets_wait = 1
    #         while lets_wait:
    #             moving = self.sync_get_moving()
    #             if moving[3] == 0 & moving[4] == 0:
    #                 b = datetime.now()
    #                 lets_wait = 0
    #
    #         print(b - a)
    #
    #     print(datetime.now() - init_time)
    #
    # def move_change_to_neutral(self, side):
    #     # sleeptimes = [0.2, 0.1, 0.2, 0.1]
    #     init_time = datetime.now()
    #     for i in range(len(dxlcx.N2C[side]) - 2, -1, -1):  # if length=4, counts 2 1 0
    #         self.sync_set_position(dxlcx.IDs[side], dxlcx.N2C[side][i].tolist())
    #         a = datetime.now()
    #         time.sleep(.05)
    #         lets_wait = 1
    #         while lets_wait:
    #             moving = self.sync_get_moving()
    #             if moving[0] == 0 & moving[1] == 0:
    #                 b = datetime.now()
    #                 lets_wait = 0
    #
    #         print(b - a)
    #
    #     print(datetime.now() - init_time)
    #


    ###################################################
    ## Simple reads/writes
    ###################################################


    def get_moving_thresh(self, motor):
        val, result, error = self.packet_handler.read4ByteTxRx(self.port_handler, motor, dxlcx.ADDR_MOVING_THRESH)
        self.error_handler('get_moving_thresh: ', result, error)
        return val

    def set_moving_thresh(self, motor, thresh):
        result, error = self.packet_handler.write4ByteTxRx(self.port_handler, motor, dxlcx.ADDR_MOVING_THRESH, thresh)
        self.error_handler('set_moving_thresh: ', result, error)

    def get_torque(self, motor):
        val, result, error = self.packet_handler.read1ByteTxRx(self.port_handler, motor, dxlcx.ADDR_TORQUE_ENABLE)
        self.error_handler('get_torque: ', result, error)
        return val

    def set_torque(self, motor, enable):
        # enable or disable torque control of motor
        result, error = self.packet_handler.write1ByteTxRx(self.port_handler, motor, dxlcx.ADDR_TORQUE_ENABLE, enable)
        self.error_handler('set_torque: ', result, error)

    def get_op_mode(self, motor):
        # 0=current control, 1=velocity, 3=position, 4=extended position, 5=current based position, 16=pwm control
        val, result, error = self.packet_handler.read1ByteTxRx(self.port_handler, motor, dxlcx.ADDR_OPERATING_MODE)
        self.error_handler('get_op_mode: ', result, error)
        return val

    def set_op_mode(self, motor, mode):
        # 0=current control, 1=velocity, 3=position, 4=extended position, 5=current based position, 16=pwm control
        result, error = self.packet_handler.write1ByteTxRx(self.port_handler, motor, dxlcx.ADDR_OPERATING_MODE, mode)
        self.error_handler('set_op_mode: ', result, error)

    def get_position(self, motor):
        val, result, error = self.packet_handler.read4ByteTxRx(self.port_handler, motor, dxlcx.ADDR_PRESENT_POSITION)
        self.error_handler('get_position: ', result, error)
        return val

    def set_position(self, motor, position):
        result, error = self.packet_handler.write4ByteTxRx(self.port_handler, motor, dxlcx.ADDR_GOAL_POSITION, position)
        self.error_handler('set_position: ', result, error)

    def get_current_limit(self, motor):
        # only relevant if in correct mode, like current limited position mode
        val, result, error = self.packet_handler.read2ByteTxRx(self.port_handler, motor, dxlcx.ADDR_CURRENT_LIMIT)
        self.error_handler('get_current_limit: ', result, error)
        return val

    def set_current_limit(self, motor, limit):
        # only relevant if in correct mode, like current limited position mode
        result, error = self.packet_handler.write2ByteTxRx(self.port_handler, motor, dxlcx.ADDR_CURRENT_LIMIT, limit)
        self.error_handler('set_current_limit: ', result, error)

    def get_moving(self, motor):
        # returns 1 if motor is moving, 0 if not
        val, result, error = self.packet_handler.read1ByteTxRx(self.port_handler, motor, dxlcx.ADDR_MOVING)
        self.error_handler('get_current_limit: ', result, error)
        return val

    def get_moving_status(self, motor):
        # gives more info about moving status including can't reach target (8?)
        val, result, error = self.packet_handler.read1ByteTxRx(self.port_handler, motor, dxlcx.ADDR_MOVING_STATUS)
        self.error_handler('get_moving_status: ', result, error)
        return val

    def get_goal_pwm(self, motor):
        val, result, error = self.packet_handler.read2ByteTxRx(self.port_handler, motor, dxlcx.ADDR_GOAL_PWM)
        self.error_handler('get_goal_pwm: ', result, error)
        return val

    def set_goal_pwm(self, motor, limit):
        #determines, in part, how much torque the motor will apply
        result, error = self.packet_handler.write2ByteTxRx(self.port_handler, motor, dxlcx.ADDR_GOAL_PWM, limit)
        self.error_handler('set_goal_pwm: ', result, error)

    def get_max_position(self, motor):
        val, result, error = self.packet_handler.read4ByteTxRx(self.port_handler, motor, dxlcx.ADDR_MAX_POSITION)
        self.error_handler('get_moving_status: ', result, error)
        return val

    def set_max_position(self, motor, limit):
        result, error = self.packet_handler.write4ByteTxRx(self.port_handler, motor, dxlcx.ADDR_MAX_POSITION, limit)
        self.error_handler('set_current_limit: ', result, error)



    ##############################################################
    ## Reads/writes for multiple motors
    ##############################################################

    def sync_get_moving(self):
        result = self.groupMoving.txRxPacket()
        self.error_handler('sync_moving: ', result, 0)

        moving = []
        for i in range(0, len(dxlcx.IDs)):                          # for each arm
            for ii in range(0, len(dxlcx.IDs[0])):                  # for each motor in each arm
                moving.append(self.groupMoving.getData(dxlcx.IDs[i][ii], dxlcx.ADDR_MOVING_STATUS, 1))

        return moving

    def sync_get_position(self):
        result = self.groupGetPosition.txRxPacket()
        self.error_handler('sync_get_position: ', result, 0)

        position = []
        for i in range(0, len(dxlcx.IDs)):                          # for each arm
            for ii in range(0, len(dxlcx.IDs[0])):                  # for each motor in each arm
                position.append(self.groupGetPosition.getData(dxlcx.IDs[i][ii], dxlcx.ADDR_PRESENT_POSITION, 4))

        return position

    def sync_get_goal_position(self):
        result = self.groupGetGoalPosition.txRxPacket()
        self.error_handler('sync_get_goal_position: ', result, 0)

        position = []
        for i in range(0, len(dxlcx.IDs)):                          # for each arm
            for ii in range(0, len(dxlcx.IDs[0])):                  # for each motor in each arm
                position.append(self.groupGetGoalPosition.getData(dxlcx.IDs[i][ii], dxlcx.ADDR_GOAL_POSITION, 4))

        return position


    def sync_set_position(self, motors, positions):
        # inputs must be arrays (can be length=1)
        # each element in motors array corresponds to same element in positions array
        # e.g., sync_set_position([11],[2000])
        # e.g., sync_set_position([11, 12, 13],[2000, 1000, 400])
        # Make sure we're given lists
        if type(motors) != list or type(positions) != list:
            print("sync_set_position: Input variables must be type: list!")
            return

        # Make sure we have equal-length input arrays
        if len(motors) != len(positions):
            print("sync_set_position: Need the same number of motors and positions!")
            return

        for i in range(0, len(motors)):
            self.groupSetPosition.addParam(motors[i], self.int_to_bytes(positions[i]))

        result = self.groupSetPosition.txPacket()               # send command
        self.error_handler('sync_set_position: ', result, 0)    # check for errors
        self.groupSetPosition.clearParam()                      # clean up


    def set_torque_all(self, enable):
        # loop through all motors and turn the torque on or off

        IDs = sum(dxlcx.IDs, [])  # turn it into a 1-d list

        for id in IDs:
            self.set_torque(id, enable)

    def set_moving_thresh_all(self):
        # loop through all motors and set the moving threshold

        IDs = sum(dxlcx.IDs, [])  # turn it into a 1-d list
        threshs = sum(dxlcx.threshs, [])

        for id, thresh in zip(IDs, threshs):
            self.set_moving_thresh(id, thresh)

    def set_moving_pwms(self):
        # loop through all motors and set the moving threshold

        IDs = sum(dxlcx.IDs, [])  # turn it into a 1-d list
        moving_pwms = sum(dxlcx.moving_pwms, [])

        for id, moving_pwm in zip(IDs, moving_pwms):
            self.set_goal_pwm(id, moving_pwm)

    def move_arm_to_pos(self, arm=-1, pos='unspecified', rotation=0):
        # moves arm to a specified position
        # args:
        # arm (int) 0 (left) or 1 (right)
        # pos (string) pick, prep_pick, prep_present, present
        # rotation (degrees) (int -180 -- 180)

        if arm != 0 and arm != 1:
            print('invalid arm choice, pick 0 or 1')
            return 0

        if rotation > 180 or rotation < -180:
            print('please give rotation in degrees in range -180 to 180')
            return 0



        armmult = arm * 2 - 1   # produces -1 for left and 1 for right

        # depending on arm and position specified, determine the dxl positions for three motors
        if pos == 'pick':
            position = [dxlcx.pick_pos[arm][0],
                        dxlcx.pick_pos[arm][1],
                        dxlcx.pick_pos[arm][2]]
        elif pos == 'prep_pick':
            position = [dxlcx.pick_pos[arm][0] + 150 * armmult,
                        dxlcx.pick_pos[arm][1],
                        dxlcx.pick_pos[arm][2]]
        elif pos == 'prep_present':
            position = [dxlcx.pick_pos[arm][0] + 250 * armmult,
                        dxlcx.pick_pos[arm][1] + 2048 * armmult,
                        dxlcx.pick_pos[arm][2] + round(rotation * 4096/360)]
        elif pos == 'present':
            position = [dxlcx.pick_pos[arm][0] + 750 * armmult,
                        dxlcx.pick_pos[arm][1] + 2048 * armmult,
                        dxlcx.pick_pos[arm][2] + round(rotation * 4096/360)]
        else:
            print('invalid position specified')
            return 0

        # move motors
        print('moving motors ' + str(dxlcx.IDs[arm]) + ' to position ' + str(position))
        self.sync_set_position(dxlcx.IDs[arm], position)
        return 1



    ###################################################
    ## Misc functions
    ###################################################

    def error_handler(self, label, comm_result, error):
        if comm_result != dxlcx.COMM_SUCCESS:
            print(label)
            print("%s" % self.packet_handler.getTxRxResult(comm_result))
        elif error != 0:
            print(label)
            print("%s" % self.packet_handler.getRxPacketError(error))

    def int_to_bytes(self, number):
        comps = [dxlfx.DXL_LOBYTE(dxlfx.DXL_LOWORD(number)),
                 dxlfx.DXL_HIBYTE(dxlfx.DXL_LOWORD(number)),
                 dxlfx.DXL_LOBYTE(dxlfx.DXL_HIWORD(number)),
                 dxlfx.DXL_HIBYTE(dxlfx.DXL_HIWORD(number))]
        return comps

    def exit_handler(self):
        print('Closing port...')
        self.port_handler.closePort()


# if __name__ == "__main__":
#     dxl = D2C()

