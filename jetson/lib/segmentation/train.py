import sys
import os
import random
import PIL

import tensorflow as tf
from tensorflow import keras
import numpy as np

from . import model
from . import datagen

def train_autoencoder(
        input_shape, latent_dims,
        epochs, steps_per_epoch,
        train_dataset, validation_dataset, anomaly_dataset,
        checkpoints, reconstructions
    ):
    
    loss_fn = keras.losses.BinaryCrossentropy(from_logits=False)
    
    autoencoder = model.create_autoencoder(input_shape, latent_dims)
    autoencoder.compile(optimizer="adam", loss=loss_fn)
    
    def validation_callback(name, dataset, epoch, logs):
        losses = []
        for i in range(8):
            x, y = next(dataset)
            y_hat = autoencoder.predict(x)
            losses.append(loss_fn(y, y_hat))
        loss = sum(losses) / len(losses)
        logs[name] = loss
        
        num_show = 64
        x_cat = np.concatenate(x[:num_show], axis=1)
        yh_cat = np.concatenate(y_hat[:num_show], axis=1)
        img_arr = np.concatenate((x_cat, yh_cat), axis=0)
        img_arr = (img_arr * 255).round().astype("uint8")
        img = PIL.Image.fromarray(img_arr) #, mode="YCbCr").convert(mode="RGB")
        img.save(
            reconstructions + "/AE - {name} - {epoch:03d} ({loss:.4f}).png".format(
                name=name, epoch=epoch, loss=loss
            )
        )
        
    def create_validation_callback(name, dataset):
        fn = lambda epoch, logs: validation_callback(name, dataset, epoch, logs)
        return keras.callbacks.LambdaCallback(on_epoch_end=fn)
        
    callbacks = [
        create_validation_callback("val_normal", validation_dataset),
        create_validation_callback("val_anomaly", anomaly_dataset),
        keras.callbacks.ModelCheckpoint(
            filepath = checkpoints + "/AE - {epoch:03d} ({loss:.4f})"
        )
    ]
    
    autoencoder.fit(
        x=train_dataset,
        epochs = epochs,
        steps_per_epoch = steps_per_epoch,
        callbacks = callbacks
    )

def do_train_autoencoder(normals, anomalies, latent_dims, epochs, checkpoints, reconstructions):
    
    normal_imgs = datagen.list_images(normals)
    random.shuffle(normal_imgs)
    normal_train_imgs, normal_val_imgs = datagen.partition(normal_imgs, 0.8)
    
    anomaly_imgs = datagen.list_images(anomalies)
    
    normal_train, N = datagen.generate_single_class_autoencoder_data(normal_train_imgs, patch_side=24)
    normal_validate, _ = datagen.generate_single_class_autoencoder_data(normal_val_imgs, patch_side=24)
    anomaly_validate, _ = datagen.generate_single_class_autoencoder_data(anomaly_imgs, patch_side=24)
    
    burn = next(normal_validate)[0]
    
    batch_size = 2048
    batch = lambda g: datagen.batch(g, batch_size=batch_size)
    
    os.makedirs(checkpoints, exist_ok=True)
    os.makedirs(reconstructions, exist_ok=True)
    
    train_autoencoder(
        burn.shape, int(latent_dims),
        int(epochs), N // batch_size,
        batch(normal_train), batch(normal_validate), batch(anomaly_validate),
        checkpoints, reconstructions
    )
    
def do_train_classifier(normals, anomalies, epochs, checkpoints):

    batch_size = 2048
    os.makedirs(checkpoints, exist_ok=True)

    def prep_data(dir, category):
        imgs = datagen.list_images(dir)
        train, val = datagen.partition(imgs, 0.8)
        train_patches, train_N = datagen.generate_patches(train)
        val_patches, val_N = datagen.generate_patches(val)
        train_xy = datagen.assign_one_hot_class(train_patches, category, 2)
        val_xy = datagen.assign_one_hot_class(val_patches, category, 2)
        return train_xy, train_N, val_xy, val_N
    
    def fuse_data(normal, anomaly):
        train = datagen.round_robin(normal[0], anomaly[0])
        val = datagen.round_robin(normal[2], anomaly[2])
        return (
            datagen.batch(train, batch_size=batch_size),
            (normal[1] + anomaly[1]) // batch_size,
            datagen.batch(val, batch_size=batch_size),
            (normal[3] + anomaly[3]) // batch_size
        )
    
    normal_tuple = prep_data(normals, 1)
    anomaly_tuple = prep_data(anomalies, 0)
    train, train_N, val, val_N = fuse_data(normal_tuple, anomaly_tuple)
    
    burn = next(val)[0][0]
    
    classifier = model.create_classifier(burn.shape)
    classifier.compile(
        optimizer="adam",
        loss="categorical_crossentropy",
        metrics=['accuracy']
    )
    
    callbacks = [
        keras.callbacks.ModelCheckpoint(
            filepath = checkpoints + "/C - {epoch:04d} ({loss:.4f})"
        )
    ]
    
    classifier.fit(
        x=train,
        epochs = int(epochs),
        steps_per_epoch = train_N,
        validation_data = val,
        validation_steps = val_N,
        callbacks = callbacks
    )

