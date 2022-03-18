import sys
import numpy as np
import cv2 as cv
#import serial

def create_video_capture(source_string):
    # coerce the string to a camera integer if possible
    # which is a reasonable assumption since a file would at least have an extension
    try:
        src = int(source_string)
    except ValueError:
        src = source_string
    return cv.VideoCapture(src)

class RobotController(object):
    def __init__(self, outfile, fps, frame_size_wh, initial_motors):
        encoder = cv.VideoWriter_fourcc(*"avc1")
        self.writer = cv.VideoWriter(outfile, encoder, fps, frame_size_wh)
    @staticmethod
    def _intify_point(pt):
        return tuple(int(x) for x in pt)
    def control(self, goal_frame, current_frame, relationships, motors):
        for old_pt, new_pt in relationships:
            old_pt = self._intify_point(old_pt)
            new_pt = self._intify_point(new_pt)
            cv.circle(current_frame, new_pt, 5, color=(0,0,255), thickness=2)
            cv.line(current_frame, old_pt, new_pt, color=(0,0,255), thickness=2)
        self.writer.write(current_frame)
        pass
    def close(self):
        self.writer.release()
        
# class RobotController(object):
#     def __init__(self):
#         self.serial = None # TODO
#     def control(self, goal_frame, current_frame, relationships, motors):
#         raise NotImplementedError()
#     def close(self):
#         pass
        
class FeatureMapper(object):

    def __init__(self, base_frame):

        self.detector = cv.BRISK_create()
        self.base_kp, self.base_des = self.detector.detectAndCompute(base_frame, None)

        # if this is expensive, maybe these should be static and reusable across instances
        # we haven't measured, so we won't worry about it yet
        FLANN_INDEX_LSH = 6
        flann_idx_params = dict(algorithm=FLANN_INDEX_LSH, trees=5)
        flann_search_params = dict(checks=50)
        self.flann = cv.FlannBasedMatcher(flann_idx_params, flann_search_params)

    def _map_points(self, current_keypoints, matches):
        result = []
        for match_vector in matches:
            for m in match_vector:
                base_point = self.base_kp[m.queryIdx].pt
                current_point = current_keypoints[m.trainIdx].pt
                result.append((base_point, current_point))
        return result

    @staticmethod
    def _des_len_ok(des):
        return des is not None and len(des) >= 2

    def map(self, current_frame):

        kp_n, des_n = self.detector.detectAndCompute(current_frame, None)

        if self._des_len_ok(des_n) and self._des_len_ok(self.base_des):
            matches = self.flann.knnMatch(self.base_des, des_n, k=2)
        else:
            matches = []

        # ratio test from the paper
        good_matches = []
        for match_vector in matches:
            if len(match_vector) < 2:
                continue
            # slice, just in case k > 2
            m1, m2 = match_vector[:2]
            if m1.distance < 0.5 * m2.distance:
                # it's a list of one so "good_matches" has the same structure as "matches"
                good_matches.append([m1])
                
        return self._map_points(kp_n, good_matches)
        
class VisualNavigator(object):

    def __init__(self, base_frame):
        self.mapper = FeatureMapper(base_frame)
        
    # consider: leverage result of last steer
    def steer(self, current_frame, current_motors):
        relationships = self.mapper.map(current_frame)
        return (0, 0), relationships

infile, outfile = sys.argv[1:]
current_motors = 100, 100

vid_in = create_video_capture(infile)

width = int(vid_in.get(cv.CAP_PROP_FRAME_WIDTH))
height = int(vid_in.get(cv.CAP_PROP_FRAME_HEIGHT))
fps = vid_in.get(cv.CAP_PROP_FPS)

controller = RobotController(outfile, fps, (width, height), current_motors)

ret, first_frame = vid_in.read()
navigator = VisualNavigator(first_frame)

while vid_in.isOpened():

    ret, current_frame = vid_in.read()
    if not ret:
        break
        
    next_motors, relationships = navigator.steer(current_frame, current_motors)
    controller.control(first_frame, current_frame, relationships, next_motors)
    current_motors = next_motors

controller.close()

# #encoder = cv.VideoWriter_fourcc(*"avc1")
# #vid_out = cv.VideoWriter(outfile, encoder, fps, (width,height))
# 
# 
# # detector = cv.BRISK_create()
# # kp, des = detector.detectAndCompute(first_frame, None)
# 
# vid_out.write(cv.drawKeypoints(first_frame, kp, None, color=(255,0,0)))
# 
# # FLANN parameters
# # FLANN_INDEX_KDTREE = 1
# # FLANN_INDEX_LSH    = 6
# # index_params = dict(algorithm = FLANN_INDEX_LSH, trees = 5)
# # search_params = dict(checks=50)   # or pass empty dictionary
# # flann = cv.FlannBasedMatcher(index_params,search_params)
# 
# try:
#     while vid_in.isOpened():
# 
#         print("Frame")
#         ret, frame = vid_in.read()
#         if not ret:
#             break
#         
# #         kp_n, des_n = detector.detectAndCompute(frame, None)
#     
# #         if des_n is None:
# #             vid_out.write(frame)
# #             continue
# #     
# #         print(len(des_n))
# #         print(des_n)
# #         matches = flann.knnMatch(des, des_n, k=2)
# # 
# #         points = []
# #         for match_vector in matches:
# # 
# #             if len(match_vector) < 2:
# #                 continue
# # 
# #             # ratio test
# #             m, n = match_vector
# #             good = m.distance < 0.7 * n.distance
# #             if not good:
# #                 continue
# # 
# #             # p1 = kp[m.queryIdx].pt
# #             p2 = kp_n[m.trainIdx].pt
# #             points.append(p2)
# #             center = tuple(int(round(x)) for x in p2)
# #             cv.circle(frame, center, 5, color=(255,0,0), thickness=2)
#         
#         vid_out.write(frame)
#         
#         # vid_out.write(cv.drawKeypoints(frame, points, None, color=(255,0,0)))
# finally:
#     vid_out.release()