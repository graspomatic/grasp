import gpiod
import sys
import asyncio

async def main():


    with gpiod.Chip("gpiochip2") as chip:
        offsets = [0]
        values = [1]

        lines = chip.get_lines(offsets)
        lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
        vals = lines.set_values(values)

        await asyncio.sleep(0.025)

        offsets = [0]
        values = [0]
        lines = chip.get_lines(offsets)
        vals = lines.set_values(values)
        vals = lines.get_values()

        for val in vals:
            print(val, end=' ')
        print()







