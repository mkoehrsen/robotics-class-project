import argparse
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
            wheelBase=194.0 * .0394, # measured in mm, converted to inches
            wheelDiam=69.0 * .0394, # ditto
            pwmMode=1,  # See constants in motor.h
        ),
        leftMotor=SimpleNamespace(
            # enablePin=9, forwardPin=7, reversePin=8, encoderPin=2
            enablePin=9, forwardPin=5, reversePin=4, encoderPin=2
        ),
        rightMotor=SimpleNamespace(
            # enablePin=6, forwardPin=4, reversePin=5, encoderPin=3
            enablePin=6, forwardPin=8, reversePin=7, encoderPin=3
        ),
    ),
    # Jared TODO -- update below
    "default": SimpleNamespace(
        vehicle=SimpleNamespace(
            wheelBase=100 * .0394,  # TODO
            wheelDiam=69.0 * .0394,
            pwmMode=1,  # See constants in motor.h
        ),
        leftMotor=SimpleNamespace(
            enablePin=9, forwardPin=7, reversePin=8, encoderPin=2
        ),
        rightMotor=SimpleNamespace(
            enablePin=6, forwardPin=4, reversePin=5, encoderPin=3
        ),
    ),
}


class _DummyInterface:
    def __init__(self):
        self.last_dir = "stop"

    def __getattr__(self, attrname):
        def log(*args):
            _logger.debug(
                f"_DummyVehicle: {attrname}({', '.join(str(x) for x in args)})"
            )

            result = (0, 0)
            if self.last_dir == "forward":
                result = (30, 30)
            elif self.last_dir == "reverse":
                result = (-30, -30)
            elif self.last_dir == "left":
                result = (-10, 10)
            elif self.last_dir == "right":
                result = (10, -10)

            self.last_dir = attrname
            return result

        return log


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

    def action_start(self, direction, transitions):
        self.interface.actionStart(direction, transitions)
    
    def action_status(self):
        return self.interface.actionStatus()

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

def drive():
    def instruction(instr_str):
        # An instruction on the command line is a string of the form:
        # <direction><dist>
        # direction is one of (F, B, L, R)
        # For (F, B) -- forwards, backwards -- the dist is in inches
        # For (L, R) -- left, right -- the dist is in degrees.
        # In the left/right case the vehicle pivots approximately in-place.
        # Distances are integers.
        dir = instr_str[0]
        if dir not in ('F', 'B', 'L', 'R'):
            raise ValueError
        return (dir, int(instr_str[1:]))

    parser = argparse.ArgumentParser()
    parser.add_argument("instructions", nargs="+", type=instruction)
    args = parser.parse_args()

    veh = Vehicle()
    config = veh.config.vehicle

    for (dir, dist) in args.instructions:

        if dir in ('F', 'B'):
            transitionsGoal = (dist*20)/(config.wheelDiam*math.pi)
        else:
            transitionsGoal =  ((dist*20)/360)*(config.wheelBase/config.wheelDiam)
        
        print(dir, dist, "transitionsGoal:", transitionsGoal)

        dir_const = {
            'F': 1,
            'B': 2,
            'L': 3,
            'R': 4
        }[dir]

        veh.action_start(dir_const, int(transitionsGoal))
        action_state = 1
        while action_state == 1:
            action_state, left_transitions, left_speed, right_transitions, right_speed = veh.action_status()
            print(dict(
                action_state = action_state,
                left_transitions = left_transitions,
                left_speed = left_speed,
                right_transitions = right_transitions,
                right_speed = right_speed
            ))
            time.sleep(.010)
        
        # Arbitrary wait in case of further coasting.
        time.sleep(.025)
        action_state, left_transitions, left_speed, right_transitions, right_speed = veh.action_status()
        print(dict(
            action_state = action_state,
            left_transitions = left_transitions,
            left_speed = left_speed,
            right_transitions = right_transitions,
            right_speed = right_speed
        ))



if __name__ == '__main__':
    drive()