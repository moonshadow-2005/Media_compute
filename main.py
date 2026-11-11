"""L0 平滑命令行：读取图片、保存完整运行包，并按记录复现。"""

import argparse
import json
from pathlib import Path

import numpy as np

from image_io import environment, load_image, save_comparison, save_png, sha256, write_json
from l0_smoothing import smooth


def run_smoothing(input_path, output_dir, lambda_=0.02, kappa=2., beta_max=1e5):
    output_dir = Path(output_dir)
    # 不覆盖已有运行包，避免把输入或已有实验结果误写掉。
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f'输出目录非空，请使用新的目录：{output_dir}')
    source = load_image(input_path)
    result = smooth(source, lambda_=lambda_, kappa=kappa, beta_max=beta_max)
    output_dir.mkdir(parents=True, exist_ok=True)
    save_png(output_dir / 'input.png', source)
    save_png(output_dir / 'smoothed.png', result.image)
    np.save(output_dir / 'smoothed.npy', result.image, allow_pickle=False)
    save_comparison(output_dir / 'comparison.png', [('Input', source), ('L0 smoothed', result.image)])
    record = {
        'schema_version': 1,
        'input': 'input.png',
        'input_sha256': sha256(output_dir / 'input.png'),
        'source_filename': Path(input_path).name,
        'shape': list(source.shape),
        'parameters': {'lambda_': result.lambda_, 'kappa': result.kappa, 'beta_max': result.beta_max},
        'iterations': result.iterations,
        'elapsed_seconds': result.elapsed_seconds,
        'environment': environment(),
        'preprocessing': 'EXIF orientation; alpha over white; 8-bit L/RGB divided by 255; periodic boundary',
        'float_output': 'smoothed.npy',
        'display_output': 'smoothed.png',
        'display_sha256': sha256(output_dir / 'smoothed.png'),
    }
    write_json(output_dir / 'run.json', record)
    return record


def replay(record_path, output_dir):
    record_path = Path(record_path)
    record = json.loads(record_path.read_text(encoding='utf-8'))
    source = record_path.parent / record['input']
    if sha256(source) != record['input_sha256']:
        raise ValueError('输入图像 SHA256 与运行记录不一致，拒绝使用被修改的输入复现')
    rerun = run_smoothing(source, output_dir, **record['parameters'])
    matches = rerun['display_sha256'] == record['display_sha256']
    write_json(Path(output_dir) / 'replay_check.json', {
        'reference_display_sha256': record['display_sha256'],
        'actual_display_sha256': rerun['display_sha256'],
        'display_bytes_match': matches,
        'same_environment': rerun['environment'] == record['environment'],
    })
    if not matches:
        raise ValueError('复现输出与记录不同，检查 replay_check.json 和依赖版本')
    return rerun


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('smooth', help='载入灰度/彩色图片并保存运行包')
    run.add_argument('input', type=Path)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--lambda', dest='lambda_', type=float, default=.02)
    run.add_argument('--kappa', type=float, default=2.)
    run.add_argument('--beta-max', type=float, default=1e5)
    repeat = commands.add_parser('replay', help='使用运行包中的输入和参数重新运行')
    repeat.add_argument('record', type=Path)
    repeat.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'smooth':
            result = run_smoothing(args.input, args.output, args.lambda_, args.kappa, args.beta_max)
        else:
            result = replay(args.record, args.output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'错误：{error}\n')
    print(f"完成：{result['iterations']} 次迭代，{result['elapsed_seconds']:.3f} 秒；结果：{args.output}")


if __name__ == '__main__':
    main()
