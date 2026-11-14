"""交互计算层：现场运行核心算法，作者参考仅用于显示与核验。"""

import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image, ImageOps

from .core import smooth
from .edges import canny
from .image_io import environment, load_image, to_uint8
from .metrics import measure_quality

PROJECT = Path(__file__).resolve().parents[1]
PHOTO_SOURCES = {
    item['key']: item
    for item in json.loads((PROJECT / 'data/photos/sources.json').read_text(encoding='utf-8'))['images']
}
PAPER_SOURCES = {
    item['key']: item
    for item in json.loads((PROJECT / 'data/paper_examples/sources.json').read_text(encoding='utf-8'))['images']
}
SOURCE_INFO = {**PAPER_SOURCES, **PHOTO_SOURCES}
DEFAULT_SAMPLE = 'paper_beach'
SAMPLES = {
    **{key: (item['label'], 'data/paper_examples/' + item['file'], 'data/paper_examples/' + item['file'])
       for key, item in PAPER_SOURCES.items()},
    **{key: (item['label'], 'data/photos/' + item['file'], 'data/photos/' + item['file'])
       for key, item in PHOTO_SOURCES.items()},
    'color_landscape': ('彩色风景', 'data/illustrations/color_landscape_input.png', 'data/illustrations/color_landscape_clean.png'),
    'gray_step': ('灰度阶跃', 'data/illustrations/gray_step_input.png', 'data/illustrations/gray_step_clean.png'),
    'color_shapes': ('彩色几何', 'data/illustrations/color_shapes_input.png', 'data/illustrations/color_shapes_clean.png'),
    'line_art': ('灰度线条', 'data/clipart/line_art_clean.png', 'data/clipart/line_art_clean.png'),
}
MAX_UPLOAD = 8 * 1024 * 1024
MAX_SIDE = 768


def number(payload, key, default, low, high):
    value = payload.get(key, default)
    if isinstance(value, bool):
        raise ValueError(f'{key} 必须为数值')
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{key} 必须为数值') from None
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{key} 必须在 {low:g} 到 {high:g} 之间')
    return value


def read_source(payload, mode, uploaded_bytes=None):
    sample = None
    if uploaded_bytes is not None:
        if not isinstance(uploaded_bytes, bytes):
            raise ValueError('上传内容必须是图片文件字节')
        if len(uploaded_bytes) > MAX_UPLOAD:
            raise ValueError('上传文件不能超过 8 MiB')
        stream = io.BytesIO(uploaded_bytes)
        label = '上传图片'
    else:
        sample = payload.get('sample', DEFAULT_SAMPLE)
        if sample not in SAMPLES:
            raise ValueError('请选择内置样例或上传图片')
        label, input_path, clean_path = SAMPLES[sample]
        stream = PROJECT / (clean_path if mode == 'jpeg' else input_path)
    with Image.open(stream) as original:
        if original.width * original.height > 16_000_000:
            raise ValueError('上传图片不能超过 1600 万像素')
        if original.mode in ('I', 'F') or original.mode.startswith('I;16'):
            raise ValueError('请使用 8 位灰度或彩色图片')
        oriented = ImageOps.exif_transpose(original)
        original_size = list(oriented.size)
        # 两张已知大小的论文样例保留原尺寸，才能与作者公开结果逐像素比较。
        if sample not in PAPER_SOURCES:
            oriented.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        if oriented.mode == 'CMYK':
            oriented = oriented.convert('RGB')
        normalized = io.BytesIO()
        oriented.save(normalized, format='PNG')
        normalized.seek(0)
        image = load_image(normalized)
    preprocessing = {'source': label, 'original_size': original_size,
                     'processed_size': [image.shape[1], image.shape[0]],
                     'resized': original_size != [image.shape[1], image.shape[0]]}
    if uploaded_bytes is None and sample in SOURCE_INFO:
        preprocessing['attribution'] = dict(SOURCE_INFO[sample])
    return image, preprocessing


def panel(title, array, filename):
    stream = io.BytesIO()
    Image.fromarray(to_uint8(array)).save(stream, format='PNG')
    return {'title': title, 'filename': filename,
            'image': stream.getvalue()}


