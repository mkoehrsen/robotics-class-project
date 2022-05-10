import sys
import os
import itertools

from . import datagen

import PIL
import numpy as np
import cv2

import tensorflow as tf
from tensorflow import keras

COLOR_UNKNOWN, COLOR_NONFLOOR, COLOR_FLOOR = 0, 1, 2
DEFAULT_COLORS = {
    COLOR_UNKNOWN:  np.array((1.,1.,1.)),
    COLOR_NONFLOOR: np.array((1.,0.,0.)),
    COLOR_FLOOR:    np.array((0.,1.,0.))
}

def color_slice(arr, lower, upper, bgr_f32, blend=0.2):
    """ Applies color in-place. """
    h1, w1 = lower
    h2, w2 = upper
    s = arr[h1:h2, w1:w2]
    s *= (1-blend)
    s += blend * bgr_f32    

def label_frame(classifier_callback, frame, patch_side, colors, stride=None, batch_size=512):
    assert stride is None, "We don't yet support labeling sub-patches, but we want to."
    patch_gen = datagen.extract_patches(frame, patch_side, stride=stride)
    batcher = datagen.batch(patch_gen, batch_size=batch_size)
    for patches, coords in batcher:
        categories = classifier_callback(patches)
        for ix, cat in enumerate(categories):
            h, w = coords[ix]
            color_slice(frame, (h,w), (h+patch_side,w+patch_side), colors[cat])

def label_image(classifier_callback, patch_side, path_in, path_out):
    pass
    
def label_video(classifier_callback, patch_side, video_in, video_out):
    pass

def do_label_image_from_classifier(model_path, image_in, image_out, threshold=0.75):
    model = TFRenderer(model_path)

    # expecting 4D like (None, 16, 16, 3)
    patch_side = model.input.shape[1]

    with PIL.Image.open(image_in) as im:
        arr = np.array(im.convert(mode="RGB"))

    arr = np.true_divide(arr, 255, dtype="float32")
    
    def classify(patches):
        # expecting two categories, 0=nonfloor, 1=floor
        # producing three categories, 0=unknown, 1=nonfloor, 2=floor
        c = categories_one_hot = model.predict(patches)
        # they're probabilities over two categories, so this is simple
        return np.where(c[:,0] >= threshold, 1, 0) + np.where(c[:,1] >= threshold, 2, 0)
        
    label_frame(classify, arr, patch_side, DEFAULT_COLORS)
    arr = (arr * 255).astype("uint8")
    PIL.Image.fromarray(arr).save(image_out)

def label_image_from_unet(model, int_arr_in, threshold=0.75):
    arr_in = np.true_divide(int_arr_in, 255, dtype="float32")
    batch_in = np.stack([arr_in])
    batch_out = model.predict(batch_in)
    arr_out = batch_out[0]
    
    mask = np.zeros(arr_in.shape, dtype="float32")
    mask += np.expand_dims(np.where(arr_out[:,:,0] >= threshold, 1., 0), axis=-1) * DEFAULT_COLORS[COLOR_NONFLOOR]
    mask += np.expand_dims(np.where(arr_out[:,:,1] >= threshold, 1., 0), axis=-1) * DEFAULT_COLORS[COLOR_FLOOR]
    # TODO unknown case, this doesn't work
#    mask += np.where(mask[:,:] == (0,0,0), DEFAULT_COLORS[COLOR_UNKNOWN], (0,0,0))    
    
    blended = 0.7 * arr_in + 0.3 * mask
    return (blended * 255).astype("uint8")

def do_label_image_from_unet(model_path, threshold, image_in, image_out):
    model = TFRenderer(model_path)
    with PIL.Image.open(image_in) as im:
        int_arr_in = np.array(im)
    int_arr_out = label_image_from_unet(model, int_arr_in, threshold=float(threshold))
    PIL.Image.fromarray(int_arr_out).save(image_out)

def do_label_images_from_unet(model_path, threshold, input_image_dir, output_image_dir):
    model = TFRenderer(model_path)
    for fn in os.listdir(input_image_dir):
        print(fn)
        in_path = os.path.join(input_image_dir, fn)
        out_path = os.path.join(output_image_dir, fn)
        with PIL.Image.open(in_path) as im:
            int_arr_in = np.array(im)
        int_arr_out = label_image_from_unet(model, int_arr_in, threshold=float(threshold))
        PIL.Image.fromarray(int_arr_out).save(out_path)    

def do_label_video_from_unet(model_path, threshold, video_in, video_out):
    model = TFRenderer(model_path)
    # model = keras.models.load_model(model_path)
    camera = cv2.VideoCapture(video_in)
    
    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = camera.get(cv2.CAP_PROP_FPS)
    
    codec = cv2.VideoWriter_fourcc(*"mp4v") #*"avc1")
    output = cv2.VideoWriter(video_out, codec, fps, (width,height))
    
    c = itertools.count()
    while camera.isOpened():
        ret, in_frame = camera.read()
        if not ret:
            break
        in_rgb = np.flip(in_frame, axis=-1)
        out_rgb = label_image_from_unet(model, in_rgb, threshold=float(threshold))
        out_frame = np.flip(out_rgb, axis=-1)
        print("frame", next(c), in_frame.shape, out_frame.shape)
        output.write(out_frame)
    output.release()

class KerasRenderer(object):
    def __init__(self, model_path):
        self.model = tf.keras.models.load_model(model_path)
    def predict(self, batch):
        return self.model.predict(batch)

class TFRenderer(object):
    def __init__(self, model_path):
        from tensorflow.python.saved_model import tag_constants, signature_constants
        self.model = tf.saved_model.load(model_path, tags=tag_constants.SERVING)
        self.graph_func = self.model.signatures[signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY]
    def predict(self, batch):
        batch_tensor = tf.constant(batch)
        result, = list(self.graph_func(batch_tensor).values())
        return result.numpy()

if __name__ == "__main__":

    opcode = sys.argv[1]
    args = sys.argv[2:]
    
    func_name = "do_" + opcode
    func = locals()[func_name]
    func(*args)