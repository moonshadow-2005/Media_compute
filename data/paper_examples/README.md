# 论文作者公开样例与参考结果

来源：[Image Smoothing via L0 Gradient Minimization 项目](https://jiaya.me/file/archive/projects/L0smoothing/)，
[平滑结果页](https://jiaya.me/file/archive/projects/L0smoothing/ImageSmoothing.htm)。
论文作者：Li Xu、Cewu Lu、Yi Xu、Jiaya Jia，SIGGRAPH Asia 2011。

| 原图 | 作者参考结果 | 原始尺寸 |
|---|---|---|
| beach_input.png | beach_author.png | 800 × 533 |
| rock2_input.png | rock2_author.png | 876 × 584 |

这些 PNG 是项目网页公开文件的原始下载字节；没有生成、缩放、裁剪或改色。
完整下载 URL 与 SHA256 见 [sources.json](sources.json)。作者参考文件来自网页的 λ=0.020 列。
项目页没有单独标注这些照片的摄影者和图片授权许可，因此不将它们标为原创、CC0 或公共领域。
此处附来源用于课程复现与结果比较；作者 MATLAB 代码没有纳入本仓库。

Streamlit 默认选中海滩，也可切换岩石。两张论文样例在三种任务中均保留原尺寸；
用户上传的图片仍按最长边 768 缩小预览，避免大图影响交互响应。
结构平滑模式显示原图、本项目现场计算结果和作者固定参考；局部观察与下载包含三幅图。

核对配置为 λ=0.02、κ=2、β 最大值=100000：λ 来自结果页，κ 与 β 上限采用作者代码默认值。
当前两张图在该配置下的 8 位 RGB 输出与作者 PNG 逐像素相同。
页面按本次实际计算结果重新统计最大／平均像素差和不同像素数，不显示写死的通过结果。
改变参数后，作者参考保持固定；页面明确提示此时参数不同，差异不作为复现正确性的判断。
边缘提取及 JPEG 模式不把平滑参考冒充相应任务的官方结果。
