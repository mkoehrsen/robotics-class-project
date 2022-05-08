import os

import cv2

STANDARD_CAMERA_STREAM = """
    nvarguscamerasrc
    ! video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=30/1
    ! nvvidconv flip-method={orientation}
    ! video/x-raw, width=640, height=480, format=BGRx
    ! videoconvert
    ! video/x-raw, format=BGR
    ! appsink drop=True max-buffers=1
"""


def capture_image(tmpdir, orientation):
    """
    Run capture a single image and return it as a numpy array.
    Currently slow.
    """
    subprocess.run(
        [
            "nvgstcapture",
            "-m",
            "1",
            f"--orientation={orientation}",
            "-A",
            "--capture-auto=1",
            "--file-name",
            tmpdir + "/",
        ],
        check=True,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
    )
    image_file = sorted(
        [fn for fn in os.listdir(tmpdir) if fn.endswith(".jpg")],
        key=lambda fn: os.stat(os.path.join(tmpdir, fn)).st_ctime,
    )[-1]
    return cv2.cvtColor(cv2.imread(os.path.join(tmpdir, image_file)), cv2.COLOR_BGR2RGB)
    

class FrameSession(object):

    def __init__(self, orientation, save=None):
        self.orientation = orientation
        self.reader = cv2.VideoCapture(
            STANDARD_CAMERA_STREAM.format(orientation=self.orientation)
        )
        self.save = save
        self.frame_number = 1

    def __next__(self):
        ret, frame = self.reader.read()
        assert ret, "Did not capture a frame from the video stream."
        if self.save:
            fn = os.path.join(self.save, "image_{:05d}.png".format(self.frame_number))
            cv2.imwrite(fn, frame)
        self.frame_number += 1
        return frame

    def close(self):
        self.reader.release()