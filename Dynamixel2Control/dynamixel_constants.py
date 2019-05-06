BAUDRATE        = 1000000

# DEVICENAME      = "COM6".encode('utf-8')    # Check which port is being used on your controller
# DEVICENAME      = "COM6"    # Check which port is being used on your controller
DEVICENAME = '/dev/ttyUSB0'   # Check which port is being used on your controller
PROTOCOL = 2                  # See which protocol version is used in the Dynamixel

# Control table addresses for dynamixel x
ADDR_OPERATING_MODE     = 11        # operating mode, writeable only when torque disabled
ADDR_MOVING_THRESH      = 24        # 4 bytes, writeable only when torque disabled
ADDR_PWM_LIMIT          = 36        # 2 bytes, writeable only when torque disabled
ADDR_CURRENT_LIMIT      = 38        # 2 bytes, writeable only when torque disabled
ADDR_ACCELERATION_LIMIT = 40        # 4 bytes, writeable only when torque disabled
ADDR_VELOCITY_LIMIT     = 44        # 4 bytes, writeable only when torque disabled
ADDR_MAX_POSITION       = 48        # 4 bytes, writeable only when torque disabled, must be >= min
ADDR_MIN_POSITION       = 52        # 4 bytes, writeable only when torque disabled
ADDR_TORQUE_ENABLE      = 64        # 1 byte
ADDR_HARDWARE_ERROR     = 70        # 1 byte
ADDR_POSITION_D_GAIN    = 80        # 2 bytes
ADDR_POSITION_I_GAIN    = 82        # 2 bytes
ADDR_POSITION_P_GAIN    = 84        # 2 bytes
ADDR_GOAL_PWM           = 100       # 2 bytes
ADDR_GOAL_VELOCITY      = 104       # 4 bytes
ADDR_PROFILE_ACCEL      = 108       # 4 bytes
ADDR_PROFILE_VEL        = 112       # 4 bytes
ADDR_GOAL_POSITION      = 116       # 4 bytes
ADDR_MOVING             = 122       # 1 byte
ADDR_MOVING_STATUS      = 123       # 1 byte
ADDR_PRESENT_POSITION   = 132       # 4 bytes

COMM_SUCCESS = 0                             # Communication Success result value
COMM_TX_FAIL = -1001                         # Communication Tx Failed

# motor ids
IDs = [[11, 12, 13],                # left
       [21, 22, 23]]                # right

# threshold for considering movement complete
threshs = [[2, 2, 2],
           [2, 2, 2]]

# power to be used for movement, also how hard to resist pushing by subject
moving_pwms = [[580, 880, 300],
               [580, 880, 300]]

# top speed
profile_vels = [[400, 0, 0],
                [400, 0, 0]]

# top accel for slow movement
profile_accels_low = [[150, 0, 0],
                      [150, 0, 0]]

profile_accels_high = [[400, 0, 0],
                       [400, 0, 0]]

# position of all motors when in the 'pick' arm position
# 2044 to 2024
#1980 to 2010
#1027 to 1017
pick_pos = [[2064, 3264, 2024],
            [1510, 1022, 2010]]


