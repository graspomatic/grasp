import gpiod
import asyncio
import MagConstants as magcx


class MAGS(object):
    def __init__(self):
        self.chip = gpiod.Chip(magcx.CHIP)
        left_offsets = [magcx.LEFT_HOLD, magcx.LEFT_RELEASE]
        right_offsets = [magcx.RIGHT_HOLD, magcx.RIGHT_RELEASE]
        self.left_lines = self.chip.get_lines(left_offsets)
        self.right_lines = self.chip.get_lines(right_offsets)
        self.left_lines.request(consumer="", type=gpiod.LINE_REQ_DIR_OUT)
        self.right_lines.request(consumer="", type=gpiod.LINE_REQ_DIR_OUT)


    async def energize(self, side=-1):
        with gpiod.Chip(magcx.CHIP) as chip:
            if side == 1:
                lines = self.right_lines
            elif side == 0:
                lines = self.left_lines
            else:
                print("Enter 0 (left) or 1 (right)")
                return

            lines.set_values([1, 0])

            # vals = lines.get_values()
            #
            # for val in vals:
            #     print(val, end=' ')
            # print()

    async def deenergize(self, side=-1):
        with gpiod.Chip(magcx.CHIP) as chip:
            if side == 1:
                lines = self.right_lines
            elif side == 0:
                lines = self.left_lines
            else:
                print("Enter 0 (left) or 1 (right)")
                return

            lines.set_values([0, 1])

            await asyncio.sleep(magcx.RELEASE_DUR - 0.001)  # subtract one ms for processing time
            lines.set_values([0, 0])
            # vals = lines.get_values()
            #
            # for val in vals:
            #     print(val, end=' ')
            # print()
