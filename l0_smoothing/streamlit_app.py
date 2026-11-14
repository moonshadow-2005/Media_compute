"""Streamlit 交互页面；参数变化触发真实计算，下载和局部查看复用本次结果。"""

import hashlib
import io
import json
import zipfile

from PIL import Image
import streamlit as st

from l0_smoothing.interactive import DEFAULT_SAMPLE, MODE_DEFAULTS, PAPER_SOURCES, SOURCE_INFO, TASK_SOURCES, SAMPLES, compute


PARAMETER_HELP = {
    'lambda_': (
        '控制保留原图与减少非零梯度之间的权衡。调大通常会去掉更多纹理、让平坦区域更连贯，'
        '但细线、弱边界和小结构也可能消失；调小更接近原图、保留更多细节，也会留下更多纹理或伪影。'
        '效果不保证随数值增大而变好。'
    ),
    'kappa': (
        '每轮迭代把内部惩罚参数 β 乘以 κ。调小、接近 1 时，更新更细、迭代更多、耗时通常更长；'
        '调大则迭代较少、通常更快，但求解路径和最终结果可能改变。它不是平滑强度，更多迭代也不保证效果更好；默认 2。'
    ),
    'low': (
        'Canny 的弱边缘下限：低于该阈值的梯度会被舍弃；介于低、高阈值之间的弱边缘，'
        '只有连接到强边缘时才会保留。调低可能连接更多细弱轮廓，也可能引入纹理边缘；'
        '调高会减少弱边缘，但可能使轮廓断开。必须小于高阈值，两幅图使用同一数值。'
    ),
    'high': (
        'Canny 判定强边缘的阈值。调高通常只留下更强的轮廓，弱轮廓可能漏检；'
        '调低会产生更多强边缘候选，能找出较弱结构，也可能带入更多杂乱边缘。'
        '必须大于低阈值，两幅图使用同一数值。'
    ),
    'quality': (
        '控制现场生成的 JPEG 输入质量，范围 1–95。调低会加强有损压缩，通常出现更多块效应、'
        '边缘振铃和颜色失真，恢复更困难；调高通常更接近参考图、伪影较少，但文件通常更大。'
        '这改变的是压缩输入，不是 L0 平滑强度，也不是保留信息的百分比。'
    ),
    'beta_max': (
        '交替优化的停止阈值。内部 β 用于约束图像梯度接近筛选后的辅助梯度，β 增长到此值后停止。'
        '调大通常会增加迭代和耗时，但不保证画质更好；调小会提早结束，结果可能还未稳定。'
        '通常保留默认 100000，主要通过 λ 控制平滑程度。'
    ),
    'crop_x': (
        '选择局部对照的左右边界，0% 是最左侧、100% 是最右侧。缩小两个端点的间距会显示更窄的区域，'
        '在同样显示宽度下细节更大；整体移动两个端点可观察其他位置。仅改变查看区域，不重新计算或修改输出图片。'
    ),
    'crop_y': (
        '选择局部对照的上下边界，0% 是顶部、100% 是底部。缩小两个端点的间距可聚焦更短的区域，'
        '整体移动两个端点可观察上方或下方。仅改变查看区域，不重新计算或修改输出图片。'
    ),
}


def result_archive(result):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for item in result['panels']:
            archive.writestr(item['filename'], item['image'])
        archive.writestr('parameters.json', json.dumps(result['metadata'], ensure_ascii=False, indent=2, allow_nan=False))
    return buffer.getvalue()


def sync_parameter(source, target):
    st.session_state[target] = st.session_state[source]


def select_task_example():
    st.session_state['sample'] = MODE_DEFAULTS[st.session_state['mode']]


def parameter_input(label, minimum, maximum, default, step, key, format=None, disabled=False):
    """滑块和数值框双向同步；回调在重新计算前更新共同参数。"""
    entry_key = key + '_input'
    st.session_state.setdefault(key, default)
    st.session_state.setdefault(entry_key, st.session_state[key])
    options = dict(min_value=minimum, max_value=maximum, step=step, help=PARAMETER_HELP[key], disabled=disabled)
    if format is not None:
        options['format'] = format
    st.slider(label, key=key, on_change=sync_parameter, args=(key, entry_key), **options)
    st.number_input(label + ' · 直接输入', key=entry_key,
                    on_change=sync_parameter, args=(entry_key, key), **options)
    return st.session_state[key]


