"""三组输入的边缘提取对照；参数对两幅图完全一致。"""

import argparse
from pathlib import Path

from edge_application import add_edges
from image_io import write_json
from main import run_smoothing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/edges'))
    args = parser.parse_args()
    summaries = []
    for name in ['gray_step', 'color_landscape', 'color_shapes']:
        output = args.output / name
        run_smoothing(f'data/illustrations/{name}_input.png', output, lambda_=.02)
        record = add_edges(output, low=20., high=40., clean_reference=f'data/illustrations/{name}_clean.png')
        summaries.append({'image': name, **record})
    write_json(args.output / 'summary.json', summaries)
    print(f'已保存三组同参数边缘对照：{args.output}')


if __name__ == '__main__':
    main()
