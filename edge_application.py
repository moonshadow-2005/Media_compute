"""在原图和平滑图上使用完全相同的 Canny 参数。"""

from pathlib import Path

import cv2
import numpy as np

from image_io import load_image, save_comparison, save_png, to_uint8, write_json


def canny(image, low=20., high=40.):
    if not np.isfinite([low, high]).all() or not 0 <= low < high:
        raise ValueError('Canny 阈值必须有限并满足 0 <= low < high')
    pixels = to_uint8(image)
    gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY) if pixels.ndim == 3 else pixels
    return cv2.Canny(gray, low, high, apertureSize=3, L2gradient=True) != 0


def contour_measures(edges, reference):
    """以干净插画的 Canny 为参考，允许一像素偏移；不是人工标注真值。"""
    kernel = np.ones((3, 3), dtype=np.uint8)
    near_reference = cv2.dilate(reference.astype(np.uint8), kernel) != 0
    near_edges = cv2.dilate(edges.astype(np.uint8), kernel) != 0
    reference_count = int(reference.sum())
    return {
        'edge_pixels': int(edges.sum()),
        'pixels_away_from_reference': int((edges & ~near_reference).sum()),
        'reference_coverage_within_1px': float((reference & near_edges).sum() / reference_count) if reference_count else None,
    }


def add_edges(output_dir, low=20., high=40., clean_reference=None):
    output_dir = Path(output_dir)
    source = load_image(output_dir / 'input.png')
    smoothed = load_image(output_dir / 'smoothed.png')
    before, after = canny(source, low, high), canny(smoothed, low, high)
    save_png(output_dir / 'edges_input.png', before)
    save_png(output_dir / 'edges_smoothed.png', after)
    save_comparison(output_dir / 'edges_comparison.png', [
        ('Input', source), ('L0 smoothed', smoothed),
        ('Canny input', before), ('Canny smoothed', after)])
    record = {
        'detector': 'OpenCV Canny', 'opencv': cv2.__version__,
        'shared_parameters': {'low': low, 'high': high, 'apertureSize': 3, 'L2gradient': True},
        'preprocessing': 'same 8-bit quantization; RGB to grayscale; no additional blur',
        'input_edge_pixels': int(before.sum()), 'smoothed_edge_pixels': int(after.sum()),
    }
    if clean_reference is not None:
        clean = load_image(clean_reference)
        if clean.shape != source.shape:
            raise ValueError('干净参考图必须与输入尺寸和通道一致')
        reference_edges = canny(clean, low, high)
        save_png(output_dir / 'reference_clean.png', clean)
        save_png(output_dir / 'edges_reference.png', reference_edges)
        record['reference_note'] = '干净人工插画的同参数 Canny，容忍 1 像素；不是人工标注边缘真值。'
        record['input_vs_reference'] = contour_measures(before, reference_edges)
        record['smoothed_vs_reference'] = contour_measures(after, reference_edges)
    write_json(output_dir / 'edges.json', record)
    return record
