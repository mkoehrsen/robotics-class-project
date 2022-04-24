import argparse
import cv2
import dt_apriltags
import enum
import logging
import numpy as np
import os
import subprocess
import tempfile

"""
Calibration protocol:

- Center the front wheels of the vehicle on the center line of the positioning panel.
- Align the tag panel with the positioning panel in the chosen orientation, and
  measure distance in inches from the top line of the positioning panel to the bottom line of
  the tag panel. This is the panel_dist to give to CalibrationSession.
- Create a CalibrationSession with appropriate orientation and with the measured panel distance, and
  invoke calibrate(). Unless no tags are detected at all the calibration session will 
"""


def flatten_rects(rects):
    """
    Convert a list of rects into a list of corners.
    """
    return sum(rects, [])


def get_tag_rects_world(panel_dist):
    # Distance from the vehicle origin to the bottom framing
    # line of the positioning panel
    baseline_dist = 11.0 + panel_dist

    # Empirically, apriltags returns corners in the order
    # (lower left, lower right, upper right, upper left)
    # relative to the upright position of the tag
    # Use a coordinate frame where the center line is y=0,
    # positive x is to the right, negative x is to the left.
    centers = [
        (0.0, baseline_dist + 3.0),
        (-11.0, baseline_dist + 11.0),
        (0.0, baseline_dist + 19.0),
        (11.0, baseline_dist + 11.0),
    ]

    # April tag interior square is 2.75 x 2.75 in:
    def ctr2rect(ctr):
        d = 2.75 / 2  # delta to apply to center for each point
        return [
            (ctr[0] - d, ctr[1] - d),
            (ctr[0] + d, ctr[1] - d),
            (ctr[0] + d, ctr[1] + d),
            (ctr[0] - d, ctr[1] + d),
        ]

    return [ctr2rect(ctr) for ctr in centers]


def get_tag_rects_calibrated_panel_img():
    # Map tag rects from world coordinates into a frame suitable
    # for visualizing the homography transform
    # panel is 28" wide by 22" high, make it 560 x 440 (20 ppi)
    def transform_point(pt):
        return (pt[0] + 14) * 20, (22 - pt[1]) * 20

    return [[transform_point(p) for p in rect] for rect in get_tag_rects_world(-11)]


def apply_homography(hmat, points):
    """
    Apply homography matrix hmat to a set of points in image coordinates
    (e.g. detected corners of tags).  This is weirdly fussy, steps are:
    - Extend points to have 1s as the third element.
    - Perform the matrix multiplication.
    - Scale the points based on the third coordinate. (This is the part I don't understand).
    """
    points = np.concatenate([points, np.ones((points.shape[0], 1))], axis=1)
    pred_raw = np.matmul(hmat, points.transpose()).transpose()
    pred, scale = np.split(pred_raw, [2], axis=1)
    return pred / scale


class TagsNotDetectedException(Exception):
    pass


class CalibrationSession(object):
    def __init__(self, panel_dist, desired_tags=3, max_tries=3):
        self.tmpdir = tempfile.mkdtemp()

        self.at_detector = dt_apriltags.Detector(
            searchpath=["apriltags"],
            families="tagStandard41h12",
            nthreads=1,
            quad_decimate=1.0,
            quad_sigma=0.0,
            refine_edges=1,
            decode_sharpening=0.25,
            debug=0,
        )

        self.panel_dist = panel_dist
        self.desired_tags = desired_tags
        self.max_tries = max_tries

        self.input_img = None
        self.input_tags = None

    def capture_image(self):
        subprocess.run(
            [
                "nvgstcapture",
                "-m",
                "1",
                "--orientation=2",  # Invert image
                "-A",
                "--capture-auto=1",
                "--file-name",
                self.tmpdir + "/",
            ],
            check=True,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        image_file = sorted(
            [fn for fn in os.listdir(self.tmpdir) if fn.endswith(".jpg")],
            key=lambda fn: os.stat(os.path.join(self.tmpdir, fn)).st_ctime,
        )[-1]
        return cv2.cvtColor(
            cv2.imread(os.path.join(self.tmpdir, image_file)), cv2.COLOR_BGR2RGB
        )

    def calibrate(self):
        best_img = None
        best_tags = []
        remaining_tries = self.max_tries

        while len(best_tags) < self.desired_tags and remaining_tries > 0:

            img = self.capture_image()
            img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            tags = self.at_detector.detect(img_gray)

            if len(tags) > len(best_tags):
                best_tags = tags
                best_img = img

            if len(best_tags) < self.desired_tags:
                if remaining_tries == 0:
                    if len(best_tags) == 0:
                        raise TagsNotDetectedException

            remaining_tries -= 1

        self.input_img = best_img
        self.input_tags = best_tags

        all_tag_rects_world = get_tag_rects_world(self.panel_dist)
        all_tag_rects_cal_img = get_tag_rects_calibrated_panel_img()

        self.det_corners_world = np.array(
            flatten_rects(all_tag_rects_world[t.tag_id] for t in best_tags)
        )
        self.det_corners_cal_img = np.array(
            flatten_rects(all_tag_rects_cal_img[t.tag_id] for t in best_tags)
        )
        self.det_corners_input_img = np.array(
            flatten_rects(list(t.corners) for t in best_tags)
        )

        self.world_hmat, _ = cv2.findHomography(
            self.det_corners_input_img, self.det_corners_world
        )
        self.cal_img_hmat, _ = cv2.findHomography(
            self.det_corners_input_img, self.det_corners_cal_img
        )

        self.calibrated_img = cv2.warpPerspective(
            self.input_img, self.cal_img_hmat, (560, 440), flags=cv2.INTER_LINEAR
        )

    @property
    def error(self):
        return (
            apply_homography(self.world_hmat, self.det_corners_input_img)
            - self.det_corners_world
        )


def main():
    pass


if __name__ == "__main__":
    main()
