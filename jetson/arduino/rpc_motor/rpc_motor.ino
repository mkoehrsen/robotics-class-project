#include <simpleRPC.h>
#include "motor.h"

typedef struct {
  unsigned short wheelBase;   // Distance between wheels in mm
  unsigned short wheelCircum; // Circumference of each wheel in mm
  byte pwmMode;               // PWM_MODE_ENABLE or PWM_MODE_INPUT, defined in motor.h
} VehicleConfig;

// These structs must be configured through RPC calls
VehicleConfig vehicleConfig;
MotorControl leftControl;
MotorControl rightControl;

// These are internal state so they can be initialized here.
EncoderState leftState = { LOW, LOW, 0, 0 };
EncoderState rightState = { LOW, LOW, 0, 0 };

void setup() {
  Serial.begin(9600);
}

void loop() {
  interface(
    Serial,
    configureVehicle, F("configureVehicle: Set wheel base, circumference and pwm mode of vehicle."),
    configureLeftMotor, F("configureLeftMotor: Set control pins of left motor."),
    configureRightMotor, F("configureRightMotor: Set control pins of right motor."),
    forwardManual, F("forwardManual: Run motors forward."),
    reverseManual, F("reverseManual: Run motors in reverse."),
    rightManual, F("rightManual: Rotate to right."),
    leftManual, F("leftManual: Rotate to left."),
    stopManual, F("stopManual: Stop motors.")
  );
}

// RPC interface starts here
// Config functions
void configureVehicle(unsigned short wheelBase, unsigned short wheelCircum, byte pwmMode) {
  vehicleConfig.wheelBase = wheelBase;
  vehicleConfig.wheelCircum = wheelCircum;
  vehicleConfig.pwmMode = pwmMode;
}

void configureLeftMotor(byte enablePin, byte forwardPin, byte reversePin, byte encoderPin) {
  leftControl.enablePin = enablePin;
  leftControl.forwardPin = forwardPin;
  leftControl.reversePin = reversePin;
  leftControl.encoderPin = encoderPin;
}

void configureRightMotor(byte enablePin, byte forwardPin, byte reversePin, byte encoderPin) {
  rightControl.enablePin = enablePin;
  rightControl.forwardPin = forwardPin;
  rightControl.reversePin = reversePin;
  rightControl.encoderPin = encoderPin;
}

// Manual control functions
void forwardManual(byte speed) {
  run_motor(&leftControl, vehicleConfig.pwmMode, DIR_FORWARD, speed);
  run_motor(&rightControl, vehicleConfig.pwmMode, DIR_FORWARD, speed);
}

void reverseManual(byte speed) {
  run_motor(&leftControl, vehicleConfig.pwmMode, DIR_REVERSE, speed);
  run_motor(&rightControl, vehicleConfig.pwmMode, DIR_REVERSE, speed);
}

void leftManual(byte speed) {
  run_motor(&leftControl, vehicleConfig.pwmMode, DIR_REVERSE, speed);
  run_motor(&rightControl, vehicleConfig.pwmMode, DIR_FORWARD, speed);
}

void rightManual(byte speed) {
  run_motor(&leftControl, vehicleConfig.pwmMode, DIR_FORWARD, speed);
  run_motor(&rightControl, vehicleConfig.pwmMode, DIR_REVERSE, speed);
}

void stopManual() {
  run_motor(&leftControl, vehicleConfig.pwmMode, DIR_STOP, 0);
  run_motor(&rightControl, vehicleConfig.pwmMode, DIR_STOP, 0);
}
