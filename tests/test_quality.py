import numpy as np
import pytest

from l0_smoothing.metrics import measure_quality


def test_identity_and_constant_offset_analytic_values():
    source = np.full((13, 17), .4)
    identity = measure_quality(source, source)
    assert np.isinf(identity['psnr_db'])
    assert identity['ssim'] == pytest.approx(1.)
    result = measure_quality(source, np.full_like(source, .5))
    assert result['psnr_db'] == pytest.approx(20.)
    assert result['ssim'] == pytest.approx((2*.4*.5+.01**2)/(.4**2+.5**2+.01**2))


def test_rgb_ssim_matches_independent_weighted_patch_formula():
    # 11×11 输入恰好只有一个有效窗口，独立显式加权求和验证协方差和通道平均。
    rng = np.random.default_rng(42)
    a, b = rng.random((2, 11, 11, 3))
    y, x = np.mgrid[-5:6, -5:6]
    weights = np.exp(-(x*x+y*y)/(2*1.5**2))
    weights = (weights / weights.sum())[..., None]
    ma, mb = (a*weights).sum((0, 1)), (b*weights).sum((0, 1))
    va = ((a-ma)**2*weights).sum((0, 1))
    vb = ((b-mb)**2*weights).sum((0, 1))
    cov = ((a-ma)*(b-mb)*weights).sum((0, 1))
    expected = (((2*ma*mb+.0001)*(2*cov+.0009))/((ma*ma+mb*mb+.0001)*(va+vb+.0009))).mean()
    assert measure_quality(a,b)['ssim'] == pytest.approx(expected, abs=1e-12)
    with pytest.raises(ValueError):
        measure_quality(a[:5], b[:5])
