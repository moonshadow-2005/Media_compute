# 边缘提取与 JPEG 去伪影公开样例

这些是外部公开素材，未由本项目生成。下载文件保持原始字节，URL、尺寸、来源与 SHA256 见 [sources.json](sources.json)。

| 样例 | 来源 | 本项目用法 |
|---|---|---|
| 象群 `253036.jpg` | L0 作者的边缘处理示例页 | 原图和平滑图分别做同参数 Canny |
| 停车标志 `stop.png` | L0 作者的边缘处理示例页 | 观察背景纹理与主轮廓 |
| 西瓜 `9.jpg`、蜗牛 `20.jpg` | L0 作者的 Clip-art JPEG 示例页 | 直接恢复已有压缩图，旁边展示作者公开恢复结果 |
| 黑白马 `horse.png` | Andreas Preuss (marauder) / Openclipart，经 scikit-image v0.25.2 收录，CC0 | 从参考 PNG 生成 JPEG，再计算相对该 PNG 的 PSNR／SSIM |

- [作者边缘示例](https://jiaya.me/file/archive/projects/L0smoothing/EdgeEnhancement.htm)展示的是梯度图；本页面的 Canny 二值边缘不能与其当作同一结果逐像素核对。
- [作者 JPEG 示例](https://jiaya.me/file/archive/projects/L0smoothing/ClipArt.htm)提供压缩输入与恢复结果，没有在该展示页给出对应压缩前原图及逐图恢复参数。作者恢复图仅供观察，不作为真值或“相同参数复现”标准。
- [公开马剪贴画说明](https://scikit-image.org/docs/0.25.x/api/skimage.data.html#skimage.data.horse)注明 CC0 许可；PNG 是本项目再次压缩实验的参考。

作者项目图片未单独注明摄影者或图片授权许可，本项目保留来源，不标为原创或 CC0。作者代码未引入。

切换到边缘提取时默认选象群；切换 JPEG 时默认选西瓜。西瓜与蜗牛自动走“直接恢复已有压缩图”，质量控件禁用，不进行第二次 JPEG 编码，也不计算缺少真值的 PSNR／SSIM。
选择马剪贴画或其他参考图，可选择“从参考图生成 JPEG”并调节质量；上传已有 JPEG 也可手动选择“直接恢复已有压缩图”。

## 其他团队与基准

[Berkeley 分割数据集与边缘检测基准](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/segbench/)提供人工标注和算法比较，另有扩展版 BSDS500。
正式评测应遵循其划分、标注匹配和评测协议；本项目目前仅做同参数 Canny 的图像对照，没有宣称取得 BSDS 基准分数。

[Harvard CS205 团队的 L0 实现](https://github.com/ideafisher/l0-smoothing)可查看另一团队的串行／并行复现。
上述参考链接也放在 Streamlit 页面的“公开示例与其他实现”中。
