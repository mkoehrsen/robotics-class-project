# Forked from https://github.com/prabhakar-sivanesan/OpenCV-rtsp-server/blob/master/stream.py

import gi
import cv2
import argparse
import logging
import numpy as np
import time

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

_logger = logging.getLogger(__name__)

DEFAULT_PORT=8554
DEFAULT_PATH="/video_stream"

class VideoWriter(object):

    def __init__(self, frame_size_wh):
        self.width, self.height = frame_size_wh
        self.num_frames_written = 0
        self.frame = np.zeros((self.height, self.width, 3))
        # todo init frame to black?

    def write(self, frame):
        self.frame = frame
        self.num_frames_written += 1

class VideoFactory(GstRtspServer.RTSPMediaFactory):

    def __init__(self, writer, fps):
        super(VideoFactory, self).__init__()
        self.writer = writer
        self.num_frames_emitted = 0
        self.fps = fps
        self.duration = 1 / self.fps * Gst.SECOND  # duration of a frame in nanoseconds
        self.launch_string = """
            appsrc name=source is-live=true block=true format=GST_FORMAT_TIME
            caps=video/x-raw,format=BGR,width={width},height={height},framerate={fps}/1
            ! videoconvert ! video/x-raw,format=I420
            ! x264enc speed-preset=ultrafast tune=zerolatency
            ! rtph264pay config-interval=1 name=pay0 pt=96
        """.format(
             # coercing for security - gst injection attacks?
             fps=float(self.fps),
             width=int(writer.width),
             height=int(writer.height)
         )
         
    # attach the launch string to the override method
    def do_create_element(self, url):
        return Gst.parse_launch(self.launch_string)
    
    # attaching the source element to the rtsp media
    def do_configure(self, rtsp_media):
        appsrc = rtsp_media.get_element().get_child_by_name('source')
        appsrc.connect('need-data', self.on_need_data)
        
    def on_need_data(self, gst_src, length):
        frame = self.writer.frame
        data = frame.tostring()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        buf.duration = self.duration
        timestamp = self.num_frames_emitted * self.duration
        buf.pts = buf.dts = int(timestamp)
        buf.offset = timestamp
        self.num_frames_emitted += 1
        retval = gst_src.emit('push-buffer', buf)
        print("pushed buf")
        if retval != Gst.FlowReturn.OK:
            print(retval)

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
                             'caps=video/x-raw,format=BGR,width=640,height=480,framerate={}/1 ' \
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

class RTSPServer(GstRtspServer.RTSPServer):
    def __init__(self, port, **properties):
        super(RTSPServer, self).__init__(**properties)
        self.set_service(str(port))
        self.attach(None)
    def serve(self, writer, fps, path):
        f = VideoFactory(writer, fps)
        f.set_shared(False)
        self.get_mount_points().add_factory(path, f)

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
# def run_server():
#     GObject.threads_init()
#     Gst.init(None)
#     server = GstServer()
#     loop = GObject.MainLoop()
#     loop.run()
# def run_server():
#     GObject.threads_init()
#     Gst.init(None)
#     server = RTSPServer(DEFAULT_PORT)
# #    w = VideoWriter((640,480))
# #    server.serve(w, 30, DEFAULT_PATH)
#     w = cv2.VideoWriter('appsrc ! videoconvert' + \
#     ' ! x264enc speed-preset=ultrafast bitrate=600' + \
#     ' ! rtspclientsink location=rtsp://localhost:8554/video_stream',
#     cv2.CAP_GSTREAMER, 0, 25, (640, 480), True)
#     loop = GObject.MainLoop()
#     loop.run()

import threading

# this doc helps
# https://lazka.github.io/pgi-docs/GstRtspServer-1.0/classes/RTSPMediaFactory.html#GstRtspServer.RTSPMediaFactory

def run_server():
    # imitating https://github.com/GStreamer/gst-rtsp-server/blob/master/examples/test-record.c
    GObject.threads_init()
    Gst.init(None)
    server = GstRtspServer.RTSPServer()
    server.set_service(str(DEFAULT_PORT))
    mounts = server.get_mount_points()
    factory = GstRtspServer.RTSPMediaFactory()
    factory.set_launch("intervideosrc name=s1 ! videoconvert ! video/x-raw, format=BGRx ! nvvidconv ! nvv4l2h264enc bitrate=8000000 ! video/x-h264 ! rtph264pay name=pay0") # decodebin name=depay0 ! 
    factory.set_latency(2000)
    factory.set_transport_mode(GstRtspServer.RTSPTransportMode.PLAY)
    mounts.add_factory(DEFAULT_PATH, factory)
    server.attach(None)
    loop = GObject.MainLoop()
    print("got loop")
    loop.run()

threading.Thread(target=run_server, daemon=True).start()

#https://github.com/aler9/rtsp-simple-server#from-opencv
"""
    appsrc
    ! video/x-raw, format=BGR
    ! queue
    ! videoconvert
    ! video/x-raw, format=BGRx, width=640, height=480, framerate=25/1
    ! nvvidconv
    ! intervideosink name=s1
"""

# and this guy's helpful
# https://forums.developer.nvidia.com/t/gstreamer-pipeline-replacements-for-hardware-accelerated-encoding-with-the-same-pipeline-output/142296/2

p = """
    appsrc is-live=true
    ! videoconvert
    ! video/x-raw, format=BGRx
    ! nvvidconv
    ! nvv4l2h264enc
    ! video/x-h264, profile=constrained-baseline, stream-format=byte-stream
    ! intervideosink
"""

p = "appsrc is-live=true ! intervideosink sync=false name=s1"
w = cv2.VideoWriter(p, cv2.CAP_GSTREAMER, 0, 25, (640, 480), True)

#'appsrc ! videoconvert' + \
#    ' ! nvv4l2h264enc'
#    ' ! x264enc speed-preset=ultrafast bitrate=6000' + \
#    ' ! mpegtsmux' + \
#    ' ! rtspclientsink location=rtsp://localhost:8554/video_stream',
#    '! intervideosink name=s1',
#    cv2.CAP_GSTREAMER, 0, 25, (640, 480), True)

cam_in = "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=30/1 ! nvvidconv flip-method=0 ! video/x-raw, width=640, height=480, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink"
reader = cv2.VideoCapture(cam_in)

det = cv2.BRISK_create()
while True:
    ret, frame = reader.read()
    assert ret, "Frame is %s" % frame
    kp, des = det.detectAndCompute(frame, None)
    #kp = []
    for k in kp:
        pt = tuple(int(round(x)) for x in k.pt)
        cv2.circle(frame, pt, 5, color=(0,0,255), thickness=2)
    print("writing...")
    w.write(frame)
#    w.write(np.zeros((640,480,3), np.uint8))
#    time.sleep(0.1)