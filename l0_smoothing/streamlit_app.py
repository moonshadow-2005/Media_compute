"""Streamlit 交互页面；参数变化触发真实计算，下载和局部查看复用本次结果。"""

import hashlib
import io
import json
import zipfile

from PIL import Image
import streamlit as st

from l0_smoothing.interactive import SAMPLES, compute


def result_archive(result):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in result['panels']:
            archive.writestr(item['filename'], item['image'])
        archive.writestr('parameters.json', json.dumps(result['metadata'], ensure_ascii=False, indent=2, allow_nan=False))
    return buffer.getvalue()


def main():
    st.set_page_config(page_title='L0 结构平滑 · 现场计算', page_icon='🖼️', layout='wide')
    st.title('L0 梯度最小化 · 现场计算')
    st.caption('媒体计算第 4 题 · 蒋天乐 | 调整参数后重新运行 Python 算法')
    labels = {'结构平滑': 'smooth', '边缘提取': 'edges', 'JPEG 去伪影': 'jpeg'}
    with st.sidebar:
        st.header('输入与参数')
        mode = labels[st.selectbox('任务', list(labels), key='mode')]
        uploaded = st.file_uploader('上传自己的图片', type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'],
                                    max_upload_size=8, key='upload')
        sample = st.selectbox('内置样例', list(SAMPLES), format_func=lambda key: SAMPLES[key][0],
                              disabled=uploaded is not None, key='sample')
        st.caption('上传图片仅用于本次计算；最长边超过 768 像素会缩小预览，原文件不修改。')
        lam = st.slider('λ · 平滑强度', .0001, .1000, .0200, .0001, format='%.4f', key='lambda_',
                        help='增大通常去除更多细节，也可能改变小结构。')
        kappa = st.slider('κ · 惩罚增长率', 1.05, 4.00, 2.00, .05, key='kappa',
                          help='越接近 1，迭代越多，计算时间通常越长。')
        low, high, quality = 20, 40, 10
        if mode == 'edges':
            low = st.slider('Canny 低阈值', 0, 255, 20, key='low')
            high = st.slider('Canny 高阈值', 1, 255, 40, key='high')
            st.caption('原图与平滑图使用同一组检测参数。')
        elif mode == 'jpeg':
            quality = st.slider('JPEG 质量', 1, 95, 10, key='quality')
            st.caption('将选定图片当作参考，现场生成 JPEG，再执行恢复。')
        with st.expander('高级参数'):
            beta_max = st.number_input('β 最大值', 1.0, 100000.0, 100000.0, 1000.0, key='beta_max')
        auto = st.checkbox('参数变化后自动计算', value=True, key='auto')
        run = st.button('重新计算', type='primary', key='run')

    uploaded_bytes = uploaded.getvalue() if uploaded is not None else None
    payload = dict(mode=mode, sample=sample, lambda_=lam, kappa=kappa, beta_max=beta_max,
                   low=low, high=high, quality=quality)
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode() + (uploaded_bytes or b'')).hexdigest()
    changed = fingerprint != st.session_state.get('result_fingerprint')
    if run or (auto and changed):
        try:
            with st.spinner('正在运行 L0 梯度最小化…'):
                result = compute(payload, uploaded_bytes)
        except (ValueError, TypeError, OSError, Image.DecompressionBombError) as error:
            st.error(str(error))
            st.stop()
        st.session_state.result = result
        st.session_state.result_fingerprint = fingerprint
        st.session_state.compute_count = st.session_state.get('compute_count', 0) + 1
        changed = False
    if 'result' not in st.session_state:
        st.info('选择输入和参数后，点击侧栏“重新计算”。')
        st.stop()
    if changed:
        st.warning('参数已修改，下方仍是上次计算结果。点击“重新计算”应用新参数。')
    result = st.session_state.result
    record = result['metadata']
    preprocessing = record['preprocessing']
    columns = st.columns(4)
    columns[0].metric('迭代次数', record['iterations'])
    columns[1].metric('算法耗时', f"{record['algorithm_seconds']:.3f} s")
    columns[2].metric('λ', f"{record['parameters']['lambda_']:.4f}")
    columns[3].metric('κ', f"{record['parameters']['kappa']:.2f}")
    width, height = preprocessing['processed_size']
    st.caption(f"本次输入：{preprocessing['source']} · {width} × {height} · 实际计算次数：{st.session_state.compute_count}")
    if preprocessing['resized']:
        original_w, original_h = preprocessing['original_size']
        st.info(f'交互预览从 {original_w} × {original_h} 缩小至 {width} × {height}；全尺寸计算可使用命令行 smooth。')
    for column, item in zip(st.columns(len(result['panels'])), result['panels']):
        with column:
            st.subheader(item['title'])
            st.image(item['image'], width='stretch')

    metrics = record['metrics']
    if record['mode'] == 'edges':
        before, after = metrics['input_edge_pixels'], metrics['output_edge_pixels']
        st.metric('边缘像素数（原图 → 平滑后）', f'{before} → {after}')
    elif record['mode'] == 'jpeg':
        if 'note' in metrics:
            st.info(metrics['note'])
        else:
            rows = []
            for name, values in [('JPEG 输入', metrics['compressed']), ('L0 恢复', metrics['restored'])]:
                psnr = values['psnr_db']
                rows.append({'图像': name, 'PSNR / dB': '∞' if psnr == 'Infinity' else f'{psnr:.4f}', 'SSIM': f"{values['ssim']:.5f}"})
            st.table(rows)
    with st.expander('局部放大对照'):
        x_range = st.slider('横向范围（%）', 0, 100, (25, 75), key='crop_x')
        y_range = st.slider('纵向范围（%）', 0, 100, (25, 75), key='crop_y')
        box = (width*x_range[0]//100, height*y_range[0]//100, width*x_range[1]//100, height*y_range[1]//100)
        if box[0] < box[2] and box[1] < box[3]:
            for column, item in zip(st.columns(len(result['panels'])), result['panels']):
                with Image.open(io.BytesIO(item['image'])) as image:
                    column.image(image.crop(box), caption=item['title'], width='stretch')
        else:
            st.info('请选择非空的观察范围。')
    st.download_button('下载本次结果与参数', data=result_archive(result),
                       file_name=f"l0_{record['mode']}_result.zip", mime='application/zip', on_click='ignore')
    with st.expander('查看本次运行记录'):
        st.json(record)
    st.caption('这里的参数变化会触发真实计算。查看局部和下载复用本次结果，不会重复计算。')


if __name__ == '__main__':
    main()
