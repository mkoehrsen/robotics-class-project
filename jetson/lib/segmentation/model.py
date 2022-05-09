import tensorflow as tf
from tensorflow import keras
import keras.layers as kl

def apply_layers(layers, input_tensor):
    """
    Like Sequential but without the model significance.
    """
    r = input_tensor
    for layer in layers:
        r = layer(r)
    return r

def create_erfnet(input_shape, num_classes):

    # looking at https://github.com/baudcode/tf-semantic-segmentation/blob/master/tf_semantic_segmentation/models/erfnet.py
    # but I couldn't get that project to load my dataset
    
    # ignoring L2 regularizer since the entire model defaults to having that off
    
    from tensorflow.keras import backend as K
    kl = keras.layers
    
    def conv(x, filters, kernel_size,
            strides=1,
            deconv=False,
            norm=keras.layers.BatchNormalization,
            activation="relu",
            dilation_rate=1):
        conv = kl.Conv2DTranspose if deconv else kl.Conv2D
        c = conv(filters, kernel_size,
                 strides=strides,
                 padding="same",
                 dilation_rate=dilation_rate,
                 activation=activation)
        y = c(x)
        if norm:
            y = norm()(y)
        return y
    
    def factorized_module(x, dropout=0.3, dilation=[1,1]):
        n = K.int_shape(x)[-1]
        y = conv(x, n, [3,1], dilation_rate=dilation[0], norm=None)
        y = conv(y, n, [1,3], dilation_rate=dilation[0])
        y = conv(y, n, [3,1], dilation_rate=dilation[1], norm=None)
        y = conv(y, n, [1,3], dilation_rate=dilation[1])
        y = kl.Dropout(dropout)(y)
        y = kl.Add()([x,y])
        return y
        
    def downsample(x, n):
        # removed activation and norm arguments since they weren't called or propagated
        f_in = K.int_shape(x)[-1]
        f_conv = n - f_in
        branch_1 = conv(x, f_conv, 3, strides=2)
        branch_2 = kl.MaxPool2D(pool_size=(2,2), strides=(2,2), padding="same")(x)
        return kl.Concatenate(axis=-1)([branch_1, branch_2])
        
    def upsample(x, n):
        # removed activation and norm arguments since they weren't called or propagated
        return conv(x, n, 3, strides=2, deconv=True)
        
    x = kl.Input(input_shape)
    
    y = downsample(x, 16)
    y = downsample(y, 64)
    for i in range(5):
        y = factorized_module(y, dilation=[1,1])
        
    y = downsample(y, 128)
    for k in range(2):
        for i in range(4):
            y = factorized_module(y, dilation=[1, pow(2, i + 1)])
    
    encoder = keras.Model(inputs=x, outputs=y)

    x = kl.Input(encoder.output_shape[1:])
    y = upsample(x, 64)
    for i in range(2):
        y = factorized_module(y, dilation=[1,1])
        
    y = upsample(y, 16)
    for i in range(2):
        y = factorized_module(y, dilation=[1,1])

    # y = upsample(y, num_classes)
    y = kl.UpSampling2D()(y)
    y = kl.Conv2D(num_classes, 3, activation="softmax", padding="same")(y)
    
    decoder = keras.Model(inputs=x, outputs=y)
    
    return keras.Sequential([encoder, decoder]), (encoder, decoder)
    
