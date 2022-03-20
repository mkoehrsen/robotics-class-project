# Forked from https://github.com/prabhakar-sivanesan/OpenCV-rtsp-server/blob/master/stream.py

import gi
import cv2
import argparse
import logging
import numpy as np
import time

from vision import process_frame

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

_logger = logging.getLogger(__name__)

DEFAULT_PORT=8554
DEFAULT_PATH="/video_stream"

# Sensor Factory class which inherits the GstRtspServer base class and add
# properties to it.
class SensorFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, **properties):
        super(SensorFactory, self).__init__(**properties)

        camera_pipeline = 'nvarguscamerasrc ! video/x-raw(memory:NVMM),width=640, height=480, ' \
                          'format=NV12, framerate=30/1 ! nvvidconv flip-method=0 ! ' \
                          'video/x-raw, width=640, height=480, format=BGRx ! videoconvert ! ' \
                          'video/x-raw, format=BGR ! appsink'

        self.cap = cv2.VideoCapture(camera_pipeline)
        self.number_frames = 0
        self.fps = 30
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        self.launch_string = 'appsrc name=source is-live=true block=true format=GST_FORMAT_TIME ' \
                             'caps=video/x-raw,format=BGR,width=640,height=960,framerate={}/1 ' \
                             '! videoconvert ! video/x-raw,format=I420 ' \
                             '! x264enc speed-preset=ultrafast tune=zerolatency ' \
                             '! rtph264pay config-interval=1 name=pay0 pt=96' \
                             .format(self.fps)

    # method to capture the video feed from the camera and push it to the
    # streaming buffer.
    def on_need_data(self, src, length):
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = np.concatenate([frame, process_frame(frame)], 0)
                data = frame.tostring()
                buf = Gst.Buffer.new_allocate(None, len(data), None)
                buf.fill(0, data)
                buf.duration = self.duration
                timestamp = self.number_frames * self.duration
                buf.pts = buf.dts = int(timestamp)
                buf.offset = timestamp
                self.number_frames += 1
                retval = src.emit('push-buffer', buf)
                _logger.debug('pushed buffer, frame {}, duration {} ns, durations {} s'.format(self.number_frames,
                                                                                       self.duration,
                                                                                       self.duration / Gst.SECOND))
                # time.sleep(self.duration / Gst.SECOND)
                if retval != Gst.FlowReturn.OK:
                    print(retval)
    # attach the launch string to the override method
    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)
    
    # attaching the source element to the rtsp media
    def do_configure(self, rtsp_media):
        self.number_frames = 0
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)

# Rtsp server implementation where we attach the factory sensor with the stream uri
class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, **properties):
        super(GstServer, self).__init__(**properties)
        self.factory = SensorFactory()
        self.factory.set_shared(True)
        self.set_service(str(DEFAULT_PORT))
        self.get_mount_points().add_factory(DEFAULT_PATH, self.factory)
        self.attach(None)

# Entry point for running the rtsp server.
# This should be on its own thread.
def run_server():
    GObject.threads_init()
    Gst.init(None)
    server = GstServer()
    loop = GObject.MainLoop()
    loop.run()
