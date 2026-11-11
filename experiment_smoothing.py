"""第 1 项要求：三组自制插画的 lambda/kappa 参数对照。"""

import argparse
import csv
import json
import platform
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, __version__ as pillow_version

from l0_smoothing import periodic_gradient, smooth


def make_illustrations():
    """确定性图案，无随机过程；平坦结构上叠加幅度为 0.025 的细纹理。"""
    y, x = np.indices((128, 192))
    texture = .025 * np.cos(np.pi * x / 2) * np.cos(np.pi * y / 2)

    gray = np.where(x < 96, .25, .75)

    landscape = np.empty((128, 192, 3))
    landscape[:] = [.30, .55, .80]
    landscape[(x - 150)**2 + (y - 30)**2 < 18**2] = [.95, .80, .25]
    landscape[y > 85 - .3 * x] = [.25, .60, .30]
    landscape[(x > 90) & (x < 140) & (y > 70) & (y < 115)] = [.80, .40, .25]
    landscape[(y > 42 + np.abs(x - 115)) & (y < 72)] = [.45, .25, .25]

    shapes = np.empty((128, 192, 3))
    shapes[:] = [.80, .82, .75]
    shapes[(x - 70)**2 + (y - 70)**2 < 26**2] = [.25, .45, .80]
    shapes[(x > 120) & (x < 170) & (y > 48) & (y < 108)] = [.80, .30, .35]
    shapes[(x > 112) & (x < 178) & (y > 20) & (y < 25)] = [.30, .65, .40]

    return {
        'gray_step': (gray, gray + texture),
        'color_landscape': (landscape, landscape + texture[..., None]),
        'color_shapes': (shapes, shapes + texture[..., None]),
    }


def to_pil(array):
    return Image.fromarray(np.rint(np.clip(array, 0, 1) * 255).astype(np.uint8))


def measures(array, clean):
    gx, gy = periodic_gradient(array)
    if array.ndim == 2:
        energy = gx**2 + gy**2
    else:
        energy = np.sum(gx**2 + gy**2, axis=-1)
    # 三幅插画左上角均为平坦区域；按通道去均值后衡量剩余纹理。
    roi = array[8:32, 8:32]
    roi_std = np.sqrt(np.mean((roi - roi.mean(axis=(0, 1)))**2))
    return {
        'flat_roi_std': float(roi_std),
        'mae_to_clean': float(np.mean(np.abs(array - clean))),
        'mean_gradient_magnitude': float(np.sqrt(energy).mean()),
        'gradient_fraction_gt_0.001': float(np.mean(np.sqrt(energy) > .001)),
        'raw_min': float(array.min()),
        'raw_max': float(array.max()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/structure_smoothing'))
    parser.add_argument('--lambdas', type=float, nargs='+', default=[.005, .02, .08])
    parser.add_argument('--kappas', type=float, nargs='+', default=[1.5, 2.])
    parser.add_argument('--beta-max', type=float, default=1e5)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sources = Path('data/illustrations')
    sources.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (clean, source) in make_illustrations().items():
        # 实验使用落盘 PNG 的实际像素，确保保存的输入能重现结果。
        to_pil(clean).save(sources / f'{name}_clean.png')
        to_pil(source).save(sources / f'{name}_input.png')
        with Image.open(sources / f'{name}_input.png') as loaded:
            source = np.asarray(loaded, dtype=np.float64) / 255.0
        with Image.open(sources / f'{name}_clean.png') as loaded:
            clean = np.asarray(loaded, dtype=np.float64) / 255.0
        baseline = measures(source, clean)
        rows.append(dict(image=name, kind='input', lambda_='', kappa='', beta_max='',
                         iterations=0, elapsed_seconds=0., **baseline))
        panel = Image.new('RGB', (192 * (len(args.lambdas) + 1), 158 * len(args.kappas)), 'white')
        draw = ImageDraw.Draw(panel)
        for row_index, kappa in enumerate(args.kappas):
            top = row_index * 158
            panel.paste(to_pil(source).convert('RGB'), (0, top + 30))
            draw.text((5, top + 8), f'Input ({name})', fill='black')
            for col_index, lam in enumerate(args.lambdas, start=1):
                result = smooth(source, lambda_=lam, kappa=kappa, beta_max=args.beta_max)
                filename = f'{name}_lambda_{lam:g}_kappa_{kappa:g}.png'
                rendered = to_pil(result.image)
                rendered.save(args.output / filename)
                panel.paste(rendered.convert('RGB'), (col_index * 192, top + 30))
                draw.text((col_index * 192 + 5, top + 8), f'lambda={lam:g}, kappa={kappa:g}', fill='black')
                rows.append(dict(image=name, kind='smoothed', lambda_=lam, kappa=kappa,
                                 beta_max=args.beta_max, iterations=result.iterations,
                                 elapsed_seconds=result.elapsed_seconds,
                                 **measures(result.image, clean)))
        panel.save(args.output / f'{name}_comparison.png')
    with (args.output / 'metrics.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    metadata = dict(lambdas=args.lambdas, kappas=args.kappas, beta_max=args.beta_max,
                    python=platform.python_version(), numpy=np.__version__, pillow=pillow_version,
                    input_dir=str(sources), random_seed=None,
                    input_source='本项目用 NumPy 几何图案生成的三幅原创插画；无外部图片。',
                    metrics_domain='平滑结果采用裁剪前的浮点值；PNG 显示结果裁剪到 [0,1]。')
    (args.output / 'config.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'已保存 {len(rows) - 3} 组平滑结果、3 张对照图及运行记录：{args.output}')


if __name__ == '__main__':
    main()
