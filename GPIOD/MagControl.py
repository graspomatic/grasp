import gpiod
import asyncio
import MagConstants as magcx


class MAGS(object):
    def enable(self, side=-1):
        with gpiod.Chip(magcx.CHIP) as chip:
            if side == 'right':
                offsets = [magcx.RIGHT_HOLD, magcx.RIGHT_RELEASE]
            elif side == 'left':
                offsets = [magcx.LEFT_HOLD, magcx.LEFT_RELEASE]
            else:
                print("enter left or right")
                return

            lines = chip.get_lines(offsets)
            lines.request(consumer="", type=gpiod.LINE_REQ_DIR_OUT)
            lines.set_values([1, 0])

            vals = lines.get_values()

            for val in vals:
                print(val, end=' ')
            print()

    async def disable(self, side=-1):
        with gpiod.Chip(magcx.CHIP) as chip:
            if side == 'right':
                offsets = [magcx.RIGHT_HOLD, magcx.RIGHT_RELEASE]
            elif side == 'left':
                offsets = [magcx.LEFT_HOLD, magcx.LEFT_RELEASE]
            else:
                print("enter left or right")
                return

            lines = chip.get_lines(offsets)
            lines.request(consumer="", type=gpiod.LINE_REQ_DIR_OUT)
            lines.set_values([0, 1])

            await asyncio.sleep(magcx.RELEASE_DUR - 0.001)  # subtract one ms for processing time
            lines.set_values([0, 0])
            vals = lines.get_values()

            for val in vals:
                print(val, end=' ')
            print()