def create_unet(input_shape, num_classes):
    
    # looking at the following links:
    # https://keras.io/examples/vision/oxford_pets_image_segmentation/
    # https://towardsdatascience.com/semantic-image-segmentation-using-fully-convolutional-networks-bf0189fa3eb8
    
    # we're doing less than the keras page
    # we're focusing perhaps naively on the picture in towardsdatascience (which is from the paper)
    
    input = keras.layers.Input(input_shape)

    # in the spirit of the paper's opinion on the initializer
    k_init = keras.initializers.GlorotNormal()
    
    filter_plan = (8, 32, 64, 128) # (64, 128, 256, 512)
    
    last_output = input
    round_outputs = []
    for filters in filter_plan:
        # using padding="same" for now even though the paper wants "valid"
        # Challet did - it definitely simplifies the decoder half
        x = keras.layers.Conv2D(filters, 3, activation="relu", padding="same", kernel_initializer=k_init)(last_output)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.Conv2D(filters, 3, activation="relu", padding="same", kernel_initializer=k_init)(x)
        x = keras.layers.BatchNormalization()(x)
        round_outputs.append(x)
        last_output = keras.layers.MaxPooling2D()(x)
    
    bottleneck = 256 # 1024
    bottom = keras.layers.Conv2D(bottleneck, 3, activation="relu", padding="same", kernel_initializer=k_init)(last_output)
    x = keras.layers.BatchNormalization()(bottom)
    last_output = x
    
    for filters in filter_plan[::-1]:
        x = keras.layers.Conv2DTranspose(filters, 3, activation="relu", padding="same", kernel_initializer=k_init)(last_output)
        x = keras.layers.BatchNormalization()(x)
        x = keras.layers.UpSampling2D()(x)
        x = keras.layers.Concatenate()((x, round_outputs.pop()))
        x = keras.layers.Conv2DTranspose(filters, 3, activation="relu", padding="same", kernel_initializer=k_init)(x)
        last_output = keras.layers.BatchNormalization()(x)
        
    x = keras.layers.Conv2DTranspose(filter_plan[0], 3, activation="relu", padding="same", kernel_initializer=k_init)(last_output)
    x = keras.layers.BatchNormalization()(x)
    
    # Challet does a 3x3 conv, but the paper says 1x1, going with the paper
    x = keras.layers.Conv2D(num_classes, 1, activation="softmax", padding="same", kernel_initializer=k_init)(x)
    
    model = keras.Model(inputs=input, outputs=x)
    model.summary()
    return model

def create_classifier(input_shape):
    return keras.Sequential([
        kl.Input(input_shape),
        kl.Conv2D(16, 3, padding="same", activation="relu"),
        kl.BatchNormalization(),
        kl.MaxPooling2D(),
        kl.Conv2D(32, 3, padding="same", activation="relu"),
        kl.BatchNormalization(),
        kl.MaxPooling2D(),
        kl.Conv2D(64, 3, padding="same", activation="relu"),
        kl.BatchNormalization(),
        kl.Flatten(),
        kl.Dense(128, activation="relu"),
        kl.Dense(2, activation="softmax")
    ])

def create_autoencoder(input_shape, latent_dims):

    input = kl.Input(input_shape)

    enc_convs = [
        kl.Conv2D(64, (5,5), activation="relu", padding="same"),
        kl.BatchNormalization(),
        kl.MaxPooling2D(),
        kl.Conv2D(128, (3,3), activation="relu", padding="same"),
        kl.BatchNormalization(),
        kl.MaxPooling2D(),
        kl.Conv2D(128, (3,3), activation="relu", padding="same"),
        kl.BatchNormalization()
    ]        

    enc_conv_out = apply_layers(enc_convs, input)
    x = kl.Flatten()(enc_conv_out)
    latent = kl.Dense(latent_dims)(x)
    x = kl.Dense(36)(latent) #(16)(latent)
    x = kl.Reshape((6,6,1))(x) #(4,4,1))(x)
    
    dec_convs = [
        kl.Conv2DTranspose(128, (3,3), activation="relu", padding="same"),
        kl.BatchNormalization(),
        kl.UpSampling2D(),
        kl.Conv2DTranspose(128, (3,3), activation="relu", padding="same"),
        kl.BatchNormalization(),
        kl.UpSampling2D(),
        kl.Conv2DTranspose(64, (5,5), activation="relu", padding="same"),
        kl.BatchNormalization(),
        kl.Conv2D(input_shape[-1], (5,5), activation="sigmoid", padding="same")
    ]
    
    decoded = apply_layers(dec_convs, x)
    
    encoder = keras.Model(inputs=input, outputs=latent)
    autoencoder = keras.Model(inputs=input, outputs=decoded)
    autoencoder.summary()
    
    return autoencoder