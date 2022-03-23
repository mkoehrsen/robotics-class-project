# Prerequisites (one-time install):
#   arduino-cli core install arduino:avr
#   arduino-cli lib install firmata
#
# jq is used to extract the device name from arduino-cli output:
#   sudo apt-get install -y jq
#
# You need permission to open the arduino port (log out and back in after running this):
#   sudo usermod -a -G dialout $USER
#
# Install other requirements:
#   pip3 install -r requirements.txt
#
# I had some trouble with virtualenv and the system python so I stopped using it.

ifeq ($(ARDUINO_BOARD),)
  $(error ARDUINO_BOARD is not set. Examples: arduino:avr:nano, arduino:avr:nano:cpu=atmega328old)
endif

# sometimes bogus ports show up in the list, so we have to select a good one
# since this is now a fiddly process, let's reuse it for webapp so there aren't two flavors
# this command is deferred until the variable is first needed
ARDUINO_PORT = $(eval ARDUINO_PORT := $$(shell \
	arduino-cli board list --format json | jq -r 'map(.port | select(.properties) | .address)[0]' \
	))$(ARDUINO_PORT)

compile:
	arduino-cli compile arduino/firmata_motor_nano -b "$(ARDUINO_BOARD)"

install: compile
	arduino-cli upload arduino/firmata_motor_nano -b "$(ARDUINO_BOARD)" -p "$(ARDUINO_PORT)"

run:
	FLASK_APP=webapp.main \
	PYTHONPATH="$PYTHONPATH:$(PWD)/lib" \
	ARDUINO_PORT="$(ARDUINO_PORT)" \
	flask run --host 0.0.0.0 --port 8080

.PHONY: compile install run
