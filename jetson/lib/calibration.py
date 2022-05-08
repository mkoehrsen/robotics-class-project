import argparse
import cv2
import dt_apriltags
import enum
import json
import logging
import numpy as np
import os
import subprocess
import sys
import tempfile
from camera import capture_image

"""
Calibration protocol:

- Center the front wheels of the vehicle on the center line of the positioning panel.
- Align the tag panel with the positioning panel in the chosen orientation, and
  measure distance in inches from the top line of the positioning panel to the bottom line of
  the tag panel. This is the panel_dist to give to CalibrationSession.
- Create a CalibrationSession with appropriate orientation and with the measured panel distance, and
  invoke calibrate(). Unless no tags are detected at all the calibration session will 
"""
CALIBRATION_DIR = os.path.join(os.environ["HOME"], ".robot", "calibration")


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


def deskew(img, hmat, output_size, output_ppi=20, output_y_offset=20):
    """
    Uses a calibrated homography matrix to de-skew an image taken
    by the vehicle.

    - img: input image from the vehicle
    - hmat: homography matrix representing transform from image coordinates to vehicle coordinates.
    - output_size: pair of (width, height) of desired output in pixels, as a list or tuple.
    - output_ppi: number of pixels in the output representation that represent one inch in the world.
    - output_y_offset: distance in inches from the vehicle origin to the bottom of the output image.
    """
    world2output = np.array(
        [
            [float(output_ppi), 0.0, output_size[0] / 2],
            [
                0.0,
                -float(output_ppi),
                float(output_y_offset * output_ppi + output_size[1]),
            ],
            [0.0, 0.0, 1.0],
        ]
    )
    deskew_mat = np.matmul(world2output, hmat)
    return cv2.warpPerspective(img, deskew_mat, output_size, flags=cv2.INTER_LINEAR)


def apply_homography(hmat, points):
    """
    Apply homography matrix hmat to a set of points in image coordinates
    (e.g. detected corners of tags).  This is weirdly fussy, steps are:
    - Extend points to have 1s as the third element.
    - Perform the matrix multiplication.
    - Scale the points based on the third coordinate.
    """
    # Note -- it turns out the function cv2.perspectiveTransform also does this operation.
    # The following gives the same result other than some small numeric differences.
    # cv2.perspectiveTransform(points.reshape(1,len(points),2), hmat).reshape(len(points),2)
    points = np.array(points)
    points = np.concatenate([points, np.ones((points.shape[0], 1))], axis=1)
    pred_raw = np.matmul(hmat, points.transpose()).transpose()
    pred, scale = np.split(pred_raw, [2], axis=1)
    return pred / scale


class TagsNotDetectedException(Exception):
    pass


class CalibrationSession(object):
    def __init__(self, panel_dist, orientation=0, desired_tags=3, max_tries=3):
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
        self.orientation = orientation
        self.desired_tags = desired_tags
        self.max_tries = max_tries

        self.input_img = None
        self.input_tags = None

    def calibrate(self):
        best_img = None
        best_tags = []
        remaining_tries = self.max_tries

        while len(best_tags) < self.desired_tags and remaining_tries > 0:

            img = capture_image(self.tmpdir, self.orientation)
            img_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            tags = self.at_detector.detect(img_gray)

            if len(tags) > len(best_tags):
                best_tags = tags
                best_img = img

            remaining_tries -= 1

        if len(best_tags) == 0:
            raise TagsNotDetectedException

        self.input_img = best_img
        self.input_tags = best_tags

        all_tag_rects_world = get_tag_rects_world(self.panel_dist)

        self.det_corners_world = np.array(
            flatten_rects(all_tag_rects_world[t.tag_id] for t in best_tags)
        )
        self.det_corners_input_img = np.array(
            flatten_rects(list(t.corners) for t in best_tags)
        )

        self.world_hmat, _ = cv2.findHomography(
            self.det_corners_input_img, self.det_corners_world
        )
        self.calibrated_img = deskew(
            self.input_img,
            self.world_hmat,
            (560, 440),
            output_ppi=20,
            output_y_offset=self.panel_dist + 11.0,
        )

    @property
    def error(self):
        return (
            apply_homography(self.world_hmat, self.det_corners_input_img)
            - self.det_corners_world
        )

    @property
    def input_tag_ids(self):
        return [t.tag_id for t in self.input_tags]


def write_calibration(hmat, input_img, calibrated_img):
    cv2.imwrite(os.path.join(CALIBRATION_DIR, "input.png"), input_img[:, :, ::-1])
    cv2.imwrite(
        os.path.join(CALIBRATION_DIR, "calibrated.png"), calibrated_img[:, :, ::-1]
    )
    with open(os.path.join(CALIBRATION_DIR, "hmat.json"), "wt") as f:
        # TODO might lose some precision on dump/load?
        json.dump(list(hmat.reshape((9,))), f)


def read_calibration():
    with open(os.path.join(CALIBRATION_DIR, "hmat.json"), "rt") as f:
        return (
            np.array(json.load(f)).reshape((3, 3)),
            cv2.imread(os.path.join(CALIBRATION_DIR, "input.png")),
            cv2.imread(os.path.join(CALIBRATION_DIR, "calibrated.png")),
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("panel_dist", type=float)
    parser.add_argument("--desired-tags", type=int, default=3)
    parser.add_argument("--max-tries", type=int, default=3)
    parser.add_argument("--orientation", type=int, default=0)
    args = parser.parse_args()

    sess = CalibrationSession(
        panel_dist=args.panel_dist,
        orientation=args.orientation,
        desired_tags=args.desired_tags,
        max_tries=args.max_tries,
    )
    sess.calibrate()

    sys.stderr.write(f"Used tags {sess.input_tag_ids} to calibrate.\n")
    sys.stderr.write(f"Error vector is:\n{sess.error}\n")

    if os.path.exists(CALIBRATION_DIR):
        import datetime

        backup_dir = CALIBRATION_DIR + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        sys.stderr.write(f"Backing up old calibration directory to {backup_dir}.\n")
        os.rename(CALIBRATION_DIR, backup_dir)
    os.makedirs(CALIBRATION_DIR)

    write_calibration(sess.world_hmat, sess.input_img, sess.calibrated_img)


if __name__ == "__main__":
    main()
