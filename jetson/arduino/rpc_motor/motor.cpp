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

void run_motor(MotorControl* ctl, byte pwmMode, byte direction, byte speed) {
  if ((direction != DIR_FORWARD && direction != DIR_REVERSE) || speed == 0) {
    digitalWrite(ctl->reversePin, LOW);
    digitalWrite(ctl->forwardPin, LOW);
  } else if (pwmMode == PWM_MODE_ENABLE) {
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

void update_encoder_state(EncoderState *st, byte pinState) {
  if (pinState != st->lastPinState) {
    st->lastPinState = pinState;
    st->pinStateCount = 0;
  } else {
    st->pinStateCount++;
  }

  if (st->pinStateCount >= ENCODER_MIN_COUNT && pinState != st->stablePinState) {
    st->stablePinState = pinState;
    if (pinState == HIGH) {
      // Count rising edges
      st->transitionCount++;
    }
  }

}
