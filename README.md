# L0 梯度最小化课程大作业

作者／提交者：蒋天乐。按要求逐项开发，每个阶段验证后提交。

第 4 题基础与额外功能均已实现。报告见 `docs/REPORT.md`，7 分钟展示提纲见
`docs/PRESENTATION.md`，逐项验收见 `docs/REQUIREMENTS_CHECKLIST.md`。
可直接双击 `results/demo/index.html` 查看离线 Demo。
需要动态调整参数并现场计算时，运行 `python3 main.py serve` 启动 Streamlit。

## 目录导航

```text
大作业/
├── main.py                  # 唯一命令行入口
├── requirements.txt         # Python 依赖
├── l0_smoothing/            # 算法、图像处理及应用模块
│   ├── core.py              # 周期差分、联合阈值、FFT、交替优化
│   ├── pipeline.py          # 平滑运行包与复现
│   ├── image_io.py          # 图像读写、配置与对照图
│   ├── edges.py             # Canny 边缘对照
│   ├── jpeg.py              # JPEG 去伪影
│   ├── metrics.py           # PSNR、SSIM
│   ├── demo.py              # 离线展示生成
│   ├── interactive.py       # 交互计算与图片预处理
│   ├── streamlit_app.py     # Streamlit 参数、图像和指标页面
│   ├── serve.py             # 本地交互服务启动
│   └── templates/          # 展示页面模板
├── experiments/             # 平滑、边缘、JPEG 批量实验与评估
├── tests/                   # 数学、流程及展示验证
├── data/                    # 输入图片和来源说明
├── results/                 # 输出图片、运行配置、指标及离线 Demo
├── docs/                    # 课程要求、报告、展示提纲及验收
│   └── experiments/         # 三项实验的分析文档
├── AI_LOG.md                # 本地记录，不纳入 Git
└── COMMIT_LOG.md            # 本地提交说明，不纳入 Git
```

常用入口：`python3 main.py --help`。课程原始要求已移到
[docs/course_requirements.md](docs/course_requirements.md)。

## 环境与运行

已验证环境：Python 3.10.12，依赖见 `requirements.txt`。
建议 Python 3.10／3.11。Windows 下将命令中的 `python3` 替换为 `python`。
所有命令在“大作业”目录执行。安装依赖需要网络，算法运行与离线展示不需要网络。

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 -m experiments.smoothing
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
- [x] 4.2.1 Clip-art JPEG 伪影处理。
- [x] 4.2.2 PSNR／SSIM 和局部结果比较。
- [x] 课程报告：原理、运行说明、实验分析、参考来源。
- [x] 算法展示 Demo：离线参数切换和一键重算全部实验。
- [x] 课堂展示材料：7 分钟提纲与答辩准备；现场展示由本人完成。

## 第一项实验

输入与来源见 `data/illustrations/README.md`，输出见 `results/structure_smoothing/`。
参数分析见 [docs/experiments/structure_smoothing.md](docs/experiments/structure_smoothing.md)。
默认生成 18 组平滑结果、3 张参数对照图，以及 `config.json` 和 `metrics.csv`。
可通过 `--lambdas 0.005 0.02 0.08 --kappas 1.5 2 --beta-max 100000` 改变参数。
实验脚本应在本目录运行，重复执行会更新对应实验产物。

## 过程记录

