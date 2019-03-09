import gpiod
import sys
import threading




with gpiod.Chip("gpiochip2") as chip:
    offsets = [0]
    values = [1]

    lines = chip.get_lines(offsets)
    lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
    vals = lines.set_values(values)

    print('set complete')

timer = threading.Timer(5.0, turnOff)
timer.start()



def turnOff():
    print("made it to turnoff")
    with gpiod.Chip("gpiochip2") as chip:
        offsets = [0]
        values = [0]
        lines = chip.get_lines(offsets)
        lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
        vals = lines.set_values(values)

        print('set complete')

        print('getting values')
        vals = lines.get_values()

        for val in vals:
            print(val, end=' ')
        print()
