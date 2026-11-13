# JPEG 实验输入来源

`line_art_clean.png` 由 `experiments/jpeg.py` 中 `make_line_art()` 使用 Pillow 几何图形生成，
大小为 192×128、8 位灰度：房屋、圆形和三根宽度分别为 1、2、3 像素的斜线。
另一组使用 `../illustrations/color_landscape_clean.png`，为本项目原创彩色插画。
均不含外部素材，不使用随机过程。

JPEG 由 Pillow 编码，质量为 10 和 30，彩色图使用 4:4:4（subsampling=0），
禁用 optimize、progressive。压缩文件和解码 PNG 均随结果保存。
局部裁剪用于观察屋顶交界、圆轮廓和细线附近的振铃、块效应与细节损失，坐标见 `jpeg_run.json`。