def sync_crop(key, source):
    if source == 'slider':
        st.session_state[key + '_start'], st.session_state[key + '_end'] = st.session_state[key]
    else:
        start, end = st.session_state[key + '_start'], st.session_state[key + '_end']
        if start > end:
            if source == 'start':
                end = start
            else:
                start = end
        st.session_state[key + '_start'], st.session_state[key + '_end'] = start, end
        st.session_state[key] = (start, end)


def crop_input(label, key):
    st.session_state.setdefault(key, (25, 75))
    st.session_state.setdefault(key + '_start', st.session_state[key][0])
    st.session_state.setdefault(key + '_end', st.session_state[key][1])
    st.slider(label, 0, 100, key=key, on_change=sync_crop, args=(key, 'slider'), help=PARAMETER_HELP[key])
    for column, endpoint, suffix in zip(st.columns(2), ['start', 'end'], ['起点', '终点']):
        column.number_input(label + ' · ' + suffix, 0, 100, key=key + '_' + endpoint,
                            on_change=sync_crop, args=(key, endpoint), help=PARAMETER_HELP[key])
    return st.session_state[key]


def main():
    st.set_page_config(page_title='L0 结构平滑 · 现场计算', page_icon='🖼️', layout='wide')
    st.title('L0 梯度最小化 · 现场计算')
    st.caption('媒体计算第 4 题 · 蒋天乐 | 调整参数后重新运行 Python 算法')
    labels = {'结构平滑': 'smooth', '边缘提取': 'edges', 'JPEG 去伪影': 'jpeg'}
    with st.sidebar:
        st.header('输入与参数')
        st.caption('悬停参数旁的问号，可查看含义及调节后的预期变化。')
        st.caption('参数可拖动滑块，也可直接输入数字后按 Enter；两者同步。')
        mode = labels[st.selectbox('任务', list(labels), key='mode', on_change=select_task_example,
                                   help='切换任务会选中对应示例，已上传的图片仍优先。结构平滑对比原图与结果；边缘提取对比两路同参数 Canny；JPEG 可直接恢复已有压缩图，或从参考图生成压缩输入。')]
        uploaded = st.file_uploader('上传自己的图片', type=['png', 'jpg', 'jpeg', 'bmp', 'webp', 'tif', 'tiff'],
                                    max_upload_size=8, key='upload',
                                    help='上传后替代内置样例，清除上传文件后恢复样例。JPEG 模式会把上传图当作参考图，再进行一次 JPEG 压缩。最长边超过 768 像素会缩小预览，原文件不变。')
        st.session_state.setdefault('sample', DEFAULT_SAMPLE)
        sample = st.selectbox('内置样例', list(SAMPLES), format_func=lambda key: SAMPLES[key][0],
                              disabled=uploaded is not None, key='sample',
                              help='任务切换时会选中对应的公开示例。论文样例保留原尺寸；JPEG 压缩插画直接恢复，不再压缩。普通照片和人工插画也可用于生成压缩输入的定量实验。')
        if uploaded is None and sample in SOURCE_INFO:
            st.caption(SOURCE_INFO[sample]['note'])
        if uploaded is None and sample in PAPER_SOURCES:
            st.caption('论文样例按原尺寸计算；结构平滑模式同时显示作者 λ=0.02 的固定参考结果。')
        st.caption('上传图片仅用于本次计算；最长边超过 768 像素会缩小预览，原文件不修改。')
        lam = parameter_input('λ · 平滑强度', .00001, .20000, .02000, .00001, 'lambda_', '%.5f')
        kappa = parameter_input('κ · 惩罚增长率', 1.05, 4.00, 2.00, .01, 'kappa', '%.4f')
        low, high, quality, jpeg_source = 20, 40, 10, 'simulate'
        if mode == 'edges':
            low = parameter_input('Canny 低阈值', 0, 255, 20, 1, 'low')
            high = parameter_input('Canny 高阈值', 1, 255, 40, 1, 'high')
            st.caption('原图与平滑图使用同一组检测参数。')
        elif mode == 'jpeg':
            compressed_example = uploaded is None and TASK_SOURCES.get(sample, {}).get('kind') == 'jpeg_compressed'
            if compressed_example:
                jpeg_source = 'existing'
            else:
                jpeg_source = st.selectbox('JPEG 输入方式', ['simulate', 'existing'], key='jpeg_source',
                    format_func=lambda value: {'simulate': '从参考图生成 JPEG', 'existing': '直接恢复已有压缩图'}[value],
                    help='有参考图时可调节压缩质量并计算 PSNR／SSIM；已有压缩图直接进入恢复，不再次压缩，也不虚构参考原图。')
            quality = parameter_input('JPEG 质量', 1, 95, 10, 1, 'quality', disabled=jpeg_source == 'existing')
            if jpeg_source == 'existing':
                st.caption('直接恢复输入图，质量参数不适用。没有压缩前原图，因此不计算 PSNR／SSIM。')
            else:
                st.caption('将选定图片当作参考，现场生成 JPEG，再执行恢复。')
        with st.expander('高级参数'):
            beta_max = st.number_input('β 最大值', 1.0, 100000.0, 100000.0, 1000.0, key='beta_max',
                                        help=PARAMETER_HELP['beta_max'])
        auto = st.checkbox('参数变化后自动计算', value=True, key='auto',
                           help='勾选后，输入或算法参数变化即重新计算；取消后可先调整多个参数，再点击“重新计算”。关闭时下方保留上次结果，并提示参数尚未应用。')
        run = st.button('重新计算', type='primary', key='run',
                        help='用当前输入和参数实际运行一次算法；即使参数不变也会重跑，并更新本次耗时和运行记录。')

    uploaded_bytes = uploaded.getvalue() if uploaded is not None else None
    payload = dict(mode=mode, sample=sample, lambda_=lam, kappa=kappa, beta_max=beta_max,
                   low=low, high=high, quality=quality, jpeg_source=jpeg_source)
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
    columns[2].metric('λ', f"{record['parameters']['lambda_']:.5f}", help=PARAMETER_HELP['lambda_'])
    columns[3].metric('κ', f"{record['parameters']['kappa']:.4f}", help=PARAMETER_HELP['kappa'])
    width, height = preprocessing['processed_size']
    st.caption(f"本次输入：{preprocessing['source']} · {width} × {height} · 实际计算次数：{st.session_state.compute_count}")
    if 'attribution' in preprocessing:
        attribution = preprocessing['attribution']
        st.caption(f"图片来源：{attribution['author']} · {attribution['license']} · "
                   f"[来源说明]({attribution['documentation_url']})")
    if preprocessing['resized']:
        original_w, original_h = preprocessing['original_size']
        st.info(f'交互预览从 {original_w} × {original_h} 缩小至 {width} × {height}；全尺寸计算可使用命令行 smooth。')
    for column, item in zip(st.columns(len(result['panels'])), result['panels']):
        with column:
            st.subheader(item['title'])
            st.image(item['image'], width='stretch')

    if 'author_reference' in record:
        reference = record['author_reference']
        st.caption('作者参考固定为 λ=0.02；核对配置为 κ=2、β 最大值=100000。修改参数不会改变参考图。')
        if not reference['parameters_match']:
            st.info('当前参数与核对配置不同，以下差异仅供观察，不用于判定复现是否一致。')
        elif reference['different_pixels'] == 0:
            st.success('本次计算与作者公开结果逐像素完全一致。')
        else:
            st.warning('本次计算与作者公开结果存在像素差异，请查看差异数值。')
        comparison_columns = st.columns(3)
        comparison_columns[0].metric('最大像素差（0–255）', reference['max_abs_8bit'])
        comparison_columns[1].metric('平均像素差（0–255）', f"{reference['mean_abs_8bit']:.6f}")
        comparison_columns[2].metric('不同像素数', reference['different_pixels'])

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
        x_range = crop_input('横向范围（%）', 'crop_x')
        y_range = crop_input('纵向范围（%）', 'crop_y')
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
    with st.expander('公开示例与其他实现'):
        st.markdown('- [作者的边缘处理示例](https://jiaya.me/file/archive/projects/L0smoothing/EdgeEnhancement.htm)：展示梯度图，不等同于本页面的 Canny 二值边缘。\n'
                    '- [作者的 Clip-art JPEG 示例](https://jiaya.me/file/archive/projects/L0smoothing/ClipArt.htm)：压缩输入及恢复结果，未提供对应无损真值。\n'
                    '- [Berkeley 边缘检测数据集与评测](https://www2.eecs.berkeley.edu/Research/Projects/CS/vision/grouping/segbench/)：包含人工标注与其他算法的结果。\n'
                    '- [Harvard CS205 团队的 L0 复现](https://github.com/ideafisher/l0-smoothing)：另一团队的串行／并行实现与展示。')
    st.caption('这里的参数变化会触发真实计算。查看局部和下载复用本次结果，不会重复计算。')


if __name__ == '__main__':
    main()
