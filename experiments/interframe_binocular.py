# Epipolar Geometry
# see https://docs.opencv.org/3.4/da/de9/tutorial_py_epipolar_geometry.html

import sys
import itertools
import cv2 as cv
import numpy as np

infile, outfile = sys.argv[1:]

def process(last_frame, current_frame):
    img1, img2 = last_frame, current_frame
    
    sift = cv.SIFT_create()

    # find keypoints and descriptors
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)
    
    # FLANN parameters
    FLANN_INDEX_KDTREE = 1
    index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    search_params = dict(checks=50)
    
    flann = cv.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(des1, des2, k=2)
    
    pts1 = []
    pts2 = []
    
    # ratio test as per Lowe's paper
    for i,(m,n) in enumerate(matches):
        if m.distance < 0.8 * n.distance:
            pts2.append(kp2[m.trainIdx].pt)
            pts1.append(kp1[m.queryIdx].pt)

    # now let's find the Fundamental Matrix
    pts1 = np.int32(pts1)
    pts2 = np.int32(pts2)
    F, mask = cv.findFundamentalMat(pts1, pts2, cv.FM_LMEDS)

    # we select only inlier points
    pts1 = pts1[mask.ravel() == 1]
    pts2 = pts2[mask.ravel() == 1]
    
    # Find epilines corresponding to points in right image (second image) and
    # drawing its lines on left image
    #lines1 = cv.computeCorrespondEpilines(pts2.reshape(-1,1,2), 2,F)
    #lines1 = lines1.reshape(-1,3)
    #img5,img6 = drawlines(img1,img2,lines1,pts1,pts2)
    
    # Find epilines corresponding to points in left image (first image) and
    # drawing its lines on right image
    lines2 = cv.computeCorrespondEpilines(pts1.reshape(-1,1,2), 1,F)
    lines2 = lines2.reshape(-1,3)
    img3,img4 = drawlines(img2,img1,lines2,pts2,pts1)
    
    return np.concatenate((img3,img4), axis=1)

def drawlines(img1,img2,lines,pts1,pts2):
    ''' img1 - image on which we draw the epilines for the points in img2
        lines - corresponding epilines '''
    r,c,d = img1.shape
    #img1 = cv.cvtColor(img1,cv.COLOR_GRAY2BGR)
    #img2 = cv.cvtColor(img2,cv.COLOR_GRAY2BGR)
    for r,pt1,pt2 in zip(lines,pts1,pts2):
        color = tuple(np.random.randint(0,255,3).tolist())
        x0,y0 = map(clamp_int32, [0, -r[2]/r[1] ])
        x1,y1 = map(clamp_int32, [c, -(r[2]+r[0]*c)/r[1] ])
        img1 = cv.line(img1, (x0,y0), (x1,y1), color,1)
        img1 = cv.circle(img1,tuple(pt1),5,color,-1)
        img2 = cv.circle(img2,tuple(pt2),5,color,-1)
    return img1,img2

ii32 = np.iinfo(np.int32)
def clamp_int32(n):
    n = int(n)
    return max(ii32.min, min(ii32.max, int(n)))

vid_in = cv.VideoCapture(infile)

width = int(vid_in.get(cv.CAP_PROP_FRAME_WIDTH))
height = int(vid_in.get(cv.CAP_PROP_FRAME_HEIGHT))
fps = vid_in.get(cv.CAP_PROP_FPS)

encoder = cv.VideoWriter_fourcc(*"avc1")
vid_out = cv.VideoWriter(outfile, encoder, fps, (width*2,height))

try:
    ret, last_frame = vid_in.read()
    while vid_in.isOpened():
    
        ret, current_frame = vid_in.read()
        if not ret:
            break
    
        print("Processing frame.")
        out_frame = process(last_frame, current_frame)
        vid_out.write(out_frame)
    
        last_frame = current_frame

    vid_in.release()

finally:
    vid_out.release()