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

compile:
	cd arduino/firmata_motor_nano; arduino-cli compile -b "$(ARDUINO_BOARD)"

install:
	cd arduino/firmata_motor_nano; arduino-cli compile -b "$(ARDUINO_BOARD)" -u \
		-p `arduino-cli board list --format json | jq -r '.[0].port.address'`

run:
	flask run --host 0.0.0.0 --port 8080

.PHONY: compile install run
