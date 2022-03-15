# Prerequisites (one-time install):
#   arduino-cli core install arduino:avr
#   arduino-cli lib install firmata
#
# jq is used to extract the device name from arduino-cli output:
#   sudo apt-get install -y jq
#
# You need permission to open the arduino port (log out and back in after running this):
#   sudo usermod -a -G dialout $USER


compile: 
	cd arduino/firmata_motor_nano; arduino-cli compile -b arduino:avr:nano

install: 
	cd arduino/firmata_motor_nano; arduino-cli compile -b arduino:avr:nano -u \
		-p `arduino-cli board list --format json | jq -r '.[0].port.address'`

run:
	pip3 install -r requirements.txt
	flask run --host 0.0.0.0 --port 8080
