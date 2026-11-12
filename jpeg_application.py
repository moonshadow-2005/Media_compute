"""生成 Clip-art JPEG 伪影并用自实现 L0 平滑恢复。"""

import argparse
from pathlib import Path

from PIL import Image

from image_io import environment, load_image, save_comparison, save_png, sha256, to_uint8, write_json
from l0_smoothing import smooth


def restore_jpeg(clean_path, output_dir, quality=10, lambdas=(.001, .003, .01, .03),
                 kappa=2., beta_max=1e5, crop=None):
    if not isinstance(quality, int) or not 1 <= quality <= 95:
        raise ValueError('JPEG quality 必须是 1 到 95 的整数')
    if not lambdas or len(set(lambdas)) != len(lambdas):
        raise ValueError('至少指定一个 lambda，且不能重复')
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f'输出目录非空：{output_dir}')
    clean = load_image(clean_path)
    height, width = clean.shape[:2]
    if crop is None:
        crop = (width//4, height//4, 3*width//4, 3*height//4)
    x0, y0, x1, y1 = crop
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise ValueError('局部裁剪框必须在图像范围内')
    output_dir.mkdir(parents=True, exist_ok=True)
    save_png(output_dir / 'clean.png', clean)
    Image.fromarray(to_uint8(clean)).save(output_dir / 'compressed.jpg', quality=quality,
                                        subsampling=0, optimize=False, progressive=False)
    compressed = load_image(output_dir / 'compressed.jpg')
    save_png(output_dir / 'compressed.png', compressed)
    panels = [('Clean', clean), (f'JPEG Q={quality}', compressed)]
    runs = []
    for lam in lambdas:
        result = smooth(compressed, lambda_=lam, kappa=kappa, beta_max=beta_max)
        filename = f'restored_lambda_{lam:g}.png'
        save_png(output_dir / filename, result.image)
        # 对照图与指标都读取最终保存的 PNG，避免浮点/量化统计混用。
        panels.append((f'L0 lambda={lam:g}', load_image(output_dir / filename)))
        runs.append({'lambda_': result.lambda_, 'kappa': result.kappa, 'beta_max': result.beta_max,
                     'iterations': result.iterations, 'elapsed_seconds': result.elapsed_seconds,
                     'output': filename, 'output_sha256': sha256(output_dir / filename)})
    save_comparison(output_dir / 'comparison.png', panels)
    save_comparison(output_dir / 'crop_comparison.png',
                    [(name, array[y0:y1, x0:x1]) for name, array in panels], scale=3)
    record = {
        'source_filename': Path(clean_path).name, 'quality': quality, 'subsampling': 0,
        'jpeg_options': {'optimize': False, 'progressive': False},
        'clean_sha256': sha256(output_dir / 'clean.png'),
        'compressed_sha256': sha256(output_dir / 'compressed.jpg'),
        'crop_xyxy': list(crop), 'environment': environment(), 'runs': runs,
        'note': '恢复只读取解码后的 JPEG；干净图用于生成压缩输入及事后比较，不参与 L0 优化。',
    }
    write_json(output_dir / 'jpeg_run.json', record)
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('clean', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--quality', type=int, default=10)
    parser.add_argument('--lambdas', type=float, nargs='+', default=[.001, .003, .01, .03])
    parser.add_argument('--kappa', type=float, default=2.)
    parser.add_argument('--beta-max', type=float, default=1e5)
    parser.add_argument('--crop', type=int, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'))
    args = parser.parse_args(argv)
    try:
        restore_jpeg(args.clean, args.output, args.quality, args.lambdas, args.kappa, args.beta_max, args.crop)
    except (ValueError, OSError) as error:
        parser.exit(2, f'错误：{error}\n')
    print(f'JPEG 压缩与恢复结果已保存：{args.output}')


if __name__ == '__main__':
    main()
