import gpiod
import sys
import asyncio
import MagConstants as magcx


class MAGS(object):
    async def disable(self):
        with gpiod.Chip(magcx.CHIP) as chip:
            if side == 'right':
                offsets = [magcx.RIGHT_HOLD, magcx.RIGHT_RELEASE]
            elif side == 'left':
                offsets = [magcx.LEFT_HOLD, magcx.LEFT_RELEASE]
            else:
                print("enter left or right")
                return

            lines = chip.get_lines(offsets)
            lines.request(consumer="gpioset", type=gpiod.LINE_REQ_DIR_OUT)
            lines.set_values([0, 1])

            await asyncio.sleep(0.029)

            lines.set_values([0, 0])
            vals = lines.get_values()

            for val in vals:
                print(val, end=' ')
            print()



if __name__ == "__main__":
    mags = MAGS()
