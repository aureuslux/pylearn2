import theano
from theano import tensor
import numpy
from pylearn2.linear.conv2d_c01b import (Conv2D, make_random_conv2D,
    make_sparse_random_conv2D, setup_detector_layer_c01b)
from pylearn2.space import Conv2DSpace
from pylearn2.utils import sharedX
from pylearn2.testing.skip import skip_if_no_gpu
from pylearn2.models.maxout import MaxoutConvC01B
from pylearn2.models.mlp import MLP
skip_if_no_gpu()
import unittest
try:
    scipy_available = True
    import scipy.ndimage
except:
    scipy_available = False


class TestConv2DC01b(unittest.TestCase):
    def setUp(self):
        self.image = \
            numpy.random.rand(16, 3, 3, 1).astype(theano.config.floatX)
        self.image_tensor = tensor.tensor4()
        self.filters_values = numpy.ones(
            (16, 2, 2, 16), dtype=theano.config.floatX
        )
        self.filters = sharedX(self.filters_values, name='filters')
        self.conv2d = Conv2D(self.filters)

    def test_get_params(self):
        assert self.conv2d.get_params() == [self.filters]

    def test_lmul(self):
        f = theano.function([self.image_tensor],
                            self.conv2d.lmul(self.image_tensor))
        if scipy_available:
            numpy.allclose(
                f(self.image).reshape((16, 2, 2)),
                scipy.ndimage.filters.convolve(
                    self.image.reshape((16, 3, 3, 1)),
                    self.filters_values.reshape((16, 2, 2, 16))
                )[:2, :2]
            )

    def test_lmul_T(self):
        conv2d = self.conv2d.lmul(self.image_tensor)
        f = theano.function([self.image_tensor],
                            self.conv2d.lmul_T(conv2d))
        assert f(self.image).shape == self.image.shape

    def test_axes(self):
        default_axes = ('c', 0, 1, 'b')
        axes = (0, 'b', 1, 'c')
        mapping = tuple(axes.index(axis) for axis in default_axes)
        conv2d = Conv2D(self.filters, output_axes=axes)
        f_axes = theano.function([self.image_tensor],
                                 conv2d.lmul(self.image_tensor))
        f = theano.function([self.image_tensor],
                            self.conv2d.lmul(self.image_tensor))
        output_axes = f_axes(self.image)
        output = f(self.image)
        output_axes = numpy.transpose(output_axes, mapping)
        numpy.testing.assert_allclose(output, output_axes)
        assert output.shape == output_axes.shape

    def test_channels(self):
        filters_values = numpy.ones(
            (32, 2, 2, 16), dtype=theano.config.floatX
        )
        filters = sharedX(filters_values)
        image = numpy.random.rand(32, 3, 3, 1).astype(theano.config.floatX)
        conv2d = Conv2D(filters)
        f = theano.function([self.image_tensor],
                            conv2d.lmul(self.image_tensor))
        assert f(image).shape == (16, 2, 2, 1)

    def test_make_random_conv2D(self):
        default_axes = ('c', 0, 1, 'b')
        conv2d = make_random_conv2D(1, 16, default_axes, default_axes,
                                    16, (2, 2))
        f = theano.function([self.image_tensor],
                            conv2d.lmul(self.image_tensor))
        assert f(self.image).shape == (16, 2, 2, 1)
        assert conv2d.output_axes == default_axes

    def test_make_sparse_random_conv2D(self):
        axes = ('c', 0, 1, 'b')
        input_space = Conv2DSpace((3, 3), 16, axes=axes)
        output_space = Conv2DSpace((3, 3), 16, axes=axes)
        num_nonzero = 2
        kernel_shape = (2, 2)

        conv2d = make_sparse_random_conv2D(num_nonzero, input_space,
                                           output_space, kernel_shape)
        f = theano.function([self.image_tensor],
                            conv2d.lmul(self.image_tensor))
        assert f(self.image).shape == (16, 2, 2, 1)
        assert conv2d.output_axes == axes
        assert numpy.count_nonzero(conv2d._filters.get_value()) >= 32

    def test_setup_detector_layer_c01b(self):
        axes = ('c', 0, 1, 'b')
        layer = MaxoutConvC01B(16, 2, (2, 2), (2, 2),
                               (1, 1), 'maxout', irange=1.)
        input_space = Conv2DSpace((3, 3), 16, axes=axes)
        mlp = MLP(layers=[layer], input_space=input_space)
        layer.set_input_space(input_space)
        # setup_detector_layer_c01b(layer, input_space, rng)
        assert isinstance(layer.input_space, Conv2DSpace)
        input = theano.tensor.tensor4()
        f = theano.function([input], layer.fprop(input))
