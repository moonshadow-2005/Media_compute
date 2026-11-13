import unittest

import numpy as np

from l0_smoothing.core import (difference_spectrum, fft_update, gradient_adjoint,
                          joint_threshold, periodic_gradient, smooth)


class L0Tests(unittest.TestCase):
    def test_periodic_boundary_by_hand(self):
        a = np.array([[1., 2., 4.], [8., 16., 32.]])
        gx, gy = periodic_gradient(a)
        np.testing.assert_array_equal(gx, [[1, 2, -3], [8, 16, -24]])
        np.testing.assert_array_equal(gy, [[7, 14, 28], [-7, -14, -28]])

    def test_adjoint_identity(self):
        rng = np.random.default_rng(7)
        a, h, v = rng.normal(size=(3, 4, 7, 3))
        gx, gy = periodic_gradient(a)
        self.assertAlmostEqual(np.sum(gx*h + gy*v), np.sum(a*gradient_adjoint(h, v)))

    def test_color_and_direction_joint_threshold(self):
        gx = np.array([[[.4, .4, 0.], [.5, 0., 0.]]])
        gy = np.array([[[0., 0., .4], [0., 0., 0.]]])
        h, v = joint_threshold(gx, gy, .25)
        np.testing.assert_array_equal(h[0, 0], gx[0, 0])
        np.testing.assert_array_equal(v[0, 0], gy[0, 0])
        np.testing.assert_array_equal(h[0, 1], 0)

    def test_fft_matches_independent_dense_linear_solve(self):
        # 独立按像素索引构造矩阵，避免用待测差分函数生成“标准答案”。
        height, width = 3, 5
        n = height * width
        dx, dy = np.zeros((n, n)), np.zeros((n, n))
        for row in range(height):
            for col in range(width):
                p = row * width + col
                dx[p, p] -= 1
                dx[p, row * width + (col + 1) % width] += 1
                dy[p, p] -= 1
                dy[p, ((row + 1) % height) * width + col] += 1
        rng = np.random.default_rng(19)
        source, h, v = rng.random((3, height, width, 3))
        beta = 3.7
        matrix = np.eye(n) + beta * (dx.T @ dx + dy.T @ dy)
        rhs = source.reshape(n, 3) + beta * (dx.T @ h.reshape(n, 3) + dy.T @ v.reshape(n, 3))
        expected = np.linalg.solve(matrix, rhs).reshape(height, width, 3)
        actual = fft_update(np.fft.fft2(source, axes=(0, 1)), h, v, beta,
                            difference_spectrum(height, width))
        np.testing.assert_allclose(actual, expected, atol=1e-12)

    def test_constant_and_degenerate_sizes(self):
        for shape in [(7, 11), (7, 11, 3), (1, 9), (8, 1), (1, 1)]:
            with self.subTest(shape=shape):
                np.testing.assert_allclose(smooth(np.full(shape, .37)).image, .37, atol=1e-12)

    def test_shape_mean_reproducibility_and_input_unchanged(self):
        source = np.random.default_rng(3).random((9, 13, 3))
        before = source.copy()
        first, second = smooth(source), smooth(source)
        self.assertEqual(first.image.shape, source.shape)
        np.testing.assert_array_equal(source, before)
        np.testing.assert_array_equal(first.image, second.image)
        np.testing.assert_allclose(first.image.mean((0, 1)), source.mean((0, 1)), atol=1e-12)
        self.assertEqual(first.iterations, 22)

    def test_texture_suppression_and_main_edge(self):
        y, x = np.indices((32, 48))
        source = np.where(x < 24, .25, .75) + .02 * (-1.) ** (x + y)
        output = smooth(source).image
        self.assertLess(output[4:-4, 4:20].std(), source[4:-4, 4:20].std() * .2)
        self.assertGreater(output[:, 28:44].mean() - output[:, 4:20].mean(), .4)

    def test_invalid_inputs_and_parameters(self):
        for bad in [np.empty((0, 4)), np.zeros((2, 3, 4)), [[np.nan]], [[2.]], [[1j]]]:
            with self.subTest(input=repr(bad)), self.assertRaises(ValueError):
                smooth(bad)
        for kwargs in [dict(lambda_=0), dict(lambda_=-1), dict(lambda_=np.inf),
                       dict(kappa=1), dict(kappa=np.nan), dict(beta_max=.01)]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                smooth(np.zeros((2, 3)), **kwargs)


if __name__ == '__main__':
    unittest.main()
