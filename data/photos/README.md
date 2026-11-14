# 真实摄影样例

五张图片来自 scikit-image v0.25.2 收录的实拍样例，均不是本项目生成的图片。
下载后原样保存，SHA256 与该版本上游 `_registry.py` 的记录逐一核对一致。
图片已随仓库提供，运行时无需联网，也无需安装 scikit-image。

| 文件 | 摄影者／来源 | 许可 | 可以观察的内容 |
|---|---|---|---|
| coffee.png | Rachel Michetti / Pikolo Espresso Bar | CC0 | 杯沿与木纹 |
| chelsea.png | Stefan van der Walt | CC0 | 毛发、眼睛与胡须 |
| astronaut.png | NASA | 公共领域 | 面部、服装与轮廓 |
| camera.png | Lav Varshney | CC0 | 灰度人物与三脚架 |
| rocket.jpg | SpaceX | 公共领域 | 天空、烟雾与塔架 |

来源与许可依据：[scikit-image 官方数据说明](https://scikit-image.org/docs/0.25.x/api/skimage.data.html)。
各图片的下载 URL、说明页、尺寸、SHA256 与下载时间保存在 [sources.json](sources.json)。
使用的是该数据集提供的尺寸，不声称它们是相机原始文件；`rocket.jpg` 本身已经过 JPEG 编码。

启动 `python3 main.py serve` 后，可在结构平滑模式的内置样例中选择这五张真实照片；列表最前面另提供论文作者的海滩与岩石样例。
结构平滑模式提供这些照片，下载的参数记录也会保留来源信息。其他模式的列表只展示对应任务样例，仍支持上传自己的图片。
JPEG 模式以所选照片为参考，再施加一次压缩；指标衡量相对该参考的误差，不能解释为恢复了拍摄现场的无损真值。
真实纹理可能随平滑一起消失，PSNR／SSIM 不保证改善。

原有人工插画仍用于可控纹理实验和课程要求中的 Clip-art 对照；旧离线 HTML 展示仍对应原实验结果，真实照片在 Streamlit 中现场计算。
