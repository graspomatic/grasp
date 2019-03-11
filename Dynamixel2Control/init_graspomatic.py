import AppliedMotionControl as AMC
x=AMC.AMC()
y=AMC.AMC(motor_ip="10.10.10.11", local_port=60648)

import Dynamixel2Control
dxl=Dynamixel2Control.D2C()

import MagControl
import asyncio
mags=MagControl.MAGS()