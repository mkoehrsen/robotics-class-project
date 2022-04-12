import logging
import math
import os
from simple_rpc import Interface
from types import SimpleNamespace

_logger = logging.getLogger(__name__)

CONFIGS = {
    'mkoehrsen': SimpleNamespace(
        vehicle = SimpleNamespace(
            wheelBase=100, # TODO
            wheelCircum = int(68*math.pi),
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
            wheelCircum = int(68*math.pi),
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

class _DummyVehicle:
    def __getattr__(self, attrname):
        def log(*args):
            _logger.debug(f"_DummyVehicle: {attrname}({', '.join(str(x) for x in args)})")
        return log

def init_vehicle():

    try:
        port = os.environ["ARDUINO_PORT"]
        _logger.debug(f"Found Arduino port: {port}")
        vehicle = Interface(port)
    except:
        _logger.warning("Can't connect to Arduino, vehicle will run in dummy mode.")
        vehicle=_DummyVehicle()

    config = CONFIGS.get(os.getenv('USER'), CONFIGS['default'])

    vehicle.configureVehicle(
        config.vehicle.wheelBase,
        config.vehicle.wheelCircum,
        config.vehicle.pwmMode,
    )

    vehicle.configureLeftMotor(
        config.leftMotor.enablePin,
        config.leftMotor.forwardPin,
        config.leftMotor.reversePin,
        config.leftMotor.encoderPin
    )

    vehicle.configureRightMotor(
        config.rightMotor.enablePin,
        config.rightMotor.forwardPin,
        config.rightMotor.reversePin,
        config.rightMotor.encoderPin
    )

    return vehicle
    
