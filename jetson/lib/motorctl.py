import os
import json
import logging
import pyfirmata
import subprocess

# Same constants are defined in Arduino code.
DIRECTION_STOP = 0
DIRECTION_FORWARD = 1
DIRECTION_BACKWARD = 2

_logger = logging.getLogger(__name__)


class MotorCtl(object):
    def __init__(self):
        try:
            port = os.environ["ARDUINO_PORT"]
            _logger.debug(f"Found Arduino port: {port}")
            self.board = pyfirmata.Arduino(port)
        except:
            _logger.warning(
                "Can't connect to Arduino, MotorCtl will run in dummy mode.",
                exc_info=True,
            )
            self.board = None

    def set_speeds(self, left, right):
        """
        Sets speed and direction of left and right motors.
        Each value should be in the range [-1.0, 1.0], where
        negative values indicate to run the corresponding
        motor backwards.
        """

        def direction(val):
            return (
                DIRECTION_FORWARD
                if val > 0
                else DIRECTION_BACKWARD
                if val < 0
                else DIRECTION_STOP
            )

        def speed(val):
            return min(255, int(abs(val) * 255))

        sysex_args = [direction(left), speed(left), direction(right), speed(right)]
        _logger.debug(f"send_sysex(0, {sysex_args})")
        if self.board is not None:
            self.board.send_sysex(0, sysex_args)
