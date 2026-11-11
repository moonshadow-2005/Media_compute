"""按课程公式实现 L0 梯度最小化；空间轴为 (行, 列)，通道轴为最后一维。"""

from dataclasses import dataclass
from time import perf_counter

import numpy as np


@dataclass(frozen=True)
class SmoothingResult:
    image: np.ndarray
    lambda_: float
    kappa: float
    beta_max: float
    iterations: int
    elapsed_seconds: float


def periodic_gradient(image):
    """前向差分 Dx、Dy，最后一列/行与第一列/行连接。"""
    return (np.roll(image, -1, axis=1) - image,
            np.roll(image, -1, axis=0) - image)


def gradient_adjoint(h, v):
    """Dx* h + Dy* v；负散度，符号与前向差分严格配对。"""
    return np.roll(h, 1, axis=1) - h + np.roll(v, 1, axis=0) - v


def joint_threshold(gx, gy, threshold):
    """两个方向、全部颜色通道联合计数；等于阈值时置零。"""
    energy = np.sum(gx * gx + gy * gy, axis=-1, keepdims=True)
    keep = energy > threshold
    return np.where(keep, gx, 0.0), np.where(keep, gy, 0.0)


def difference_spectrum(height, width):
    """周期差分 Dx*Dx + Dy*Dy 的特征值，与 FFT 的排列一致。"""
    x = 4.0 * np.sin(np.pi * np.fft.fftfreq(width)) ** 2
    y = 4.0 * np.sin(np.pi * np.fft.fftfreq(height)) ** 2
    return (y[:, None] + x[None, :])[..., None]


def fft_update(input_fft, h, v, beta, spectrum):
    """固定 h、v 的二次子问题；FFT(差分伴随)等价于共轭频率响应乘积。"""
    numerator = input_fft + beta * np.fft.fft2(gradient_adjoint(h, v), axes=(0, 1))
    return np.fft.ifft2(numerator / (1.0 + beta * spectrum), axes=(0, 1)).real


def smooth(image, lambda_=0.02, kappa=2.0, beta_max=1e5):
    """平滑 [0,1] 灰度 (H,W) 或 RGB (H,W,3) 数组，返回结果和运行记录。

    不在优化循环内裁剪，以免改变二次子问题。输出可能略超出 [0,1]，
    保存显示图像时再裁剪。输入不会被原地修改。
    """
    start = perf_counter()
    raw = np.asarray(image)
    if raw.ndim not in (2, 3) or (raw.ndim == 3 and raw.shape[2] != 3):
        raise ValueError('输入必须为 (H,W) 灰度或 (H,W,3) RGB 数组')
    if raw.size == 0 or not np.issubdtype(raw.dtype, np.number) or np.iscomplexobj(raw):
        raise ValueError('输入必须是非空实数数组')
    source = np.array(raw, dtype=np.float64, copy=True)
    if not np.isfinite(source).all() or source.min() < 0 or source.max() > 1:
        raise ValueError('输入必须为有限值，并预先归一化到 [0,1]')
    if not np.isfinite(lambda_) or lambda_ <= 0:
        raise ValueError('lambda_ 必须为有限正数')
    if not np.isfinite(kappa) or kappa <= 1:
        raise ValueError('kappa 必须为有限数且大于 1')
    if not np.isfinite(beta_max) or beta_max <= 2 * lambda_:
        raise ValueError('beta_max 必须为有限数且大于初始 beta=2*lambda_')
    gray = source.ndim == 2
    if gray:
        source = source[..., None]
    current = source.copy()
    input_fft = np.fft.fft2(source, axes=(0, 1))
    spectrum = difference_spectrum(*source.shape[:2])
    beta = 2.0 * lambda_
    iterations = 0
    while beta < beta_max:
        gx, gy = periodic_gradient(current)
        h, v = joint_threshold(gx, gy, lambda_ / beta)
        current = fft_update(input_fft, h, v, beta, spectrum)
        beta *= kappa
        iterations += 1
    output = current[..., 0] if gray else current
    return SmoothingResult(output, float(lambda_), float(kappa), float(beta_max),
                           iterations, perf_counter() - start)
