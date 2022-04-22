import logging
import math
import os
from pose import Pose2D, pose_from_wheel_distances
from simple_rpc import Interface
from types import SimpleNamespace

_logger = logging.getLogger(__name__)

CONFIGS = {
    'mkoehrsen': SimpleNamespace(
        vehicle = SimpleNamespace(
            # Dimensions are in mm
            wheelBase = 194.0,
            wheelDiam = 69.0,
            pwmMode = 1 # See constants in motor.h
        ),
        leftMotor = SimpleNamespace(
            enablePin=9,
            forwardPin=7,
            reversePin=8,
            encoderPin=2
        ),
        rightMotor = SimpleNamespace(
            enablePin=6,
            forwardPin=4,
            reversePin=5,
            encoderPin=3
        )
    ), 
    # Jared TODO -- update below
    'default': SimpleNamespace(
        vehicle = SimpleNamespace(
            wheelBase=100, # TODO
            wheelCircum = 69.0,
            pwmMode = 1 # See constants in motor.h
        ),
        leftMotor = SimpleNamespace(
            enablePin=9,
            forwardPin=7,
            reversePin=8,
            encoderPin=2
        ),
        rightMotor = SimpleNamespace(
            enablePin=6,
            forwardPin=4,
            reversePin=5,
            encoderPin=3
        )
    ), 
}

class _DummyInterface:
    def __init__(self):
        self.last_dir = 'stop'

    def __getattr__(self, attrname):
        def log(*args):
            _logger.debug(f"_DummyVehicle: {attrname}({', '.join(str(x) for x in args)})")

            result = (0, 0)
            if self.last_dir == 'forward':
                result = (30, 30)
            elif self.last_dir == 'reverse':
                result = (-30, -30)
            elif self.last_dir == 'left':
                result = (-10, 10)
            elif self.last_dir == 'right':
                result = (10, -10)
            
            self.last_dir = attrname
            return result
            
        return log

class Vehicle:
    def __init__(self):
        self.config=CONFIGS.get(os.getenv('USER'), CONFIGS['default'])

        try:
            port = os.environ["ARDUINO_PORT"]
            _logger.debug(f"Found Arduino port: {port}")
            self.interface = Interface(port)
        except:
            _logger.warning("Can't connect to Arduino, vehicle will run in dummy mode.")
            self.interface=_DummyInterface()

        self.interface.configureVehicle(
            self.config.vehicle.pwmMode,
        )

        self.interface.configureLeftMotor(
            self.config.leftMotor.enablePin,
            self.config.leftMotor.forwardPin,
            self.config.leftMotor.reversePin,
            self.config.leftMotor.encoderPin
        )

        self.interface.configureRightMotor(
            self.config.rightMotor.enablePin,
            self.config.rightMotor.forwardPin,
            self.config.rightMotor.reversePin,
            self.config.rightMotor.encoderPin
        )

        self.pose_hist = [Pose2D()]
    
    @property
    def curr_pose(self):
        return self.pose_hist[-1]

    def _update_pos(self, left_transitions, right_transitions):
        left_dist = (left_transitions * self.config.vehicle.wheelDiam * math.pi * 2)/20
        right_dist = (right_transitions * self.config.vehicle.wheelDiam * math.pi * 2)/20

        self.pose_hist.append(self.curr_pose + pose_from_wheel_distances(left_dist, right_dist, self.config.vehicle.wheelBase))

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