def compute(payload, uploaded_bytes=None):
    start = perf_counter()
    if not isinstance(payload, dict):
        raise ValueError('计算参数格式无效')
    mode = payload.get('mode', 'smooth')
    if mode not in ('smooth', 'edges', 'jpeg'):
        raise ValueError('未知计算模式')
    lam = number(payload, 'lambda_', .02, 1e-5, .2)
    kappa = number(payload, 'kappa', 2., 1.05, 4.)
    beta_max = number(payload, 'beta_max', 1e5, 1., 1e5)
    low = number(payload, 'low', 20., 0., 1000.)
    high = number(payload, 'high', 40., 0., 1000.)
    if mode == 'edges' and low >= high:
        raise ValueError('Canny 需要 low < high')
    quality = number(payload, 'quality', 10, 1, 95)
    if quality != int(quality):
        raise ValueError('JPEG 质量必须是整数')
    source, preprocessing = read_source(payload, mode, uploaded_bytes)
    clean = source
    if mode == 'jpeg':
        encoded = io.BytesIO()
        Image.fromarray(to_uint8(clean)).save(encoded, format='JPEG', quality=int(quality),
                                            subsampling=0, optimize=False, progressive=False)
        encoded.seek(0)
        source = load_image(encoded)
    result = smooth(source, lambda_=lam, kappa=kappa, beta_max=beta_max)
    displayed = to_uint8(result.image).astype(np.float64) / 255.
    panels = [panel('输入图', source, 'input.png'), panel('L0 平滑结果', displayed, 'smoothed.png')]
    metrics = {}
    reference_record = None
    if mode == 'smooth' and uploaded_bytes is None and payload.get('sample', DEFAULT_SAMPLE) in PAPER_SOURCES:
        reference = PAPER_SOURCES[payload.get('sample', DEFAULT_SAMPLE)]['reference']
        reference_image = load_image(PROJECT / 'data/paper_examples' / reference['file'])
        actual_pixels = to_uint8(displayed)
        reference_pixels = to_uint8(reference_image)
        if actual_pixels.shape != reference_pixels.shape:
            raise ValueError('作者参考图与当前计算结果尺寸不一致')
        difference = np.abs(actual_pixels.astype(np.int16) - reference_pixels.astype(np.int16))
        panels.append(panel('作者公开结果（固定 λ=0.02）', reference_image, 'author_reference.png'))
        reference_record = {
            **reference,
            'parameters_match': {'lambda_': lam, 'kappa': kappa, 'beta_max': beta_max} == reference['parameters'],
            'max_abs_8bit': int(difference.max()),
            'mean_abs_8bit': float(difference.mean()),
            'different_pixels': int(np.count_nonzero(np.any(difference != 0, axis=-1))),
        }
    if mode == 'edges':
        before, after = canny(source, low, high), canny(displayed, low, high)
        panels += [panel('原图边缘', before, 'edges_input.png'), panel('平滑后边缘', after, 'edges_smoothed.png')]
        metrics = {'input_edge_pixels': int(before.sum()), 'output_edge_pixels': int(after.sum())}
    elif mode == 'jpeg':
        panels = [panel('原图（压缩参考）', clean, 'clean.png'), panel('JPEG 压缩输入', source, 'compressed.png'),
                  panel('L0 恢复结果', displayed, 'restored.png')]
        if min(clean.shape[:2]) >= 11:
            metrics = {'compressed': measure_quality(clean, source), 'restored': measure_quality(clean, displayed)}
            # JSON 不支持 Infinity；无误差的 PSNR 用字符串记录。
            for values in metrics.values():
                if math.isinf(values['psnr_db']):
                    values['psnr_db'] = 'Infinity'
        else:
            metrics = {'note': '图片宽高不足 11 像素，未计算窗口 SSIM。'}
    metadata = {
        'mode': mode, 'parameters': {'lambda_': lam, 'kappa': kappa, 'beta_max': beta_max},
        'iterations': result.iterations, 'algorithm_seconds': result.elapsed_seconds,
        'total_seconds': perf_counter() - start, 'preprocessing': preprocessing,
        'environment': environment(), 'metrics': metrics,
        'computed_at': datetime.now(timezone.utc).isoformat(),
    }
    if mode == 'edges':
        metadata['canny'] = dict(low=low, high=high, apertureSize=3, L2gradient=True)
    if reference_record is not None:
        metadata['author_reference'] = reference_record
    if mode == 'jpeg':
        metadata['jpeg'] = dict(quality=int(quality), subsampling=0, optimize=False, progressive=False)
    return {'panels': panels, 'metadata': metadata}
