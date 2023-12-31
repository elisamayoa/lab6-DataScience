# -*- coding: utf-8 -*-
"""laboratorio-6-grupo-18.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1kHCAfg00EV3x7MvnMkDBofRY1vmF5yVD
"""

import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

"""**Definición de hiperparámetros**"""

BATCH_SIZE = 128
IM_SHAPE = (64, 64, 3)
LEARNING_RATE = 5e-4
LATENT_DIM = 100
EPOCHS = 30

"""**Carga de datos**"""

dataset = tf.keras.preprocessing.image_dataset_from_directory(
    "/kaggle/input/celeba-dataset/img_align_celeba/img_align_celeba/",
    label_mode = None,
    image_size = (IM_SHAPE[0], IM_SHAPE[1]),
    batch_size = BATCH_SIZE
)

"""**Procesamiento de la imagen**"""

def preprocess(image):
    return tf.cast(image, dtype = tf.float32)/127.5 - 1.0

train_data = (
    dataset
    .map(preprocess)
    .unbatch()
    .shuffle(buffer_size = 1024, reshuffle_each_iteration = True)
    .batch(BATCH_SIZE, drop_remainder = True)
    .prefetch(tf.data.AUTOTUNE)
)

from tensorflow.keras.layers import (Input, Dense, Conv2DTranspose, Reshape,
                                     LeakyReLU, BatchNormalization, Flatten, Conv2D)

"""**Creación del generador**"""

generator = tf.keras.Sequential([
    Input(shape = (LATENT_DIM,)),
    Dense(4*4*LATENT_DIM,),
    Reshape((4,4,LATENT_DIM)),

    Conv2DTranspose(512, kernel_size = 4, strides = 2, padding = 'same'),
    BatchNormalization(),
    LeakyReLU(0.3),

    Conv2DTranspose(256, kernel_size = 4, strides = 2, padding = 'same'),
    BatchNormalization(),
    LeakyReLU(0.3),

    Conv2DTranspose(128, kernel_size = 4, strides = 2, padding = 'same'),
    BatchNormalization(),
    LeakyReLU(0.3),

    Conv2DTranspose(3, kernel_size = 4, strides = 2, activation = tf.keras.activations.tanh, padding = 'same'),
], name = 'generator')

"""**Creación del discriminador**"""

discriminator = tf.keras.Sequential([
    Input(shape = (IM_SHAPE[0],IM_SHAPE[1], IM_SHAPE[2])),

    Conv2D(64, kernel_size = 4, strides = 2, padding = 'same'),
    LeakyReLU(0.3),

    Conv2D(128, kernel_size = 4, strides = 2, padding = 'same'),
    BatchNormalization(),
    LeakyReLU(0.3),

    Conv2D(256, kernel_size = 4, strides = 2, padding = 'same'),
    BatchNormalization(),
    LeakyReLU(0.3),

    Conv2D(1, kernel_size = 4, strides = 2, padding = 'same'),

    Flatten(),
    Dense(1, activation = 'sigmoid')

], name = 'discriminator')

"""**Definición de la GAN**"""

class GAN(tf.keras.Model):
    def __init__(self, generator, discriminator):
        super(GAN, self).__init__()

        self.generator = generator
        self.discriminator = discriminator

    def compile(self, d_optimizer, g_optimizer, loss_fun):
        super(GAN, self).compile()
        self.d_optimizer = d_optimizer
        self.g_optimizer = g_optimizer
        self.loss = loss_fun
        self.d_loss_mat = tf.keras.metrics.Mean(name = 'd_loss')
        self.g_loss_mat = tf.keras.metrics.Mean(name = 'g_loss')

    @property
    def metrics(self):
        return [self.d_loss_mat, self.g_loss_mat]

    def train_step(self, real_img):
        batch_size = tf.shape(real_img)[0]
        random_noise = tf.random.normal(shape = (batch_size, LATENT_DIM))
        fake_imgs = self.generator(random_noise)
        real_labels = tf.ones((batch_size, 1)) + 0.25*tf.random.uniform((batch_size, 1), minval = -1, maxval = 1)
        fake_labels = tf.zeros((batch_size, 1)) + 0.25*tf.random.uniform((batch_size, 1),)

        with tf.GradientTape() as recorder:
            real_pred = self.discriminator(real_img)
            d_loss_real = self.loss(real_labels, real_pred)

            fake_pred = self.discriminator(fake_imgs)
            d_loss_fake = self.loss(fake_labels, fake_pred)

            d_loss = d_loss_real + d_loss_fake
        partial_derivatives = recorder.gradient(d_loss, self.discriminator.trainable_weights)
        self.d_optimizer.apply_gradients(zip(partial_derivatives, self.discriminator.trainable_weights))

        random_noise = tf.random.normal(shape = (batch_size, LATENT_DIM))
        flipped_fake_labels = tf.ones((batch_size, 1))

        with tf.GradientTape() as recorder:

            fake_pred = self.discriminator(self.generator(random_noise))
            g_loss = self.loss(flipped_fake_labels, fake_pred)

        partial_derivatives = recorder.gradient(g_loss, self.generator.trainable_weights)
        self.g_optimizer.apply_gradients(zip(partial_derivatives, self.generator.trainable_weights))

        self.d_loss_mat.update_state(d_loss)
        self.g_loss_mat.update_state(g_loss)

        return {'g_loss':self.g_loss_mat.result(),
                'd_loss':self.d_loss_mat.result()}

gan = GAN(generator, discriminator)
gan.compile(
    d_optimizer = tf.keras.optimizers.Adam(learning_rate = LEARNING_RATE, beta_1 = 0.5),
    g_optimizer = tf.keras.optimizers.Adam(learning_rate = LEARNING_RATE, beta_1 = 0.5),
    loss_fun = tf.keras.losses.BinaryCrossentropy()
)

"""**Mostrar resultados**"""

class ShowGeneratedImages(tf.keras.callbacks.Callback):
    def __init__(self, latent_dim = 100):
        self.latent_dim = latent_dim

    def on_epoch_end(self, epoch, logs = None):
        n = 6
        k = 0
        out = self.model.generator(tf.random.normal(shape = (64, self.latent_dim)))
        plt.figure(figsize = (16, 16))
        for i in range(n):
            for j in range(n):
                ax = plt.subplot(n, n, k+1)
                plt.imshow((out[k]+1)/2,)
                plt.axis('off')
                k+=1
        plt.savefig("gen_images_epoch_{}.png".format(epoch))

history = gan.fit(train_data.take(10), epochs = EPOCHS, callbacks = [ShowGeneratedImages(LATENT_DIM)])