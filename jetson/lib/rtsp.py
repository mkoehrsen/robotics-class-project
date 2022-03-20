# Forked from https://github.com/prabhakar-sivanesan/OpenCV-rtsp-server/blob/master/stream.py

import gi
import cv2
import argparse
import logging
import numpy as np
import time
import itertools
import threading

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

_logger = logging.getLogger(__name__)

GObject.threads_init()
Gst.init(None)

def append_intervideosink(pipeline, channel, sync=False):
    sync = {True: "true", False: "false"}[sync]
    return pipeline + " ! intervideosink channel={channel} sync={sync}".format(
        channel=channel,
        sync=sync
    )

def create_video_channel_writer(channel, pipeline, fps, size_wh):
    p = append_intervideosink(pipeline, channel)
    print("VC Writer pipeline", p)
    return cv2.VideoWriter(p, cv2.CAP_GSTREAMER, 0, fps, size_wh)

class RtspServer(object):

    encoder_pipeline = "nvvidconv ! nvv4l2h264enc bitrate={bitrate} ! video/x-h264 ! rtph264pay name=pay0"
    source_pipeline = "intervideosrc channel={channel}"

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
        
    def stop(self):
        self.loop.quit()
    
    def mount_pipeline(self, path, pipeline, bitrate=int(3e6), latency=500):
        pipeline += " ! " + self.encoder_pipeline.format(bitrate=bitrate)
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(pipeline)
        factory.set_latency(latency)
        factory.set_transport_mode(GstRtspServer.RTSPTransportMode.PLAY)
        print("Path", path, "mounting pipeline:", pipeline)
        self.mounts.add_factory(path, factory)
    
    def mount_channel(self, path, bitrate=int(3e6), latency=500):
        channel = next(self.channels)
        pipeline = self.source_pipeline.format(channel=channel)
        self.mount_pipeline(path, pipeline, bitrate=bitrate, latency=latency)
        return channel

svr = RtspServer(8998)
svr.start()

cam_in = "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=30/1 ! nvvidconv flip-method=0 ! video/x-raw, width=640, height=480, format=BGRx ! videoconvert ! video/x-raw, format=BGR ! appsink"
reader = cv2.VideoCapture(cam_in)
width = int(reader.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = reader.get(cv2.CAP_PROP_FPS)

red_writer = create_video_channel_writer(
    svr.mount_channel("/red"),
    "appsrc is-live=true ! videoconvert ! video/x-raw, format=BGRx",
    fps, (width, height))
    
blue_writer = create_video_channel_writer(
    svr.mount_channel("/blue"),
    "appsrc is-live=true ! videoconvert ! video/x-raw, format=BGRx",
    fps, (width, height))

while True:
    ret, frame = reader.read()
    assert ret, "Error reading video. Consider running: sudo service nvargus-daemon restart"
    blue_writer.write(frame * np.uint8([1,0,0]))
    red_writer.write(frame * np.uint8([0,0,1]))