import sys
import time
import cv2
#import skimage
import numpy as np

input_path, output_path, = sys.argv[1:]

img_in = cv2.imread(input_path)
assert img_in is not None, "Could not load image."
print(img_in.shape)

height, width, depth = img_in.shape
#print(width, height)

red = np.int32([0,0,255])
red_indices = np.where(np.all(img_in == red, axis=-1))

orig_rect = np.float32([
    [2181, 1907],
    [2113, 1324],
    [3283, 1327],
    [3866, 1919]
])
print(red_indices)
print(orig_rect)

tr_rect = np.float32([
    [2000,2500],
    [2000,2300],
    [2200,2300],
    [2200,2500]
])

transform = cv2.getPerspectiveTransform(orig_rect,tr_rect)
print(transform)

# color the rectangle we've chosen
lag_y, lag_x = orig_rect[-1].astype(int)
for ix in range(len(orig_rect)):
    lead_y, lead_x = orig_rect[ix].astype(int)
    cv2.line(img_in, (lag_y, lag_x), (lead_y, lead_x), (255,0,0), 5)
    lag_y, lag_x = lead_y, lead_x

#img_out = img_in
img_out = cv2.warpPerspective(img_in, transform, (width, height),flags=cv2.INTER_LINEAR)
cv2.imwrite(output_path, img_out)