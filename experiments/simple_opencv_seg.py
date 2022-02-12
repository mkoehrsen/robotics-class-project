import sys
import itertools
import cv2 as cv
import numpy as np

class GrabCut(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.rect = (width//2-100, height-200, 200, 200)

    def setup(self):
        self.mask = np.zeros((self.height, self.width), np.uint8)
        self.bg = np.zeros((1,65),np.float64)
        self.fg = np.zeros((1,65),np.float64)
        
    def process_frame(self, frame):
        cv.grabCut(frame, self.mask, self.rect, self.bg, self.fg, 1, cv.GC_INIT_WITH_RECT)
        m = np.where((self.mask==2)|(self.mask==0), 0, 1).astype("uint8")
        return frame * m[:,:,np.newaxis]

class FloodFill(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.point = (width//2, height-1)
        
    def setup(self):
        pass
    
    def process_frame(self, frame):
        lo=hi=[16] * 3
        mask = np.zeros((self.width+2, self.height+2)).astype("uint8")
        ret = cv.floodFill(frame, None, self.point, (0,0,0), lo, hi, 8 | cv.FLOODFILL_FIXED_RANGE)
        #print(ret)
        #print(len(ret))
        return frame
        
class Watershed(object):

    def __init__(self, width, height):
        self.width = width
        self.height = height
        
    def setup(self):
        pass
        
    def process_frame(self, frame):
        markers = np.zeros((height,width)).astype("int32")
        markers[0:200, 0:self.width] = 1
        markers[height-200:height, width//2-300:width//2+300] = 2
        cv.watershed(frame, markers)
        mask = np.where(markers == 2, 1, 0).astype("uint8")
        return frame * mask[:,:,np.newaxis]

infile, outfile = sys.argv[1:]

vid_in = cv.VideoCapture(infile)
width = int(vid_in.get(cv.CAP_PROP_FRAME_WIDTH))
height = int(vid_in.get(cv.CAP_PROP_FRAME_HEIGHT))
fps = vid_in.get(cv.CAP_PROP_FPS)
print(width,height)

encoder = cv.VideoWriter_fourcc(*"avc1")
vid_out = cv.VideoWriter(outfile, encoder, fps, (width,height))

op_type = Watershed
op = op_type(width, height)
op.setup()

counter = itertools.count()
while vid_in.isOpened():

    ret, frame = vid_in.read()

    if not ret:# or next(counter) > 20:
        break

    print("frame")

    new_frame = op.process_frame(frame)
    vid_out.write(new_frame)
    
vid_in.release()
vid_out.release()