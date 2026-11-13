"""PSNR 和高斯窗口 SSIM：显式定义值域、窗口与通道处理。"""

import cv2
import numpy as np


def measure_quality(reference, candidate):
    reference = np.asarray(reference, dtype=np.float64)
    candidate = np.asarray(candidate, dtype=np.float64)
    if reference.shape != candidate.shape or reference.ndim not in (2, 3):
        raise ValueError('两幅图像必须同尺寸，为灰度或 RGB')
    if reference.ndim == 3 and reference.shape[2] != 3:
        raise ValueError('彩色指标仅支持 RGB')
    if min(reference.shape[:2]) < 11:
        raise ValueError('SSIM 的 11×11 窗口要求图像宽高至少为 11')
    if not all(np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1 for a in [reference, candidate]):
        raise ValueError('指标输入必须为 [0,1] 的有限值')
    mse = float(np.mean((reference - candidate)**2))
    psnr = float('inf') if mse == 0 else float(-10*np.log10(mse))

    def gaussian(array):
        return cv2.GaussianBlur(array, (11, 11), 1.5, borderType=cv2.BORDER_REFLECT)

    mu_x, mu_y = gaussian(reference), gaussian(candidate)
    # 总体协方差；裁去 5 像素边缘，仅统计完整窗口。RGB 各通道独立计算后平均。
    var_x = gaussian(reference**2) - mu_x**2
    var_y = gaussian(candidate**2) - mu_y**2
    cov = gaussian(reference*candidate) - mu_x*mu_y
    c1, c2 = .01**2, .03**2
    ssim_map = ((2*mu_x*mu_y+c1)*(2*cov+c2)) / ((mu_x**2+mu_y**2+c1)*(var_x+var_y+c2))
    return {'psnr_db': psnr, 'ssim': float(ssim_map[5:-5, 5:-5].mean())}
