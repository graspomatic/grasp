import os
import ctypes
import dynamixel_functions as dxlfx                    # Uses Dynamixel SDK library
import dynamixel_constants as dxlcx



class D2C(object):
    def __init__(self):
        self.port_num = dxlfx.portHandler(dxlcx.DEVICENAME)

        dxlfx.packetHandler()

        # Open port
        if dxlfx.openPort(self.port_num):
            print("Succeeded to open the port!")
        else:
            print("Failed to open the port!")
            # quit()

        # Set port baudrate
        if dxlfx.setBaudRate(self.port_num, dxlcx.BAUDRATE):
            print("Succeeded to change the baudrate!")
        else:
            print("Failed to change the baudrate!")
            # quit()

    def enable_torque(self, motor):
        dxlfx.write1ByteTxRx(self.port_num, dxlcx.PROTOCOL, motor, dxlcx.ADDR_TORQUE_ENABLE, 1)
        dxl_comm_result = dxlfx.getLastTxRxResult(self.port_num, dxlcx.PROTOCOL)
        dxl_error = dxlfx.getLastRxPacketError(self.port_num, dxlcx.PROTOCOL)
        if dxl_comm_result != dxlcx.COMM_SUCCESS:
            print(dxlfx.getTxRxResult(dxlcx.PROTOCOL, dxl_comm_result))
        elif dxl_error != 0:
            print(dxlfx.getRxPacketError(dxlcx.PROTOCOL, dxl_error))
        else:
            print("Torque enabled for motor", motor)

    def disable_torque(self, motor):
        dxlfx.write1ByteTxRx(self.port_num, dxlcx.PROTOCOL, motor, dxlcx.ADDR_TORQUE_ENABLE, 0)
        dxl_comm_result = dxlfx.getLastTxRxResult(self.port_num, dxlcx.PROTOCOL)
        dxl_error = dxlfx.getLastRxPacketError(self.port_num, dxlcx.PROTOCOL)
        if dxl_comm_result != dxlcx.COMM_SUCCESS:
            print(dxlfx.getTxRxResult(dxlcx.PROTOCOL, dxl_comm_result))
        elif dxl_error != 0:
            print(dxlfx.getRxPacketError(dxlcx.PROTOCOL, dxl_error))
        else:
            print("Torque disabled for motor", motor)

    def move(self, motor, position):
        # Write goal position
        dxlfx.write4ByteTxRx(self.port_num, dxlcx.PROTOCOL, motor, dxlcx.ADDR_GOAL_POSITION, position)
        dxl_comm_result = dxlfx.getLastTxRxResult(self.port_num, dxlcx.PROTOCOL)
        dxl_error = dxlfx.getLastRxPacketError(self.port_num, dxlcx.PROTOCOL)
        if dxl_comm_result != dxlcx.COMM_SUCCESS:
            print(dxlfx.getTxRxResult(dxlcx.PROTOCOL, dxl_comm_result))
        elif dxl_error != 0:
            print(dxlfx.getRxPacketError(dxlcx.PROTOCOL, dxl_error))
        print("Moving motor", motor, "to position", position)

    def init_arms(self):
        for i in range(0, 3):
            # P I D
            dxlfx.write2ByteTxOnly(self.port_num, dxlcx.PROTOCOL, dxlcx.R_ID[i], dxlcx.ADDR_POSITION_P_GAIN, dxlcx.PPG[i])
            dxlfx.write2ByteTxOnly(self.port_num, dxlcx.PROTOCOL, dxlcx.L_ID[i], dxlcx.ADDR_POSITION_P_GAIN, dxlcx.PPG[i])
            dxlfx.write2ByteTxOnly(self.port_num, dxlcx.PROTOCOL, dxlcx.R_ID[i], dxlcx.ADDR_POSITION_I_GAIN, dxlcx.PIG[i])
            dxlfx.write2ByteTxOnly(self.port_num, dxlcx.PROTOCOL, dxlcx.L_ID[i], dxlcx.ADDR_POSITION_I_GAIN, dxlcx.PIG[i])
            dxlfx.write2ByteTxOnly(self.port_num, dxlcx.PROTOCOL, dxlcx.R_ID[i], dxlcx.ADDR_POSITION_D_GAIN, dxlcx.PDG[i])
            dxlfx.write2ByteTxOnly(self.port_num, dxlcx.PROTOCOL, dxlcx.L_ID[i], dxlcx.ADDR_POSITION_D_GAIN, dxlcx.PDG[i])


    def moving(self):
        moving = dxlfx.read1ByteRx(self.port_num, dxlcx.PROTOCOL, dxlcx.R_ID[0], dxlcx.ADDR_MOVING)
        dxl_comm_result = dxlfx.getLastTxRxResult(self.port_num, dxlcx.PROTOCOL)
        return moving

    def model(self):
        dxl_model_number = dxlfx.pingGetModelNum(self.port_num, dxlcx.PROTOCOL, dxlcx.R_ID[0])
        # dxl_comm_result = dxlfx.getLastTxRxResult(self.port_num, dxlcx.PROTOCOL)
        # dxl_error = dxlfx.getLastRxPacketError(self.port_num, dxlcx.PROTOCOL)
        # if dxl_comm_result != dxlcx.COMM_SUCCESS:
        #     # print(dxlfx.getTxRxResult(dxlcx.PROTOCOL, dxl_comm_result))
        # elif dxl_error != 0:
        #     # print(dxlfx.getRxPacketError(dxlcx.PROTOCOL, dxl_error))
        # else:
            # print("[ID:%03d] ping Succeeded. Dynamixel model number : %d" % (dxlcx.R_ID[0], dxl_model_number))


