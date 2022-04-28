// motor.h and motor.cpp are formally C++ but I'm using something more 
// like ADT style in plain C for now so I don't have to go look up C++
// syntax. Might convert later.

#ifndef MOTOR_H
#define MOTOR_H

// PWM modes. It's unclear where PWM should be applied so allow both approaches.
// PWM_MODE_ENABLE means apply it to the enable pin (Mike style).
// PWM_MODE_INPUT means apply it to the forward/reverse input pin (Jared style).
#define PWM_MODE_ENABLE 1
#define PWM_MODE_INPUT 2

// Motor directions used in run_motor()
#define DIR_STOP 0
#define DIR_FORWARD 1
#define DIR_REVERSE 2

// Number of consistent reads from encoder before we believe it
#define ENCODER_MIN_COUNT 5

// Pin configuration and state of a motor/encoder pair. 
typedef struct {
  // These are one-time configuration, passed from jetson at startup
  byte enablePin;
  byte forwardPin;
  byte reversePin;
  byte encoderPin;

  // Remaining attributes are used to interpret encoder readings

  // Last direction sent to motor. Needed because we can't observe 
  // rotation direction from the encoders.
  byte lastDirection;

  // stablePinState is the state in which we have last seen the encoder pin
  // ENCODER_MIN_COUNT times consecutively.
  byte stablePinState;

  // lastPinState is the state which we most recently observed.
  // It could be transient so we count the observations with pinStateCount.
  byte lastPinState;

  // number of times we've observed lastPinState sequentially
  unsigned short pinStateCount;

  // Count of low-to-high transitions we've seen since last reset.
  // This is a signed value, i.e. if the direction is reverse then this
  // will be negative.
  int transitionCount;

} MotorControl;

// Initialize pins associated with a MotorConfig.
void setup_motor_pins(MotorControl *ctl);

// Set direction and speed of a motor.
// 0 for either direction or speed will stop.
void run_motor(MotorControl* ctl, byte pwmMode, byte direction, byte speed);

// Update encoder state based on a single observation of the encoder pin.
void update_encoder_state(MotorControl *ctl, byte pinState);

// Set transition count back to zero and return previous (signed) transition count.
int reset_transitions(MotorControl *ctl);

#endif