`AI_LOG.md` 保存 Agent 使用与核验情况，`COMMIT_LOG.md` 保存每次提交的完整 hash 和内容。
两者均按本人要求仅保存在本地，通过 `.gitignore` 排除，每次提交后立即更新。
最终交付时需要单独附上，Git 克隆不会取得这两个本地文件；当前分支的全部历史快照已移除它们。
提交时间为按本人要求整理的展示时间，实际开发时间和新旧 hash 对照保存在本地日志中。

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
python3 -m experiments.edges --output results/edges_rerun
```

对原图和平滑图统一做 8 位量化、RGB 转灰度，使用相同 Canny 阈值、3×3 Sobel 和 L2 梯度，
不额外添加预模糊。保存两幅边缘图、四面板对照图和 `edges.json`。
默认实验结果见 `results/edges/`，分析见 [docs/experiments/edges.md](docs/experiments/edges.md)。

## Clip-art JPEG 去伪影

```bash
python3 main.py jpeg data/clipart/line_art_clean.png --output results/my_jpeg --quality 10 --lambdas 0.001 0.003 0.01 0.03
python3 -m experiments.jpeg --output results/jpeg_rerun
```

输出目录须为空。程序从干净图生成真实 JPEG，再解码并运行 L0 平滑，保存干净图、
JPEG 文件、解码 PNG、各参数恢复图、全图和局部对照、`jpeg_run.json`。
干净图不参与恢复优化。完整实验为两幅插画 × 两档压缩质量 × 四档 lambda。
参数记录包含质量、色度采样、lambda、kappa、beta_max、迭代次数、耗时与裁剪坐标。

```bash
python3 -m experiments.evaluate_jpeg
```

默认评估已有的 `results/jpeg`，可用 `--input results/jpeg_rerun` 指定复现实验。
相对干净图计算全部方法的全图和局部 PSNR／SSIM，指标定义见 `metric_definition.json`，
完整 24 条记录见 `metrics.csv`，分析见 `docs/experiments/jpeg.md`。

## Streamlit 现场计算 Demo（推荐课堂演示）

```bash
python3 -m pip install -r requirements.txt
python3 main.py serve
```

保持该终端运行，在浏览器打开 **http://localhost:8501**。WSL Bash 中可在另一个终端执行：

```bash
explorer.exe "http://localhost:8501"
```

按 `Ctrl+C` 停止服务；端口占用时用 `python3 main.py serve --port 8502`，然后打开对应端口。
Streamlit 依赖固定为 1.57.0；页面、计算和图片处理都在本机进行，不需要云端部署。

- 侧栏选择结构平滑、边缘提取或 JPEG 去伪影，使用内置样例或上传图片。
- 拖动 λ、κ、Canny 阈值和 JPEG 质量后自动重新计算；可以关闭自动计算，改用“重新计算”按钮。
- 主区域显示本次结果、迭代次数、耗时和指标；参数改变但尚未手动计算时会明确提示旧结果。
- 支持局部放大及下载本次 PNG 和 `parameters.json` 的 ZIP。下载和查看局部不会重复计算。
- 上传限制为 8 MiB、1600 万像素，预览最长边缩至 768 像素；页面显示缩放前后尺寸。原图不修改，全尺寸运行仍可用 `main.py smooth`。

交互计算没有使用缓存结果图片。自动计算仅在输入或算法参数变化时执行；“重新计算”可强制重跑相同参数。
下载的 `parameters.json` 是交互记录，区别于命令行运行包供 `replay` 使用的 `run.json`。

## 离线结果展示

直接用浏览器打开 `results/demo/index.html`，可以离线切换输入、lambda、kappa、JPEG 质量，
查看平滑、边缘、恢复局部和实际指标。页面显示已保存实验结果。

```bash
python3 main.py demo
python3 main.py demo --recompute --output results/live_demo
```

第一条重新生成离线页面；第二条实际运行所有实验及指标评估后生成页面，输出目录下的
`runs` 必须不存在。重算结果位于 `results/live_demo/runs`，不覆盖原有实验。
测试中对完整独立重跑的 77 张图逐像素核对一致，两份指标 CSV 排除耗时后也完全一致。
Demo 图片和指标绑定已通过 Node 执行页面脚本检查 37 组参数选择；未将该检查等同于浏览器截图验收。
Streamlit 交互通过官方 AppTest 验证参数变化、手动计算、三种任务、图片上传与清除，并实际启动服务检查健康状态和主页；当前共 26 项测试通过。
