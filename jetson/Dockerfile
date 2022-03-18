FROM nvcr.io/nvidia/l4t-base:r32.6.1

# prevent apt installs from asking us our favorite keyboard layout
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update
RUN apt-get -y upgrade

RUN apt-get -y install python3 python3-pip python3-venv curl

###
### install gstreamer 
###

# https://gstreamer.freedesktop.org/documentation/installing/on-linux.html?gi-language=c
RUN apt-get install -y libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-bad1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-doc gstreamer1.0-tools gstreamer1.0-x gstreamer1.0-alsa gstreamer1.0-gl gstreamer1.0-gtk3 gstreamer1.0-qt5 gstreamer1.0-pulseaudio

###
### RTSP stuff
###

# helpful links
# https://github.com/GStreamer/gst-rtsp-server/blob/master/examples/test-launch.c
# https://stackoverflow.com/a/68856708
# https://gist.github.com/Santiago-vdk/80c378a315722a1b813ae5da1661f890

# install rtsp server
RUN curl -O https://gstreamer.freedesktop.org/src/gst-rtsp/gst-rtsp-server-1.14.5.tar.xz
RUN tar -xf gst-rtsp-server-1.14.5.tar.xz
RUN cd gst-rtsp-server-1.14.5 && ./configure && make -j 8 install
RUN cp gst-rtsp-server-1.14.5/examples/.libs/test-launch /usr/local/bin/gst-rtsp-server
RUN rm -rf /gst-rtsp-server-1.14.5{,.tar.xz}

###
### Arduino stuff
###

RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh
RUN arduino-cli core install arduino:avr
RUN arduino-cli lib install firmata

###
### Python libraries
###
RUN apt-get install -y libcairo2-dev libgirepository1.0-dev #gobject-introspection
COPY requirements.txt /tmp/requirements.txt
#RUN apt-get install -y python-markupsafe
RUN pip3 install --upgrade pip
RUN pip3 install -r /tmp/requirements.txt && rm /tmp/requirements.txt