#include <Firmata.h>

#define PIN_RIGHT_PWM 6
#define PIN_RIGHT_FORWARD 4
#define PIN_RIGHT_BACKWARD 5

#define PIN_LEFT_PWM 9
#define PIN_LEFT_FORWARD 7
#define PIN_LEFT_BACKWARD 8

#define DIRECTION_STOP 0
#define DIRECTION_FORWARD 1
#define DIRECTION_BACKWARD 2

void sysexCallback(byte command, byte argc, byte *argv)
{
  // Ignore command. Expect 4 bytes:
  // Left direction (DIRECTION_* value)
  // Left speed
  // Right direction (DIRECTION_* value)
  // Right speed
  int iter = 0;
  int leftDir = argv[iter++];
  int leftSpeed = argv[iter++];
  int rightDir = argv[iter++];
  int rightSpeed = argv[iter++];

  analogWrite(PIN_LEFT_PWM, leftSpeed);
  digitalWrite(PIN_LEFT_FORWARD, leftDir == DIRECTION_FORWARD ? HIGH : LOW);
  digitalWrite(PIN_LEFT_BACKWARD, leftDir == DIRECTION_BACKWARD ? HIGH : LOW);

  analogWrite(PIN_RIGHT_PWM, rightSpeed);
  digitalWrite(PIN_RIGHT_FORWARD, rightDir == DIRECTION_FORWARD ? HIGH : LOW);
  digitalWrite(PIN_RIGHT_BACKWARD, rightDir == DIRECTION_BACKWARD ? HIGH : LOW);

  // flash the light so we know a message was receied
  digitalWrite(LED_BUILTIN, HIGH);
  delay(50);
  digitalWrite(LED_BUILTIN, LOW);
}

void setup()
{
  // Firmata setup
  Firmata.setFirmwareVersion(FIRMATA_FIRMWARE_MAJOR_VERSION, FIRMATA_FIRMWARE_MINOR_VERSION);
  Firmata.attach(START_SYSEX, sysexCallback);
  Firmata.begin(57600);
}

void loop()
{
  while (Firmata.available()) {
    Firmata.processInput();
  }
}
