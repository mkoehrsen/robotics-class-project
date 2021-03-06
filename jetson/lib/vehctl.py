import argparse
import enum
import itertools
import logging
import math
import os
import time
from pose import Pose2D, pose_from_wheel_distances
from simple_rpc import Interface
from types import SimpleNamespace

_logger = logging.getLogger(__name__)

CONFIGS = {
    "mkoehrsen": SimpleNamespace(
        vehicle=SimpleNamespace(
            wheelBase=7.8,
            wheelDiam=2.7,
            pwmMode=1,  # See constants in motor.h
            maximumSpeed=192,
            minimumSpeed=160,
            cameraOrientation=2,  # Invert 180, value passed to nvgstcapture
        ),
        leftMotor=SimpleNamespace(
            enablePin=9, forwardPin=7, reversePin=8, encoderPin=2
        ),
        rightMotor=SimpleNamespace(
            enablePin=6, forwardPin=4, reversePin=5, encoderPin=3
        ),
    ),
    "default": SimpleNamespace(
        vehicle=SimpleNamespace(
            wheelBase=5.25,
            wheelDiam=2.7,
            pwmMode=2,  # See constants in motor.h
            maximumSpeed=80,
            minimumSpeed=40,
            cameraOrientation=0,
        ),
        leftMotor=SimpleNamespace(
            enablePin=12, forwardPin=10, reversePin=11, encoderPin=18
        ),
        rightMotor=SimpleNamespace(
            enablePin=4, forwardPin=6, reversePin=5, encoderPin=19
        ),
    ),
}


class Direction(enum.Enum):
    STOP = 0
    FORWARD = 1
    REVERSE = 2
    LEFT = 3
    RIGHT = 4


class _DummyInterface:
    def __init__(self):
        self.last_dir = Direction.STOP

    def __getattr__(self, attrname):
        # TODO not really using this currently, needs updating
        pass
        # def log(*args):
        #     _logger.debug(
        #         f"_DummyVehicle: {attrname}({', '.join(str(x) for x in args)})"
        #     )

        #     result = (0, 0)
        #     if self.last_dir == "forward":
        #         result = (30, 30)
        #     elif self.last_dir == "reverse":
        #         result = (-30, -30)
        #     elif self.last_dir == "left":
        #         result = (-10, 10)
        #     elif self.last_dir == "right":
        #         result = (10, -10)

        #     self.last_dir = attrname
        #     return result

        # return log


class Vehicle:
    def __init__(self):
        self.config = CONFIGS.get(os.getenv("USER"), CONFIGS["default"])

        try:
            port = os.environ["ARDUINO_PORT"]
            _logger.debug(f"Found Arduino port: {port}")
            self.interface = Interface(port)
        except:
            _logger.warning("Can't connect to Arduino, vehicle will run in dummy mode.")
            self.interface = _DummyInterface()

        self.interface.configureVehicle(
            self.config.vehicle.pwmMode,
            self.config.vehicle.maximumSpeed,
            self.config.vehicle.minimumSpeed,
        )

        self.interface.configureLeftMotor(
            self.config.leftMotor.enablePin,
            self.config.leftMotor.forwardPin,
            self.config.leftMotor.reversePin,
            self.config.leftMotor.encoderPin,
        )

        self.interface.configureRightMotor(
            self.config.rightMotor.enablePin,
            self.config.rightMotor.forwardPin,
            self.config.rightMotor.reversePin,
            self.config.rightMotor.encoderPin,
        )

        self.pose_hist = [Pose2D()]

    @property
    def curr_pose(self):
        return self.pose_hist[-1]

    def _update_pos(self, left_transitions, right_transitions):
        left_dist = (
            left_transitions * self.config.vehicle.wheelDiam * math.pi * 2
        ) / 20
        right_dist = (
            right_transitions * self.config.vehicle.wheelDiam * math.pi * 2
        ) / 20

        self.pose_hist.append(
            self.curr_pose
            + pose_from_wheel_distances(
                left_dist, right_dist, self.config.vehicle.wheelBase
            )
        )

    def forward(self, speed):
        self._update_pos(*self.interface.forward(speed))

    def reverse(self, speed):
        self._update_pos(*self.interface.reverse(speed))

    def left(self, speed):
        self._update_pos(*self.interface.left(speed))

    def right(self, speed):
        self._update_pos(*self.interface.right(speed))

    def stop(self):
        self._update_pos(*self.interface.stop())

    def reset(self):
        self.interface.stop()
        self.pose_hist = [Pose2D()]

    def action_start(self, direction, transitions):
        self.interface.actionStart(direction.value, transitions)

    def action_status(self):
        return self.interface.actionStatus()

    def perform_action(self, direction, dist):
        config = self.config.vehicle

        if direction in (Direction.FORWARD, Direction.REVERSE):
            transitions_goal = (dist * 20) / (config.wheelDiam * math.pi)
        else:
            transitions_goal = ((dist * 20) / 360) * (
                config.wheelBase / config.wheelDiam
            )
        print(direction, dist, "transitions_goal:", transitions_goal)

        self.action_start(direction, transitions_goal)
        action_state = 1
        while action_state == 1:
            (
                action_state,
                left_transitions,
                left_speed,
                right_transitions,
                right_speed,
            ) = self.action_status()
            print(
                dict(
                    action_state=action_state,
                    left_transitions=left_transitions,
                    left_speed=left_speed,
                    right_transitions=right_transitions,
                    right_speed=right_speed,
                )
            )
            time.sleep(0.050)

        # Arbitrary wait in case of further coasting.
        time.sleep(0.025)
        (
            action_state,
            left_transitions,
            left_speed,
            right_transitions,
            right_speed,
        ) = self.action_status()
        print(
            dict(
                action_state=action_state,
                left_transitions=left_transitions,
                left_speed=left_speed,
                right_transitions=right_transitions,
                right_speed=right_speed,
            )
        )


def drive():
    direction_map = {
        "F": Direction.FORWARD,
        "B": Direction.REVERSE,  # "R" is used for RIGHT
        "L": Direction.LEFT,
        "R": Direction.RIGHT,
    }

    def instruction(instr_str):
        # An instruction on the command line is a string of the form:
        # <direction><dist>
        # direction is one of (F, B, L, R)
        # For (F, B) -- forwards, backwards -- the dist is in inches
        # For (L, R) -- left, right -- the dist is in degrees.
        # In the left/right case the vehicle pivots approximately in-place.
        # Distances are integers.
        dir = direction_map[instr_str[0]]
        return (dir, int(instr_str[1:]))

    parser = argparse.ArgumentParser()
    parser.add_argument("instructions", nargs="+", type=instruction)
    args = parser.parse_args()

    veh = Vehicle()

    for (dir, dist) in args.instructions:
        veh.perform_action(dir, dist)


if __name__ == "__main__":
    drive()
