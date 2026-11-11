"""统一读写、显示量化和运行记录，避免实验与命令行使用不同预处理。"""

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, __version__ as pillow_version


def load_image(path):
    """EXIF 旋转后读取 8 位灰度/RGB；透明图片先合成到白底。"""
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened)
        if image.mode in ('I', 'F') or image.mode.startswith('I;16'):
            raise ValueError('请先将高位深或浮点图片转换为 8 位灰度/RGB 图像')
        if 'A' in image.getbands() or 'transparency' in image.info:
            rgba = image.convert('RGBA')
            background = Image.new('RGBA', image.size, 'white')
            image = Image.alpha_composite(background, rgba).convert('RGB')
        else:
            image = image.convert('L' if image.mode in ('1', 'L') else 'RGB')
        return np.asarray(image, dtype=np.float64) / 255.0


def to_uint8(array):
    return np.rint(np.clip(array, 0, 1) * 255).astype(np.uint8)


def save_png(path, array):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(to_uint8(array)).save(path, format='PNG')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, content):
    Path(path).write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def environment():
    return {'python': platform.python_version(), 'numpy': np.__version__, 'pillow': pillow_version}


def save_comparison(path, panels, scale=1):
    """等尺寸图像横向比较；标题用 ASCII 以免依赖系统中文字体。"""
    from PIL import ImageDraw
    pictures = [(title, Image.fromarray(to_uint8(array)).convert('RGB')) for title, array in panels]
    width, height = pictures[0][1].size
    if any(pic.size != (width, height) for _, pic in pictures):
        raise ValueError('对照图各面板必须等尺寸')
    canvas = Image.new('RGB', (width * scale * len(pictures), height * scale + 28), 'white')
    draw = ImageDraw.Draw(canvas)
    for index, (title, picture) in enumerate(pictures):
        left = index * width * scale
        draw.text((left + 5, 8), title, fill='black')
        canvas.paste(picture.resize((width * scale, height * scale), Image.Resampling.NEAREST), (left, 28))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)