def do_train_unet(parent_dir, epochs, model_dir):
    return _do_train_whole(model.create_unet, parent_dir, epochs, model_dir)
    
def do_train_erfnet(parent_dir, epochs, model_dir):
    def create_model(*args):
        erf, (encoder, decoder) = model.create_erfnet(*args)
        return erf
    return _do_train_whole(create_model, parent_dir, epochs, model_dir)
    
def do_train_erfnet_encoder(parent_dir, epochs, model_dir):
    def create_model(*args):
        erf, (encoder, decoder) = model.create_erfnet(*args)
        return keras.Sequential([
            encoder,
            keras.layers.Conv2D(2, 3, activation="softmax", padding="same")
        ])
    def expectation_transformer(y):
        """ Downsample 8-fold to match the last encoder layer. """
        f = 8
        h, w = y.shape[1:3]
        assert not (h%f or w%f)

        # we're going to resample but then round the pixel to 0,1 to compel confidence
        y = np.reshape(y, y.shape + (1,))
        y = tf.image.resize(y, (h // f, w // f))
        y = np.round(y)
        return y
    return _do_train_whole(create_model, parent_dir, epochs, model_dir, expectation_transformer=expectation_transformer, partition_randseed=0)

def do_train_erfnet_decoder(encoder_path, parent_dir, epochs, erfnet_path):
    def create_model(*args):
        _, (_, decoder) = model.create_erfnet(*args)
        encoder_plus = keras.models.load_model(encoder_path)
        print(encoder_plus.layers)
        assert len(encoder_plus.layers) == 2
        encoder = keras.Sequential([encoder_plus.layers[0]])
        #encoder = keras.Model(encoder_plus.input, encoder_plus.layers[0].output)
        encoder.trainable = False
        return keras.Sequential([encoder, decoder])
    _do_train_whole(create_model, parent_dir, epochs, erfnet_path, partition_randseed=0)

def _do_train_whole(model_create_fn, parent_dir, epochs, model_dir, expectation_transformer=None, partition_randseed=None):
    items = os.listdir(parent_dir)
    items = [os.path.join(parent_dir, item) for item in items]
    random.Random(partition_randseed).shuffle(items)
    train_items, val_items = datagen.partition(items, 0.8)
        
    train = datagen.generate_segmentation_data(train_items)
    val = datagen.generate_segmentation_data(val_items)

    input_shape = next(val)[0].shape

    batch_size = 4
    def batcher(g):
        return datagen.batch(g, batch_size=batch_size)    

    if not expectation_transformer:
        expectation_transformer = lambda y: y

    def transform_y(g):
        return ((x,expectation_transformer(y)) for (x,y) in g)

    train = transform_y(batcher(train))
    val   = transform_y(batcher(val))

    callbacks = [
        keras.callbacks.ModelCheckpoint(
            filepath=model_dir,
            save_best_only=True
        )
    ]

    mod = model_create_fn(input_shape, 2)
    mod.compile(optimizer="adam", loss="sparse_categorical_crossentropy")
    mod.summary(expand_nested=True)
    
    mod.fit(
        x=train,
        epochs=int(epochs),
        steps_per_epoch=len(train_items) // batch_size,
        validation_data=val,
        validation_steps = len(val_items) // batch_size,
        callbacks=callbacks
    )

if __name__ == "__main__":

    opcode = sys.argv[1]
    args = sys.argv[2:]
    
    func_name = "do_" + opcode
    func = locals()[func_name]
    func(*args)