import contextlib
import cv2
import logging
import numpy as np
import threading

_logger = logging.getLogger(__name__)

MODE_IDLE=0
MODE_CALIBRATING=1
MODE_DRIVING=2

_current_mode=MODE_CALIBRATING
# @contextlib.contextmanager
# def apply_mode(mode):
#     global _current_mode
#     prev_mode = _current_mode
#     _current_mode=mode
#     yield _current_mode
#     _current_mode = prev_mode
    
def process_frame(frame_in):

    if _current_mode == MODE_CALIBRATING:
        return _calibrator.process(frame_in)
    elif _current_mode == MODE_DRIVING:
        return frame_in
    else:
        return frame_in

class Calibrator:
    def __init__(self):
        self.thread = None
        self.frame_in = None
        self.frame_out = None
    
    def process(self, frame_in):
        self.frame_in = frame_in
        if self.frame_out is None:
            self.frame_out = frame_in
        
        if self.thread is None:
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
        
        return self.frame_out
    
    def loop(self):
        while True:
            _logger.debug("Start processing frame")
            frame_in = self.frame_in
            ret, corners = cv2.findChessboardCorners(frame_in, (4, 3))
            frame_out = np.copy(frame_in)
            cv2.drawChessboardCorners(frame_out, (4,3), corners, ret)

            self.frame_out = frame_out
            _logger.debug("Done processing frame")

_calibrator = Calibrator()
