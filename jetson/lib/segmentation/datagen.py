import random
import os
import functools
import sys
from itertools import chain, repeat, cycle, count
import tensorflow as tf
import PIL
import numpy as np

def partition(sliceable, fraction):
    split_point = int(len(sliceable) * fraction)
    left, right = sliceable[:split_point], sliceable[split_point:]
    assert left and right, "Fraction too extreme for a dataset this small."
    return left, right

def random_flip(arr, horizontal=True, vertical=True, arr2=None):
    h = horizontal & random.randint(0,1)
    v = vertical & random.randint(0,1)
    def flip(a):
        if h:
            a = np.flip(a, axis=1)
        if v:
            a = np.flip(a, axis=0)
        return a
    a1 = flip(arr)
    if arr2 is not None:
        a2 = flip(arr2)
        return (a1,a2)
    return a1

def random_rotation(arr, max_degree):
    degree = random.uniform(-max_degree, max_degree)
    im = PIL.Image.fromarray(arr)
    im = im.rotate(degree)
    return np.array(im)

def random_brightness(arr, brightness_offset):
    factor = 1 + random.uniform(-brightness_offset, brightness_offset)
    im = PIL.Image.fromarray(arr)
    enhancer = PIL.ImageEnhance.Brightness(im)
    im = enhancer.enhance(factor)
    return np.array(im)

def thumbnail(arr, dest_width, dest_height):
    im = PIL.Image.fromarray(arr)
    im.thumbnail((dest_width, dest_height))
    return np.array(im)

def ycbcr(arr):
    im = PIL.Image.fromarray(arr)
    im = im.convert(mode="YCbCr")
    return np.array(im)

def extract_patches(arr, patch_side, stride=None):
    if not stride:
        stride = patch_side
    p = patch_side
    max_h, max_w = arr.shape[:2]
    for h in range(0, max_h, stride):
        for w in range(0, max_w, stride):
            patch = arr[h:h+p, w:w+p]
            # ignore clipped patches
            if patch.shape[:2] != (p,p):
                continue
            yield patch, (h,w)

def load_img(fn):
    with PIL.Image.open(fn) as im:
        arr = np.array(im.convert(mode="RGB"))
        #print(fn, arr.shape)
        assert len(arr.shape) == 3, "No color for %s, shape is %s" % (fn, arr.shape)
        return arr
        
def list_images(dir):
    suff = set(["jpeg", "jpg", "png", "tiff"])
    def is_image(fn):
        return True in [fn.lower().endswith(s) for s in suff]
    
    result = []
    for f in os.listdir(dir):
        if is_image(f):
            result.append(os.path.join(dir, f))
    return result

def batch(g, batch_size=256):
    x_buf = []
    y_buf = []
    try:
        while True:
            for i in range(batch_size):
                i_x, i_y = next(g)
                x_buf.append(i_x)
                y_buf.append(i_y)    
            yield np.stack(x_buf), np.stack(y_buf)
            del x_buf[:]
            del y_buf[:]
    except StopIteration:
        pass
    if x_buf:
        yield np.stack(x_buf), np.stack(y_buf)

def iterate_over(sequence, iterations=float("inf")):
    if iterations == float("inf"):
        return cycle(sequence)
    else:
        return chain.from_iterable(repeat(sequence, iterations))

def generate_patches(
        image_files,
        patch_side=16,
        res_width=640,
        res_height=480,
        rotate=5,
        brightness=0.5,
        stride=8,
        iterations=float("inf")
    ):

    if stride is None:
        stride = patch_side

    N_estimated = len(image_files) * (res_height//stride) * (res_width//stride)
    print("Generating a data set of approximately %d patches per iteration." % N_estimated)

    # TODO noise    
    
    def gen():
        for fn in iterate_over(files, iterations=iterations):
            arr = load_img(fn)
            arr = random_rotation(arr, rotate)
            arr = random_brightness(arr, brightness)
            arr = thumbnail(arr, res_width, res_height)
            # arr = ycbcr(arr)
            # PIL.Image.fromarray(arr).save("transformed_%04d.png" % next(c))
            arr = np.true_divide(arr, 255, dtype="float32")
            for patch, ix in extract_patches(arr, patch_side, stride=stride):
                yield patch

    return gen(), N_estimated
 
def pair_for_autoencoder(g):
    for x in g:
        yield (x, x)

def assign_one_hot_class(g, k, n):
    for x in g:
        y = np.zeros(n, dtype="uint8")
        y[k] = 1
        yield (x, y)

def round_robin(*gn):
    while True:
        for g in gn:
            yield next(g)

def generate_single_class_autoencoder_data(*args, **kwargs):
    g, N = generate_patches(*args, **kwargs)
    return pair_for_autoencoder(g), N

def open_labelme_segmentation(item):
    """ Return image_array, label_array """
    img_fn = item + "/img.png"
    lab_fn = item + "/label.png"
    with PIL.Image.open(img_fn) as im:
        x = np.array(im)
    with PIL.Image.open(lab_fn) as im:
        y = np.array(im)
    return (x,y)

def generate_segmentation_data(items, brightness=0.5, h_flip=True, iterations=float("inf"), opener=open_labelme_segmentation):
    for item in iterate_over(items, iterations=iterations):
        x, y = opener(item)
        x, y = random_flip(x, arr2=y, horizontal=h_flip, vertical=False)
        x = random_brightness(x, brightness_offset=brightness)
        x = np.true_divide(x, 255, dtype="float32")
        yield x, y
        
if __name__ == "__main__":
    parent_dir, = sys.argv[1:]
    files = os.listdir(parent_dir)
    files = [os.path.join(parent_dir, f) for f in files]
    g = generate_single_class_autoencoder_data(files, iterations=1)
    c = count()
    for x in g:
        x = next(c)
        if x % 1000 == 0:
            print(x)