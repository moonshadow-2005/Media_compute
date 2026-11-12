# L0 梯度最小化课程大作业

作者／提交者：蒋天乐。按要求逐项开发，每个阶段验证后提交。

## 环境与运行

已验证环境：Python 3.10.12，依赖见 `requirements.txt`。

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 experiment_smoothing.py
```

`l0_smoothing.smooth(image, lambda_=0.02, kappa=2.0, beta_max=1e5)`
接收 `[0,1]` 灰度或 RGB 数组，返回浮点图像、参数、迭代次数和耗时。
核心算法仅使用 NumPy 数组运算及 FFT，自行实现周期差分、彩色联合阈值和交替优化。
不在迭代中裁剪结果；图像保存时才裁剪到显示值域。

算法依据：课程要求文档中给出的 L0 目标函数与半二次分裂公式；
Li Xu 等，*Image Smoothing via L0 Gradient Minimization*，2011，
https://doi.org/10.1145/2024156.2024208 。

## 逐项进度

- [x] 4.1.1 结构平滑与参数控制：核心算法、三组插画、三档 lambda 和两档 kappa 实验已完成。
- [x] 4.1.2 完整程序与结果复现：8 位灰度／彩色图片载入、保存及运行包复现。
- [x] 4.1.3 边缘提取应用：相同参数处理原图与平滑图。
- [ ] 4.2.1 Clip-art JPEG 伪影处理。
- [ ] 4.2.2 PSNR／SSIM 和局部结果比较。
- [ ] 课程报告：原理、运行说明、实验分析、参考来源。
- [ ] Demo 与课堂展示材料；现场展示由本人完成。

## 第一项实验

输入与来源见 `data/illustrations/README.md`，输出与分析见 `results/structure_smoothing/`。
默认生成 18 组平滑结果、3 张参数对照图，以及 `config.json` 和 `metrics.csv`。
可通过 `--lambdas 0.005 0.02 0.08 --kappas 1.5 2 --beta-max 100000` 改变参数。
实验脚本应在本目录运行，重复执行会更新对应实验产物。

## 过程记录

`AI_LOG.md` 保存 Agent 使用与核验情况，`COMMIT_LOG.md` 保存每次提交的完整 hash 和内容。
两者均按本人要求仅保存在本地，通过 `.gitignore` 排除，每次提交后立即更新。
最终交付时需要单独附上，Git 克隆不会取得这两个本地文件。早期提交中的历史版本仍保留。

## 图片平滑与复现

```bash
python3 main.py smooth data/illustrations/color_landscape_input.png --output results/my_run --lambda 0.02 --kappa 2 --beta-max 100000
python3 main.py replay results/my_run/run.json --output results/my_replay
```

输出目录须为空或尚不存在。运行包包括预处理后的输入 PNG、平滑 PNG、原始浮点 NPY、
对照图和 `run.json`。复现根据相对路径读取输入，并检查输入及输出 SHA256。
输入按 EXIF 方向旋转，透明像素合成白底，再转换为 8 位灰度/RGB 的 [0,1] 浮点数组；
高位深／浮点图片要求先自行转换，以免无提示地截断数值。
依赖版本不同可能导致浮点数或 PNG 编码差异，复现检查会报告差异。

## 边缘提取

```bash
python3 main.py edges data/illustrations/color_landscape_input.png --output results/my_edges --lambda 0.02 --low 20 --high 40
python3 experiment_edges.py --output results/edges_rerun
```

对原图和平滑图统一做 8 位量化、RGB 转灰度，使用相同 Canny 阈值、3×3 Sobel 和 L2 梯度，
不额外添加预模糊。保存两幅边缘图、四面板对照图和 `edges.json`。
默认实验结果见 `results/edges/`，分析见该目录的 `ANALYSIS.md`。
