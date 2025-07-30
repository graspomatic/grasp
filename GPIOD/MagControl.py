import gpiod
import asyncio
import MagConstants as magcx


class MAGS(object):
    def __init__(self):
        self.chip = gpiod.Chip(magcx.CHIP)

        # Define line settings for output
        self.config = gpiod.LineSettings()
        self.config.direction = gpiod.LineDirection.OUTPUT

        # Request left lines
        self.left_lines = self.chip.request_lines(
            consumer="mags",
            config=self.config,
            offsets=[magcx.LEFT_HOLD, magcx.LEFT_RELEASE]
        )

        # Request right lines
        self.right_lines = self.chip.request_lines(
            consumer="mags",
            config=self.config,
            offsets=[magcx.RIGHT_HOLD, magcx.RIGHT_RELEASE]
        )

    async def energize(self, side=-1):
        if side == 1:
            lines = self.right_lines
        elif side == 0:
            lines = self.left_lines
        else:
            print("Enter 0 (left) or 1 (right)")
            return

        lines.set_values([1, 0])  # energize

    async def deenergize(self, side=-1):
        if side == 1:
            lines = self.right_lines
        elif side == 0:
            lines = self.left_lines
        else:
            print("Enter 0 (left) or 1 (right)")
            return

        lines.set_values([0, 1])  # start release
        await asyncio.sleep(magcx.RELEASE_DUR)
        lines.set_values([0, 0])  # reset to idle
