import gpiod
import sys


with gpiod.Chip("gpiochip2") as chip:
    offsets = 0
    values = 1


    lines = chip.get_lines(offsets)
    lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
    vals = lines.set_values(values)
