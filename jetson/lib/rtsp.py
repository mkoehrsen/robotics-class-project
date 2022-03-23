# Forked from https://github.com/prabhakar-sivanesan/OpenCV-rtsp-server/blob/master/stream.py

"""
An RTSP server integrated with OpenCV.

Basic use:

server = RtspServer(8554)
writer = server.mount_writer("/my_stream", 24, (640,480))
"""

import gi
import cv2
import logging
import itertools
import threading

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

_logger = logging.getLogger(__name__)

GObject.threads_init()
Gst.init(None)

class RtspServer(object):

    encoder_pipeline = "nvvidconv ! nvv4l2h264enc bitrate={bitrate} ! video/x-h264 ! rtph264pay name=pay0"
    source_pipeline = "intervideosrc timeout={timeout} channel={channel}"

    def __init__(self, port):
        self.server = server = GstRtspServer.RTSPServer()
        self.mounts = server.get_mount_points()
        server.set_service(str(port))
        self.channels = itertools.count()
    
    def start(self):
        # using GObject.MainLoop() breaks KeyboardInterrupt - using GObject.MainLoop.new(...) instead
        self.loop = loop = GObject.MainLoop.new(None, False)
        self.server.attach(None)
        threading.Thread(target=loop.run, daemon=True).start()
        
#     def stop(self):
#         # TODO
#         print("I was asked to stop")
#         self.loop.quit()
#         for path in self.paths:
#             self.mounts.remove_factory(path)
#         print("My loop quit")
#         GObject.Source.remove(self.source_tag)
#         print("removed tag")
    
    def mount_pipeline(self, path, pipeline, bitrate=int(3e6)):
        pipeline += " ! " + self.encoder_pipeline.format(bitrate=bitrate)
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(pipeline)
        factory.set_transport_mode(GstRtspServer.RTSPTransportMode.PLAY)
        self.mounts.add_factory(path, factory)
    
    def mount_channel(self, path, bitrate=int(3e6), black_frame_timeout=60):
        channel = next(self.channels)
        pipeline = self.source_pipeline.format(channel=channel, timeout=black_frame_timeout * Gst.SECOND)
        self.mount_pipeline(path, pipeline, bitrate=bitrate)
        return channel
        
    def mount_writer(self, path, fps, size_wh,
            pipeline="appsrc is-live=true ! videoconvert ! video/x-raw, format=BGRx",
            bitrate=int(3e6),
            black_frame_timeout=60):
        """
        Convenience method to produce a cv2.VideoWriter bound to a streaming path.
        The default pipeline should be fine in the common case.
        """
        channel = self.mount_channel(path, bitrate=bitrate, black_frame_timeout=60)
        return create_video_channel_writer(channel, pipeline, fps, size_wh)

def create_video_channel_writer(channel, pipeline, fps, size_wh):
    """
    Produce a cv2.VideoWriter bound to a channel of the RTSP server.
    
    Example:
    channel = server.mount_channel("/file")
    pipeline = "appsrc is-live=true ! videoconvert ! video/x-raw, format=BGRx"
    writer = create_video_channel_writer(channel, pipeline, fps, size_wh)
    """
    p = append_intervideosink(pipeline, channel)
    return cv2.VideoWriter(p, cv2.CAP_GSTREAMER, 0, fps, size_wh)

def append_intervideosink(pipeline, channel, sync=False):
    """
    Add an intervideosink element to a pipeline in order to bind it to the RTSP server.
    
    Example:
    channel = server.mount_channel("/file")
    pipe = append_intervideosink("appsrc", channel)
    """
    sync = {True: "true", False: "false"}[sync]
    return pipeline + " ! intervideosink channel={channel} sync={sync}".format(
        channel=channel,
        sync=sync
    )

if __name__ == "__main__":
    import sys
    import time
    import datetime
    import numpy as np
    from collections import deque

    port, synthetic_processing_time = sys.argv[1:]
    synthetic_processing_time = float(synthetic_processing_time)
    
    server = RtspServer(int(port))
    server.start()
        
    camera_pipeline = """
        nvarguscamerasrc
        ! video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=30/1
        ! nvvidconv flip-method=0
        ! video/x-raw, width=640, height=480, format=BGRx
        ! videoconvert
        ! video/x-raw, format=BGR
        ! appsink drop=True max-buffers=1
    """
    camera = cv2.VideoCapture(camera_pipeline)

    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = camera.get(cv2.CAP_PROP_FPS)

    raw_writer = server.mount_writer("/raw", fps, (width, height))
    red_writer = server.mount_writer("/red", fps, (width, height))
    blue_writer = server.mount_writer("/blue", fps, (width, height))
    slow_writer = server.mount_writer("/slow", fps, (width, height))

    paths = ["raw", "red", "blue", "slow"]
    for path in paths:
        print("Server listening at rtsp://localhost:%s/%s" % (port, path))

    class BufEvent(threading.Event):
        def __init__(self):
            threading.Event.__init__(self)
            self.buf = deque(maxlen=1)
        def pop(self):
            self.wait()
            item = self.buf.pop()
            self.clear()
            return item
        def push(self, item):
            self.buf.append(item)
            self.set()

    def process_colors(buf_event):
        while True:
            frame = buf_event.pop()
            red_writer.write(frame * np.uint8([0,0,1]))
            blue_writer.write(frame * np.uint8([1,0,0]))
            
    def simulate_long_delay(buf_event):
        while True:
            frame = buf_event.pop()
            stamp = lambda: datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")
            before = stamp()
            time.sleep(2)
            after = stamp()
            for (text, pos) in [(before, (50,50)), (after, (50,200))]:
                cv2.putText(frame, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2, cv2.LINE_AA)
            slow_writer.write(frame)

    events = [BufEvent() for i in range(2)]
    
    threading.Thread(target=process_colors, args=[events[0]], daemon=True).start()
    threading.Thread(target=simulate_long_delay, args=[events[1]], daemon=True).start()
    
    while True:
        ret, frame = camera.read()
        assert ret, "Error reading video."
        time.sleep(synthetic_processing_time)
        raw_writer.write(frame)
        for event in events:
            event.push(np.copy(frame))