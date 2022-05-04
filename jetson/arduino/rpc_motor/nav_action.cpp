#include "nav_action.h"
#include "Arduino.h"

// Timeout in milliseconds -- if nothing happens with the encoders for this
// long then something is wrong.
#define TIMEOUT_INTERVAL 500

int leftSign(byte actionType) {
    if (actionType == ATYPE_FORWARD || actionType == ATYPE_RIGHT) return 1;
    else return -1;
}

int rightSign(byte actionType) {
    if (actionType == ATYPE_FORWARD || actionType == ATYPE_LEFT) return 1;
    else return -1;
}

void start_action(NavAction *action, byte actionType, int transitionsGoal) {
    if (action->state == ST_ACTIVE) {
        terminate_action(action, ST_INTERRUPTED);
    }

    reset_transitions(action->leftMotor);
    reset_transitions(action->rightMotor);

    action->actionType = actionType;
    action->transitionsGoal = transitionsGoal;

    action->leftTransitions = 0;
    action->rightTransitions = 0;

    // Speeds are unsigned, we apply sign when sent to the motor
    action->leftSpeed = 128;
    action->rightSpeed = 128;

    action->state = ST_ACTIVE;
    action->lastUpdateTime = millis();

    run_motor(action->leftMotor, action->leftSpeed * leftSign(action->actionType));
    run_motor(action->rightMotor, action->rightSpeed * rightSign(action->actionType));
}

void update_action(NavAction *action) {

    if (action->state != ST_ACTIVE) {
        return;
    }

    int leftTransitions = action->leftMotor->transitionCount;
    int rightTransitions = action->rightMotor->transitionCount;

    if (leftTransitions == action->leftTransitions && rightTransitions == action->rightTransitions) {
        if (millis() > action->lastUpdateTime + TIMEOUT_INTERVAL) {
            terminate_action(action, ST_TIMED_OUT);
        }
        return;
    }

    if (leftTransitions + rightTransitions >= action->transitionsGoal*2) {
        terminate_action(action, ST_SUCCEEDED);
        return;
    }

    action->lastUpdateTime = millis();
    action->leftTransitions = leftTransitions;
    action->rightTransitions = rightTransitions;

    if (leftTransitions != rightTransitions) {
        short newLeftSpeed = action->leftSpeed - ((leftTransitions-rightTransitions) * 5);
        short newRightSpeed = action->rightSpeed + ((leftTransitions-rightTransitions) * 5);

        action->leftSpeed = max(0, min(255,newLeftSpeed));
        action->rightSpeed = max(0, min(255,newRightSpeed));

        run_motor(action->leftMotor, action->leftSpeed * leftSign(action->actionType));
        run_motor(action->rightMotor, action->rightSpeed * rightSign(action->actionType));
    }

}

void terminate_action(NavAction *action, byte state) {
    action->state=state;

    run_motor(action->leftMotor, 0);
    run_motor(action->rightMotor, 0);
}
