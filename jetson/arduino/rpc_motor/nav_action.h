#ifndef NAV_ACTION_H
#define NAV_ACTION_H

#include "motor.h"

// Action state constants
#define ST_IDLE 0
#define ST_ACTIVE 1
#define ST_TIMED_OUT 2
#define ST_INTERRUPTED 3
#define ST_SUCCEEDED 4

// Action type constants
#define ATYPE_STOP 0
#define ATYPE_FORWARD 1
#define ATYPE_REVERSE 2
#define ATYPE_LEFT 3
#define ATYPE_RIGHT 4

typedef struct {
    MotorControl *leftMotor;
    MotorControl *rightMotor;

    byte actionType = ATYPE_STOP;
    int transitionsGoal = 0;

    // These are configured in the vehicle config.
    short maximumSpeed = 0;
    short minimumSpeed = 0;

    short leftSpeed = 0;
    short rightSpeed = 0;

    // Last unsigned count that we saw from the motor controllers, so
    // we can tell when things changed.
    unsigned int leftTransitions = 0;
    unsigned int rightTransitions = 0;

    // Last time we saw a change, if this goes too long declare a timeout
    unsigned long lastUpdateTime;

    byte state = ST_IDLE;
} NavAction;

void start_action(NavAction *action, byte actionType, int transitionsGoal);
void update_action(NavAction *action);
void terminate_action(NavAction *action, byte state);

#endif