if __name__ == "__main__":
    dxl = D2C()
    # print("Status = {}".format(x.get_status()))


# import os
# import ctypes
# import dynamixel_functions as dxlfx                    # Uses Dynamixel SDK library
# import dynamixel_constants as dxlcx

# define function for decoding characters, depending on OS
# if os.name == 'nt':
#     import msvcrt
#     def getch():
#         return msvcrt.getch().decode()
# else:
#     import sys, tty, termios
#     fd = sys.stdin.fileno()
#     old_settings = termios.tcgetattr(fd)
#     def getch():
#         try:
#             tty.setraw(sys.stdin.fileno())
#             ch = sys.stdin.read(1)
#         finally:
#             termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
#         return ch

# DXL1_ID                     = 11                             # Dynamixel ID: 1
# DXL2_ID                     = 12                             # Dynamixel ID: 2
#
# port_num = dxlfx.portHandler(dxlcx.DEVICENAME)
#
# # Initialize PacketHandler Structs
# dxlfx.packetHandler()
#
# # Initialize Groupsyncwrite instance
# groupwrite_num = dxlfx.groupSyncWrite(port_num, dxlcx.PROTOCOL_VERSION, dxlcx.ADDR_PRO_GOAL_POSITION, dxlcx.LEN_PRO_GOAL_POSITION)
#
# # Initialize Groupsyncread Structs for Present Position
# groupread_num = dxlfx.groupSyncRead(port_num, dxlcx.PROTOCOL_VERSION, dxlcx.ADDR_PRO_PRESENT_POSITION, dxlcx.LEN_PRO_PRESENT_POSITION)
#
# # initialize some stuff
# index = 0
# dxl_comm_result = dxlcx.COMM_TX_FAIL                              # Communication result
# dxl_addparam_result = 0                                     # AddParam result
# dxl_getdata_result = 0                                      # GetParam result
# dxl1_goal_position = [dxlcx.DXL1_MINIMUM_POSITION_VALUE, dxlcx.DXL1_MAXIMUM_POSITION_VALUE]         # Goal position
# dxl2_goal_position = [dxlcx.DXL2_MINIMUM_POSITION_VALUE, dxlcx.DXL2_MAXIMUM_POSITION_VALUE]         # Goal position
#
# dxl_error = 0                                               # Dynamixel error
# dxl1_present_position = 0                                   # Present position
# dxl2_present_position = 0
#
# # Open port
# if dxlfx.openPort(port_num):
#     print("Succeeded to open the port!")
# else:
#     print("Failed to open the port!")
#     print("Press any key to terminate...")
#     getch()
#     quit()
#
#
# # Set port baudrate
# if dxlfx.setBaudRate(port_num, dxlcx.BAUDRATE):
#     print("Succeeded to change the baudrate!")
# else:
#     print("Failed to change the baudrate!")
#     print("Press any key to terminate...")
#     getch()
#     quit()
#
#
# # Enable Dynamixel#1 Torque
# dxlfx.write1ByteTxRx(port_num, dxlcx.PROTOCOL_VERSION, DXL1_ID, dxlcx.ADDR_PRO_TORQUE_ENABLE, dxlcx.TORQUE_ENABLE)
# dxl_comm_result = dxlfx.getLastTxRxResult(port_num, dxlcx.PROTOCOL_VERSION)
# dxl_error = dxlfx.getLastRxPacketError(port_num, dxlcx.PROTOCOL_VERSION)
# if dxl_comm_result != dxlcx.COMM_SUCCESS:
#     print(dxlfx.getTxRxResult(dxlcx.PROTOCOL_VERSION, dxl_comm_result))
# elif dxl_error != 0:
#     print(dxlfx.getRxPacketError(dxlcx.PROTOCOL_VERSION, dxl_error))
# else:
#     print("Dynamixel#1 has been successfully connected")
#
# # Enable Dynamixel#2 Torque
# dxlfx.write1ByteTxRx(port_num, dxlcx.PROTOCOL_VERSION, DXL2_ID, dxlcx.ADDR_PRO_TORQUE_ENABLE, dxlcx.TORQUE_ENABLE)
# dxl_comm_result = dxlfx.getLastTxRxResult(port_num, dxlcx.PROTOCOL_VERSION)
# dxl_error = dxlfx.getLastRxPacketError(port_num, dxlcx.PROTOCOL_VERSION)
# if dxl_comm_result != dxlcx.COMM_SUCCESS:
#     print(dxlfx.getTxRxResult(dxlcx.PROTOCOL_VERSION, dxl_comm_result))
# elif dxl_error != 0:
#     print(dxlfx.getRxPacketError(dxlcx.PROTOCOL_VERSION, dxl_error))
# else:
#     print("Dynamixel#2 has been successfully connected")
#
# # Add parameter storage for Dynamixel#1 present position value
# dxl_addparam_result = ctypes.c_ubyte(dxlfx.groupSyncReadAddParam(groupread_num, DXL1_ID)).value
# if dxl_addparam_result != 1:
#     print("[ID:%03d] groupSyncRead addparam failed" % (DXL1_ID))
#     quit()
#
# # Add parameter storage for Dynamixel#2 present position value
# dxl_addparam_result = ctypes.c_ubyte(dxlfx.groupSyncReadAddParam(groupread_num, DXL2_ID)).value
# if dxl_addparam_result != 1:
#     print("[ID:%03d] groupSyncRead addparam failed" % (DXL2_ID))
#     quit()
#
#
# while 1:
#     print("Press any key to continue! (or press ESC to quit!)")
#     if getch() == chr(dxlcx.ESC_ASCII_VALUE):
#         break
#
#     # Add Dynamixel#1 goal position value to the Syncwrite storage
#     dxl_addparam_result = ctypes.c_ubyte(dxlfx.groupSyncWriteAddParam(groupwrite_num, DXL1_ID, dxl1_goal_position[index], dxlcx.LEN_PRO_GOAL_POSITION)).value
#     print(dxl_addparam_result)
#     if dxl_addparam_result != 1:
#         print("[ID:%03d] groupSyncWrite addparam failed" % (DXL1_ID))
#         quit()
#
#     # Add Dynamixel#2 goal position value to the Syncwrite parameter storage
#     dxl_addparam_result = ctypes.c_ubyte(dxlfx.groupSyncWriteAddParam(groupwrite_num, DXL2_ID, dxl2_goal_position[index], dxlcx.LEN_PRO_GOAL_POSITION)).value
#     if dxl_addparam_result != 1:
#         print("[ID:%03d] groupSyncWrite addparam failed" % (DXL2_ID))
#         quit()
#
#     # Syncwrite goal position
#     dxlfx.groupSyncWriteTxPacket(groupwrite_num)
#     dxl_comm_result = dxlfx.getLastTxRxResult(port_num, dxlcx.PROTOCOL_VERSION)
#     if dxl_comm_result != dxlcx.COMM_SUCCESS:
#         print(dxlfx.getTxRxResult(dxlcx.PROTOCOL_VERSION, dxl_comm_result))
#
#     # Clear syncwrite parameter storage
#     dxlfx.groupSyncWriteClearParam(groupwrite_num)
#
#     while 1:
#         # Syncread present position
#         dxlfx.groupSyncReadTxRxPacket(groupread_num)
#         dxl_comm_result = dxlfx.getLastTxRxResult(port_num, dxlcx.PROTOCOL_VERSION)
#         if dxl_comm_result != dxlcx.COMM_SUCCESS:
#             print(dxlfx.getTxRxResult(dxlcx.PROTOCOL_VERSION, dxl_comm_result))
#
#         # Check if groupsyncread data of Dynamixel#1 is available
#         dxl_getdata_result = ctypes.c_ubyte(dxlfx.groupSyncReadIsAvailable(groupread_num, DXL1_ID, dxlcx.ADDR_PRO_PRESENT_POSITION, dxlcx.LEN_PRO_PRESENT_POSITION)).value
#         if dxl_getdata_result != 1:
#             print("[ID:%03d] groupSyncRead getdata failed" % (DXL1_ID))
#             quit()
#
#         # Check if groupsyncread data of Dynamixel#2 is available
#         dxl_getdata_result = ctypes.c_ubyte(dxlfx.groupSyncReadIsAvailable(groupread_num, DXL2_ID, dxlcx.ADDR_PRO_PRESENT_POSITION, dxlcx.LEN_PRO_PRESENT_POSITION)).value
#         if dxl_getdata_result != 1:
#             print("[ID:%03d] groupSyncRead getdata failed" % (DXL2_ID))
#             quit()
#
#         # Get Dynamixel#1 present position value
#         dxl1_present_position = dxlfx.groupSyncReadGetData(groupread_num, DXL1_ID, dxlcx.ADDR_PRO_PRESENT_POSITION, dxlcx.LEN_PRO_PRESENT_POSITION)
#
#         # Get Dynamixel#2 present position value
#         dxl2_present_position = dxlfx.groupSyncReadGetData(groupread_num, DXL2_ID, dxlcx.ADDR_PRO_PRESENT_POSITION, dxlcx.LEN_PRO_PRESENT_POSITION)
#
#         print("[ID:%03d] GoalPos:%03d  PresPos:%03d\t[ID:%03d] GoalPos:%03d  PresPos:%03d" % (DXL1_ID, dxl1_goal_position[index], dxl1_present_position, DXL2_ID, dxl2_goal_position[index], dxl2_present_position))
#
#         if not ((abs(dxl1_goal_position[index] - dxl1_present_position) > dxlcx.DXL_MOVING_STATUS_THRESHOLD) or (abs(dxl2_goal_position[index] - dxl2_present_position) > dxlcx.DXL_MOVING_STATUS_THRESHOLD)):
#             break
#
#     # Change goal position
#     if index == 0:
#         index = 1
#     else:
#         index = 0
#
#
# # Disable Dynamixel#1 Torque
# dxlfx.write1ByteTxRx(port_num, dxlcx.PROTOCOL_VERSION, DXL1_ID, dxlcx.ADDR_PRO_TORQUE_ENABLE, dxlcx.TORQUE_DISABLE)
# dxl_comm_result = dxlfx.getLastTxRxResult(port_num, dxlcx.PROTOCOL_VERSION)
# dxl_error = dxlfx.getLastRxPacketError(port_num, dxlcx.PROTOCOL_VERSION)
# if dxl_comm_result != dxlcx.COMM_SUCCESS:
#     print(dxlfx.getTxRxResult(dxlcx.PROTOCOL_VERSION, dxl_comm_result))
# elif dxl_error != 0:
#     print(dxlfx.getRxPacketError(dxlcx.PROTOCOL_VERSION, dxl_error))
#
# # Disable Dynamixel#2 Torque
# dxlfx.write1ByteTxRx(port_num, dxlcx.PROTOCOL_VERSION, DXL2_ID, dxlcx.ADDR_PRO_TORQUE_ENABLE, dxlcx.TORQUE_DISABLE)
# dxl_comm_result = dxlfx.getLastTxRxResult(port_num, dxlcx.PROTOCOL_VERSION)
# dxl_error = dxlfx.getLastRxPacketError(port_num, dxlcx.PROTOCOL_VERSION)
# if dxl_comm_result != dxlcx.COMM_SUCCESS:
#     print(dxlfx.getTxRxResult(dxlcx.PROTOCOL_VERSION, dxl_comm_result))
# elif dxl_error != 0:
#     print(dxlfx.getRxPacketError(dxlcx.PROTOCOL_VERSION, dxl_error))
#
# # Close port
# dxlfx.closePort(port_num)
