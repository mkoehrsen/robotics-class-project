#include <simpleRPC.h>
#include "motor.h"
#include "nav_action.h"

byte PWM_MODE = PWM_MODE_ENABLE; // or PWM_MODE_INPUT, defined in motor.h

// Initialized using configureLeftMotor/configureRightMotor
MotorControl leftControl;
MotorControl rightControl;

// Single NavAction instance is used as needed.
NavAction navAction;

// RPC interface starts here

// Config functions
void configureVehicle(byte pwmMode, byte maxSpeed, byte minSpeed) {
  PWM_MODE = pwmMode;
  navAction.maximumSpeed = maxSpeed;
  navAction.minimumSpeed = minSpeed;
}

void configureLeftMotor(byte enablePin, byte forwardPin, byte reversePin, byte encoderPin) {
  leftControl = {
    enablePin,
    forwardPin,
    reversePin,
    encoderPin,
    PWM_MODE,
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
    PWM_MODE,
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
  run_motor(&leftControl, speed);
  run_motor(&rightControl, speed);
  return result;
}

Object<int, int> reverse(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, -speed);
  run_motor(&rightControl, -speed);
  return result;
}

Object<int, int> left(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, -speed);
  run_motor(&rightControl, speed);
  return result;
}

Object<int, int> right(byte speed) {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, speed);
  run_motor(&rightControl, -speed);
  return result;
}

Object<int, int> stop() {
  Object<int, int> result(reset_transitions(&leftControl), reset_transitions(&rightControl));
  run_motor(&leftControl, 0);
  run_motor(&rightControl, 0);
  return result;
}

void actionStart(byte actionType, int transitions) {
  navAction.leftMotor = &leftControl;
  navAction.rightMotor = &rightControl;
  start_action(&navAction, actionType, transitions);
}

Object<int, int, int, int, int>actionStatus() {
  Object<int, int, int, int, int>
    result(navAction.state, 
           navAction.leftTransitions, navAction.leftSpeed, 
           navAction.rightTransitions, navAction.rightSpeed);
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
    stop, F("stop: Stop motors."),
    actionStart, F("actionStart: Start an action that will run to completion."),
    actionStatus, F("actionStatus: Check action status.")
  );

  // Update encoder state every time. This should only be a few clock cycles per pass.
  update_encoder_state(&leftControl, digitalRead(leftControl.encoderPin));
  update_encoder_state(&rightControl, digitalRead(rightControl.encoderPin));
  update_action(&navAction);
}

