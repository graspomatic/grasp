import gpiod
import asyncio
import MagConstants as magcx
from gpiod.line import Direction, Value


class MAGS:
    def __init__(self):
        # Open the chip
        self.chip = gpiod.Chip(magcx.CHIP)

        # Remember offsets for left/right
        self.left_offsets = [magcx.LEFT_HOLD, magcx.LEFT_RELEASE]
        self.right_offsets = [magcx.RIGHT_HOLD, magcx.RIGHT_RELEASE]

        # Build a LineSettings object for output
        settings = gpiod.LineSettings(direction=Direction.OUTPUT)

        # Request the left lines with those settings
        self.left_lines = self.chip.request_lines(
            config={off: settings for off in self.left_offsets},
            consumer="mags"
        )

        # Request the right lines with the same settings
        self.right_lines = self.chip.request_lines(
            config={off: settings for off in self.right_offsets},
            consumer="mags"
        )

    async def energize(self, side: int = -1):
        if side == 1:
            lines = self.right_lines
            offs = self.right_offsets
        elif side == 0:
            lines = self.left_lines
            offs = self.left_offsets
        else:
            print("Enter 0 (left) or 1 (right)")
            return

        # Turn ON the “hold” line, OFF the “release” line
        lines.set_values({
            offs[0]: Value.ACTIVE,
            offs[1]: Value.INACTIVE
        })

    async def deenergize(self, side: int = -1):
        if side == 1:
            lines = self.right_lines
            offs = self.right_offsets
        elif side == 0:
            lines = self.left_lines
            offs = self.left_offsets
        else:
            print("Enter 0 (left) or 1 (right)")
            return

        # Activate release, wait, then reset both low
        lines.set_values({
            offs[0]: Value.INACTIVE,
            offs[1]: Value.ACTIVE
        })
        await asyncio.sleep(magcx.RELEASE_DUR)
        lines.set_values({
            offs[0]: Value.INACTIVE,
            offs[1]: Value.INACTIVE
        })
