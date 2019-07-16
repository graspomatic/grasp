import socket
import time
from struct import pack


class AMC(object):

    def __init__(self, motor_ip="10.10.10.10", motor_port=7775, local_port=60649, belt='standard'):
        self.bound_buff = 2  # distance from hardware limits to software limits in mm
        self.motor_ip = motor_ip
        self.motor_port = motor_port
        self.local_port = local_port
        if belt == 'standard':
            self.mmscale = 303.03
        elif belt == 'steel':
            self.mmscale = 285.71
        else:
            print('specify belt=standard or steel')

        print("UDP target IP:", self.motor_ip)
        print("UDP target port:", self.motor_port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.local_port))
        self.sock.settimeout(0.01)

        rv = []

        while len(rv) == 0:
            self.read_udp_all()
            rv = self.get_revision()
            print("Waiting for connection...")
            time.sleep(1)

        print("connected")
        self.read_udp_all()  # clear any messages

    def get_revision(self):
        # motor revision number
        self.send_command("RV")
        return self.read_udp_once()

    def get_status(self):
        # Typically returns PR: in position and ready
        # when moving returns MR: moving and ready
        # HMR: when homing
        # APR: Alarm, probably at one of the bounds
        # in transition from mr to pr, sometimes just R

        # time.sleep(0.01)        #without this, sometimes i would miss something in read-udp-all
        self.read_udp_all()     # clear out the read buffer first
        self.send_command("RS")
        resp = self.read_udp_once()

        if len(resp) > 2 and resp[3] == 'A':  # if we have an alarm, go check on that
            print(self.get_alarm())

        return resp

    def get_alarm(self):
        #alarm 0002 is CCW limit
        #alarm 0004 is CW limit

        self.read_udp_all()  # clear out the read buffer first
        self.send_command("AL")
        return self.read_udp_once()

    def get_position(self):
        # get current position
        self.read_udp_all()             # clear buffer first
        # self.send_command("EP")         # request position
        self.send_command("IP")  # request position
        position = self.read_udp_once()  # get response
        while len(position) == 0:
            print('didnt receive a position from the motor! trying again...')
            self.read_udp_all()  # clear buffer
            time.sleep(0.003)
            self.send_command("IP")  # request position
            time.sleep(0.003)
            position = self.read_udp_once()  # get response
        return int(position[3:len(position)])

    def move_distance_count(self, distance, accel=25.0, decel=25.0, vel=3.0):
        # move specified distance in counts. positive is clockwise
        cmds = ['AC' + str(accel),      # units rev/s/s
                'DE' + str(decel),      # units rev/s/s
                'VE' + str(vel),        # units rev/s
                'FL' + str(distance)]

        self.send_command(cmds)
        self.wait_for_stop()

    def move_distance_mm(self, distance, accel=25.0, decel=25.0, vel=3.0):
        # move specified distance in counts. positive is clockwise
        distance = self.mm_to_count(distance)

        cmds = ['AC' + str(accel),  # units rev/s/s
                'DE' + str(decel),  # units rev/s/s
                'VE' + str(vel),  # units rev/s
                'FL' + str(distance)]

        self.send_command(cmds)
        self.wait_for_stop()

    def move_location(self, location, accel=25.0, vel=3.0):
        # move to a location based on distance from CW bound in mm

        #first make sure that CW and CCW bounds have been set
        if not self.check_bounds():
            print("bounds not set!")
            return

        #get cw bound
        self.read_udp_all()
        self.send_command('LP') #cw bound
        time.sleep(0.01) 
        cw_bound = self.read_udp_once()
        cw_bound = int(cw_bound[3:len(cw_bound)])

        self.send_command('LM')  # ccw bound
        time.sleep(0.01) 
        ccw_bound = self.read_udp_once()
        ccw_bound = int(ccw_bound[3:len(ccw_bound)])

        target = cw_bound - self.mm_to_count(location) + self.mm_to_count(self.bound_buff)

        if target > cw_bound or target < ccw_bound:
            print("out of bounds!")
            return

        cmds = ['AC' + str(accel),  # units rev/s/s
                'DE' + str(accel),  # units rev/s/s
                'VE' + str(vel),    # units rev/s
                'FP' + str(target)]

        self.send_command(cmds)
        return target
        #self.wait_for_stop()


    def wait_for_stop(self):
        # constantly reads status until the first returned character isn't an H or M
        # in other words, loops until the thing stops moving
        self.read_udp_all()
        a = self.get_status()
        print(a)
        while a[3] == 'M' or a[3] == 'H':
            print("Movin'")
            a = self.get_status()
            while len(a) == 0:
                a = self.get_status()
                print("Empty!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")


        print("Done!")

    def find_bound(self, direction, current=0.8):
        # finds requested hard bound and sets the software limit accordingly
        if direction == 1:      # clockwise
            dval = "HO200"      # home offset, this decides which direction we seek
            limit = "LP"        # label for clockwise bound
            buf = -self.bound_buff        # distance to move once bound is reached
        elif direction == 0:    # counter clockwise
            dval = "HO-200"
            limit = "LM"
            buf = self.bound_buff
        else:
            print('direction must be 0 or 1')
            return

        curPar = 'HC' + str(current)

        # parameters for finding cw or ccw bound
        cmds = ['HA1100', 'HL1100', 'HA2100', 'HL2100', 'HA3100',
                'HL3100', 'HV15', 'HV25', 'HV35', curPar, dval, 'HS0']

        self.send_command(limit + str(0))  # set current position to software limit
        self.send_command(cmds)             # start moving towards bound
        self.wait_for_stop()                # wait until it stops
        self.move_distance_mm(buf, vel=0.2)    # move away from bound 1000 units
        self.wait_for_stop()                # wait until it stops
        pos = self.get_position()           # get that position
        self.send_command(limit + str(pos))  # set current position to software limit

    def check_bounds(self):
        self.read_udp_all()
        self.send_command('LM')
        time.sleep(0.003)
        first = self.read_udp_once()
        self.send_command('LP')
        time.sleep(0.003)
        second = self.read_udp_once()

        ok = 1

        if first[3] == '0':
            print('CCW limit not set!')
            ok = 0
        if second[3] == '0':
            print('CW limit not set!')
            ok = 0
        return ok

    def send_command(self, message):
        # can take either single command in string or multiple commands in list of strings
        if not type(message) is str:
            message = '\r'.join(message)
        # add prefix and suffix
        c = pack("BB", 0, 7) + bytes(message, "utf-8") + pack("B", 13)
        if not self.sock.sendto(c, (self.motor_ip, self.motor_port)):
            return 0
        else:
            return 1

    def read_udp_all(self):
        # grabs any and all packets available
        total_data = []
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                total_data.append(data)
            except:
                break
        return total_data

    def read_udp_once(self):
        # tries to grab one packet
        try:
            data, addr = self.sock.recvfrom(1024)
            data = data.decode()
            return data[2:len(data) - 1]
        except:
            return ''

    def mm_to_count(self, mm):
        # TSM34IP-3DG is 20000 counts per rotation i think
        # vertical (steel-reinforced belt) is 70 mm per revolution
        # horizontal (neoprene belt) is 66 mm per revolution

        #scale = 303.03  # horizontal counts per mm
        #scale = 285.71  # vertical counts per mm
        return round(mm * self.mmscale)


# if __name__ == "__main__":
#     x = AMC()
#     print("Status = {}".format(x.get_status()))
