"""统一比较干净图、JPEG 与全部 L0 恢复结果，不自动挑选或隐去失败参数。"""

import argparse
import csv
import json
from pathlib import Path

import cv2

from l0_smoothing.image_io import load_image, sha256, write_json
from l0_smoothing.metrics import measure_quality


def evaluate(root):
    root = Path(root)
    rows = []
    records = sorted(root.glob('*/*/jpeg_run.json'))
    if not records:
        raise ValueError('未找到 JPEG 实验，请先运行 python3 -m experiments.jpeg')
    for record_path in records:
        folder = record_path.parent
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if sha256(folder / 'clean.png') != record['clean_sha256'] or sha256(folder / 'compressed.jpg') != record['compressed_sha256']:
            raise ValueError(f'输入图像与原实验 hash 不一致：{folder}')
        reference = load_image(folder / 'clean.png')
        x0, y0, x1, y1 = record['crop_xyxy']
        cases = [('clean', '', 'clean.png'), ('compressed', '', 'compressed.jpg')]
        for run in record['runs']:
            if sha256(folder / run['output']) != run['output_sha256']:
                raise ValueError(f'恢复图与原实验 hash 不一致：{folder / run["output"]}')
            cases.append(('restored', run['lambda_'], run['output']))
        for kind, lam, filename in cases:
            candidate = load_image(folder / filename)
            full = measure_quality(reference, candidate)
            crop = measure_quality(reference[y0:y1, x0:x1], candidate[y0:y1, x0:x1])
            rows.append({'image': folder.parent.name, 'jpeg_quality': record['quality'],
                         'kind': kind, 'lambda_': lam, **full,
                         'crop_psnr_db': crop['psnr_db'], 'crop_ssim': crop['ssim']})
    with (root / 'metrics.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    write_json(root / 'metric_definition.json', {
        'data_range': 1, 'domain': 'saved 8-bit PNG/JPEG decoded to [0,1]',
        'PSNR': '-10*log10(mean((reference-candidate)^2)); clean identity is inf',
        'SSIM': {'window': [11, 11], 'gaussian_sigma': 1.5, 'K1': .01, 'K2': .03,
                 'covariance': 'population', 'border_crop': 5, 'channels': 'per-channel then mean'},
        'opencv': cv2.__version__, 'crop': 'jpeg_run.json crop_xyxy, identical for all methods',
    })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('results/jpeg'))
    args = parser.parse_args()
    rows = evaluate(args.input)
    print(f'已计算 {len(rows)} 组全图和局部 PSNR/SSIM：{args.input / "metrics.csv"}')


if __name__ == '__main__':
    main()
