"""干净彩色卡通和灰度线条图的 JPEG 伪影实验。"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from l0_smoothing.jpeg import restore_jpeg


def make_line_art(path):
    image = Image.new('L', (192, 128), 242)
    draw = ImageDraw.Draw(image)
    draw.rectangle((14, 52, 76, 112), fill=205, outline=25, width=3)
    draw.polygon([(8, 54), (45, 15), (82, 54)], fill=110, outline=25)
    draw.rectangle((26, 68, 43, 86), fill=242, outline=25, width=2)
    draw.rectangle((50, 76, 66, 112), fill=100, outline=25, width=2)
    draw.ellipse((105, 18, 170, 83), fill=175, outline=25, width=3)
    for index, thickness in enumerate([1, 2, 3]):
        draw.line((100, 95+index*9, 178, 87+index*9), fill=40, width=thickness)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('results/jpeg'))
    args = parser.parse_args()
    line_path = Path('data/clipart/line_art_clean.png')
    make_line_art(line_path)
    cases = [('color_landscape', Path('data/illustrations/color_landscape_clean.png'), (85, 40, 149, 104)),
             ('line_art', line_path, (100, 65, 180, 121))]
    for name, clean, crop in cases:
        for quality in [10, 30]:
            restore_jpeg(clean, args.output / name / f'q{quality}', quality=quality, crop=crop)
    print(f'已保存两组干净图、两档 JPEG 质量和四档 lambda 的恢复结果：{args.output}')


if __name__ == '__main__':
    main()
