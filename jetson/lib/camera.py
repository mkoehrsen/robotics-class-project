import cv2

CAMERA_PIPELINE = 'nvarguscamerasrc ! video/x-raw(memory:NVMM),width=640, height=480, ' \
                    'format=NV12, framerate=30/1 ! nvvidconv flip-method=0 ! ' \
                    'video/x-raw, width=640, height=480, format=BGRx ! videoconvert ! ' \
                    'video/x-raw, format=BGR ! appsink'

_video_capture = None
def read_frame():
    global _video_capture
    if _video_capture is None:
        _video_capture = cv2.VideoCapture(CAMERA_PIPELINE)
    
    return _video_capture.read()[1]
