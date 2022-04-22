#include <simpleRPC.h>
#include "motor.h"

byte PWM_MODE = PWM_MODE_ENABLE; // or PWM_MODE_INPUT, defined in motor.h

// Initialized using configureLeftMotor/configureRightMotor
MotorControl leftControl;
MotorControl rightControl;

// RPC interface starts here

// Config functions
void configureVehicle(byte pwmMode) {
  PWM_MODE = pwmMode;
}

void configureLeftMotor(byte enablePin, byte forwardPin, byte reversePin, byte encoderPin) {
  leftControl = {
    enablePin,
    forwardPin,
    reversePin,
    encoderPin,
    DIR_STOP,
    LOW,
    LOW,
    0,
    0
  };
}

void configureRightMotor(byte enablePin, byte forwardPin, byte reversePin, byte encoderPin) {
  rightControl = {
    enablePin,
    forwardPin,
    reversePin,
    encoderPin,
    DIR_STOP,
    LOW,
    LOW,
    0,
    0
  };
}

// Control functions -- these each return transition counts
// since the last change in control.
Object<int, int> forward(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, PWM_MODE, DIR_FORWARD, speed);
  run_motor(&rightControl, PWM_MODE, DIR_FORWARD, speed);
  return result;
}

Object<int, int> reverse(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, PWM_MODE, DIR_REVERSE, speed);
  run_motor(&rightControl, PWM_MODE, DIR_REVERSE, speed);
  return result;
}

Object<int, int> left(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, PWM_MODE, DIR_REVERSE, speed);
  run_motor(&rightControl, PWM_MODE, DIR_FORWARD, speed);
  return result;
}

Object<int, int> right(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, PWM_MODE, DIR_FORWARD, speed);
  run_motor(&rightControl, PWM_MODE, DIR_REVERSE, speed);
  return result;
}

Object<int, int> stop() {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, PWM_MODE, DIR_STOP, 0);
  run_motor(&rightControl, PWM_MODE, DIR_STOP, 0);
  return result;
}

// Main functions
void setup() {
  Serial.begin(9600);
}

void loop() {
  // As far as I can tell interface() is a non-blocking call which will return
  // immediately if there's no serial input. So we just interleave calls to it
  // with other logic we want to do.
  interface(
    Serial,
    configureVehicle, F("configureVehicle: Set wheel base, circumference and pwm mode of vehicle."),
    configureLeftMotor, F("configureLeftMotor: Set control pins of left motor."),
    configureRightMotor, F("configureRightMotor: Set control pins of right motor."),
    forward, F("forward: Run motors forward."),
    reverse, F("reverse: Run motors in reverse."),
    right, F("right: Rotate to right."),
    left, F("left: Rotate to left."),
    stop, F("stop: Stop motors.")
  );

  // Update encoder state every time. This should only be a few clock cycles per pass.
  update_encoder_state(&leftControl, digitalRead(leftControl.encoderPin));
  update_encoder_state(&rightControl, digitalRead(rightControl.encoderPin));
}

