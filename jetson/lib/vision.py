import cv2
import logging
import numpy as np

_logger = logging.getLogger(__name__)

MODE_IDLE=0
MODE_CALIBRATING=1
MODE_DRIVING=2

_current_mode=MODE_CALIBRATING

def process_frame(frame_in):
    if _current_mode == MODE_CALIBRATING:
        # frame_in = cv2.cvtColor(frame_in, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(frame_in, (6, 4))
        frame_out = np.copy(frame_in)
        cv2.drawChessboardCorners(frame_out, (6,4), corners, ret)
        _logger.debug("Found corners?" + str(ret))
        return frame_out
    elif _current_mode == MODE_DRIVING:
        return frame_in
    else:
        return frame_in