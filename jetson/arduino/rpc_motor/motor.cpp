#include "Arduino.h"
#include "motor.h"

void setup_motor_pins(MotorControl *ctl) {
  // Depending on pwmMode some of these pins are used
  // with analogWrite() instead of digitalWrite() so 
  // we don't need to set them as outputs -- but it 
  // shouldn't hurt either.
  pinMode(ctl->forwardPin, OUTPUT);
  pinMode(ctl->reversePin, OUTPUT);
  pinMode(ctl->enablePin, OUTPUT);

  pinMode(ctl->encoderPin, INPUT);
}

void run_motor(MotorControl* ctl, short requestedSpeed) {

  byte speed;
  byte direction;

  if (requestedSpeed > 0) {
    direction=DIR_FORWARD;
    speed = (byte)max(requestedSpeed, 255);
  } else if (requestedSpeed < 0) {
    direction=DIR_REVERSE;
    speed = (byte)max(-requestedSpeed, 255);
  } else {
    direction=DIR_STOP;
    speed = 0;
  }

  if (speed == 0) {
    digitalWrite(ctl->reversePin, LOW);
    digitalWrite(ctl->forwardPin, LOW);
  } else if (ctl->pwmMode == PWM_MODE_ENABLE) {
    analogWrite(ctl->enablePin, speed);
    if (direction == DIR_FORWARD) {
      digitalWrite(ctl->reversePin, LOW);
      digitalWrite(ctl->forwardPin, HIGH);
    } else {
      digitalWrite(ctl->forwardPin, LOW);
      digitalWrite(ctl->reversePin, HIGH);
    }
  } else {
    digitalWrite(ctl->enablePin, HIGH);
    if (direction == DIR_FORWARD) {
      analogWrite(ctl->reversePin, speed);
      digitalWrite(ctl->forwardPin, HIGH);
    } else {
      digitalWrite(ctl->forwardPin, LOW);
      analogWrite(ctl->reversePin, speed);
    }
  }
}

void update_encoder_state(MotorControl* ctl, byte pinState) {
  if (pinState != ctl->lastPinState) {
    ctl->lastPinState = pinState;
    ctl->pinStateCount = 0;
  } else {
    ctl->pinStateCount++;
  }

  if (ctl->pinStateCount >= ENCODER_MIN_COUNT && pinState != ctl->stablePinState) {
    ctl->stablePinState = pinState;
    if (pinState == HIGH) {
      // Count rising edges
      ctl->transitionCount++;
    }
  }
}

int reset_transitions(MotorControl *ctl) {
  int result = ctl->transitionCount;
  ctl->transitionCount = 0;
  return result;
}
