import gpiod
import sys
import threading

def turnOff():
    with gpiod.Chip("gpiochip2") as chip:
        offsets = [0]
        values = [0]
        lines = chip.get_lines(offsets)
        lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
        vals = lines.set_values(values)

        vals = lines.get_values()

        for val in vals:
            print(val, end=' ')
        print()



with gpiod.Chip("gpiochip2") as chip:
    offsets = [0]
    values = [1]

    lines = chip.get_lines(offsets)
    lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
    timer = threading.Timer(0.025, turnOff)
    vals = lines.set_values(values)
    timer.start()






