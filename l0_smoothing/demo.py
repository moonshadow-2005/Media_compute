"""生成可离线打开的算法展示；可选先重新计算全部实验。"""

import argparse
import base64
import csv
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def image_uri(path):
    return 'data:image/png;base64,' + base64.b64encode(Path(path).read_bytes()).decode('ascii')


def build_demo(results, output):
    results, output = Path(results), Path(output)
    structure = results / 'structure_smoothing'
    config = json.loads((structure / 'config.json').read_text(encoding='utf-8'))
    with (structure / 'metrics.csv').open(encoding='utf-8') as file:
        smooth_metrics = list(csv.DictReader(file))
    with (results / 'jpeg/metrics.csv').open(encoding='utf-8') as file:
        jpeg_metrics = list(csv.DictReader(file))
    data = {'smooth': [], 'edges': [], 'jpeg': []}
    for name, label in [('gray_step', '灰度阶跃'), ('color_landscape', '彩色风景'), ('color_shapes', '彩色几何')]:
        for kappa in config['kappas']:
            for lam in config['lambdas']:
                row = next(r for r in smooth_metrics if r['image'] == name and r['kind'] == 'smoothed'
                           and float(r['lambda_']) == lam and float(r['kappa']) == kappa)
                data['smooth'].append({'name': name, 'label': label, 'lambda': lam, 'kappa': kappa,
                    'input': image_uri(PROJECT / f'data/illustrations/{name}_input.png'),
                    'output': image_uri(structure / f'{name}_lambda_{lam:g}_kappa_{kappa:g}.png'),
                    'info': f"{row['iterations']} 次迭代 · {float(row['elapsed_seconds']):.4f} 秒 · 平坦区标准差 {float(row['flat_roi_std']):.6f}"})
        folder = results / 'edges' / name
        record = json.loads((folder / 'edges.json').read_text(encoding='utf-8'))
        data['edges'].append({'name': name, 'label': label, 'comparison': image_uri(folder / 'edges_comparison.png'),
            'info': f"Canny 20 / 40；边缘像素 {record['input_edge_pixels']} → {record['smoothed_edge_pixels']}；参考轮廓覆盖率 {record['smoothed_vs_reference']['reference_coverage_within_1px']:.0%}"})
    for name, label in [('color_landscape', '彩色风景'), ('line_art', '灰度线条')]:
        for quality in [10, 30]:
            folder = results / 'jpeg' / name / f'q{quality}'
            record = json.loads((folder / 'jpeg_run.json').read_text(encoding='utf-8'))
            baseline = next(r for r in jpeg_metrics if r['image'] == name and int(r['jpeg_quality']) == quality and r['kind'] == 'compressed')
            for run in record['runs']:
                lam = run['lambda_']
                row = next(r for r in jpeg_metrics if r['image'] == name and int(r['jpeg_quality']) == quality and r['kind'] == 'restored' and float(r['lambda_']) == lam)
                data['jpeg'].append({'name': name, 'label': label, 'quality': quality, 'lambda': lam,
                    'clean': image_uri(folder / 'clean.png'), 'compressed': image_uri(folder / 'compressed.png'),
                    'restored': image_uri(folder / run['output']), 'crop': image_uri(folder / 'crop_comparison.png'),
                    'info': f"PSNR {float(baseline['psnr_db']):.2f} → {float(row['psnr_db']):.2f} dB；SSIM {float(baseline['ssim']):.4f} → {float(row['ssim']):.4f}"})
    template = (Path(__file__).resolve().parent / 'templates/demo.html').read_text(encoding='utf-8')
    rendered = template.replace('__DEMO_DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding='utf-8')
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/demo'))
    parser.add_argument('--recompute', action='store_true', help='重新运行全部实验，再生成展示；输出 runs 目录必须不存在')
    args = parser.parse_args(argv)
    output = args.output.resolve()
    results = PROJECT / 'results'
    if args.recompute:
        results = output / 'runs'
        if results.exists():
            parser.error(f'复现实验目录已存在，请指定新的 --output：{results}')
        for module, name in [('experiments.smoothing', 'structure_smoothing'),
                             ('experiments.edges', 'edges'), ('experiments.jpeg', 'jpeg')]:
            subprocess.run([sys.executable, '-m', module, '--output', str(results / name)], cwd=PROJECT, check=True)
        subprocess.run([sys.executable, '-m', 'experiments.evaluate_jpeg', '--input', str(results / 'jpeg')], cwd=PROJECT, check=True)
    build_demo(results, output / 'index.html')
    print(f'离线展示已生成，双击或用浏览器打开：{output / "index.html"}')


if __name__ == '__main__':
    main()
