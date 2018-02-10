"""A functional decomposition of the content reconstruction algorithm."""
import numpy as np
from PIL import Image
from typing import Callable
from keras import backend as K
from .vgg19 import VGG_19
from .img_util import load_image
from .img_util import normalize
from .img_util import denormalize
from .img_util import image_to_matrix
from .img_util import matrix_to_image
from .loss_functions import content_loss
from .optimizers.l_bfgs import L_BFGS


def reconstruct_content(content_path: str,
                        image_shape: tuple=None,
                        layer_name: str='block4_conv2',
                        optimizer: 'optimizers.Optimizer'=L_BFGS(),
                        iterations: int=10,
                        callback: Callable=None) -> Image:
    """
    Reconstruct the given content image at the given VGG19 layer.

    Args:
        content: the content image to reconstruct
        layer_name: the layer to reconstruct the content from
        optimizer: the optimizer for minimizing the content loss
        iterations: the number of iterations to run the optimizer
        callback: the callback for iterations of gradient descent

    Returns:
        the reconstructed content image based on the VGG19 response
        at the given layer name
    """
    # load the image with the given shape (or the default shape if there is
    # no shape provided)
    content = load_image(content_path, image_shape)
    # convert the binary image to a 3D NumPy matrix of RGB values
    content = image_to_matrix(content)
    # normalize the image's RGB values about the RGB channel means for the
    # ImageNet dataset
    content = normalize(content)

    # load the content image into keras as a constant, it never changes
    content = K.constant(content, name='Content')
    # create a placeholder for the trained image, this variable trains
    canvas = K.placeholder(content.shape, name='Cavnas')
    # combine the content and canvas tensors along the frame axis (0) into a
    # 4D tensor of shape [2, height, width, channels]
    tensor = K.concatenate([content, canvas], axis=0)
    # build the model with the 4D input tensor of content and canvas
    model = VGG_19(include_top=False, input_tensor=tensor, pooling='avg')

    # extract the layer's out that we have interest in for reconstruction
    layer = model[layer_name]

    # calculate the loss between the output of the layer on the content (0)
    # and the canvas (1)
    loss = content_loss(layer[0], layer[1])
    # calculate the gradients
    grads = K.gradients(loss, canvas)[0]
    # generate the iteration function for gradient descent optimization
    step = K.function([canvas], [loss, grads])

    # generate random noise
    noise = np.random.uniform(0, 1, content.shape)

    # optimize the white noise to reconstruct the content
    image = optimizer.minimize(noise, canvas.shape, step, iterations, callback)

    # de-normalize the image (from ImageNet means) and convert back to binary
    return matrix_to_image(denormalize(image.reshape(canvas.shape)[0]))


__all__ = ['reconstruct_content']