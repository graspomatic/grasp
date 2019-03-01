import os
import dynamixel_sdk as dxlfx                    # Uses Dynamixel SDK library
import dynamixel_constants as dxlcx


portHandler = dxlfx.PortHandler(dxlcx.DEVICENAME)
packetHandler = dxlfx.PacketHandler(dxlcx.PROTOCOL)

# Open port
if portHandler.openPort():
    print("Succeeded to open the port")
else:
    print("Failed to open the port")

# Set port baudrate
if portHandler.setBaudRate(dxlcx.BAUDRATE):
    print("Succeeded to change the baudrate")
else:
    print("Failed to change the baudrate")

dxl_model_number, dxl_comm_result, dxl_error = packetHandler.ping(portHandler, dxlcx.R_ID[0])

if dxl_comm_result != dxlcx.COMM_SUCCESS:
    print("%s" % packetHandler.getTxRxResult(dxl_comm_result))
elif dxl_error != 0:
    print("%s" % packetHandler.getRxPacketError(dxl_error))
else:
    print("[ID:%03d] ping Succeeded. Dynamixel model number : %d" % (dxlcx.R_ID[0], dxl_model_number))

# Close port
portHandler.closePort()
