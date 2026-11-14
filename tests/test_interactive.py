import io
import json
import zipfile

import numpy as np
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from l0_smoothing.core import smooth
from l0_smoothing.image_io import load_image, to_uint8
from l0_smoothing.interactive import DEFAULT_SAMPLE, MODE_SAMPLES, PAPER_SOURCES, SOURCE_INFO, TASK_SOURCES, PROJECT, SAMPLES, compute
from l0_smoothing.streamlit_app import result_archive


def start_app():
    app = AppTest.from_file(str(PROJECT/'l0_smoothing/streamlit_app.py'), default_timeout=30).run()
    assert not app.exception
    return app


@pytest.mark.parametrize('mode', ['smooth', 'edges', 'jpeg'])
def test_live_compute_uses_requested_parameters(mode):
    result = compute(dict(mode=mode, sample='color_landscape', lambda_=.017, kappa=1.5))
    record = result['metadata']
    assert record['parameters'] == dict(lambda_=.017, kappa=1.5, beta_max=100000.)
    assert record['mode'] == mode
    assert record['iterations'] > 22 and record['algorithm_seconds'] > 0
    for item in result['panels']:
        with Image.open(io.BytesIO(item['image'])) as image:
            assert image.size == (192, 128)
    if mode == 'smooth':
        source = load_image(PROJECT/'data/illustrations/color_landscape_input.png')
        expected = smooth(source, lambda_=.017, kappa=1.5)
        actual = np.asarray(Image.open(io.BytesIO(result['panels'][1]['image'])))
        np.testing.assert_array_equal(actual, to_uint8(expected.image))


def test_parameter_changes_recompute_and_manual_mode_marks_old_result():
    app = start_app()
    first = app.session_state['result']['panels'][1]['image']
    app.slider(key='lambda_').set_value(.06).run()
    assert not app.exception
    assert app.session_state['compute_count'] == 2
    assert app.session_state['result']['panels'][1]['image'] != first
    app.slider(key='crop_x').set_value((10, 50)).run()
    assert app.session_state['compute_count'] == 2  # 局部查看不触发算法。
    app.checkbox(key='auto').uncheck().run()
    app.slider(key='lambda_').set_value(.03).run()
    assert app.warning and app.session_state['compute_count'] == 2
    assert app.session_state['result']['metadata']['parameters']['lambda_'] == .06
    app.button(key='run').click().run()
    assert not app.exception and not app.warning
    assert app.session_state['compute_count'] == 3
    assert app.session_state['result']['metadata']['parameters']['lambda_'] == .03
    app.button(key='run').click().run()
    assert app.session_state['compute_count'] == 4  # 同参数也可以显式重算。


def test_streamlit_switches_modes_and_validates_canny():
    app = start_app()
    app.selectbox(key='mode').set_value('边缘提取').run()
    assert app.session_state['result']['metadata']['mode'] == 'edges'
    assert 'author_reference' not in app.session_state['result']['metadata']
    app.slider(key='low').set_value(100).run()
    assert app.error and not app.exception
    assert 'low < high' in app.error[0].value
    app.slider(key='high').set_value(150).run()
    assert not app.error and not app.exception
    assert app.session_state['result']['metadata']['canny']['high'] == 150
    app.selectbox(key='mode').set_value('JPEG 去伪影').run()
    assert app.selectbox(key='sample').value == 'jpeg_9'
    assert app.slider(key='quality').disabled
    assert app.number_input(key='quality_input').disabled
    assert app.session_state['result']['metadata']['jpeg']['recompressed'] is False
    app.selectbox(key='sample').set_value('clipart_horse').run()
    app.slider(key='quality').set_value(30).run()
    app.slider(key='lambda_').set_value(.01).run()
    record = app.session_state['result']['metadata']
    assert not app.exception and record['jpeg']['quality'] == 30
    assert 'author_reference' not in record
    # 真实照片的细节可能被抹掉，不能把 PSNR 必然改善当作正确性要求。
    for values in record['metrics'].values():
        assert np.isfinite(values['psnr_db'])
        assert -1 <= values['ssim'] <= 1


def test_streamlit_upload_and_clear_input():
    app = start_app()
    stream = io.BytesIO()
    Image.new('L', (36, 24), 128).save(stream, format='PNG')
    app.file_uploader(key='upload').set_value(('灰度输入.png', stream.getvalue(), 'image/png')).run()
    assert not app.exception
    record = app.session_state['result']['metadata']
    assert record['preprocessing']['source'] == '上传图片'
    assert 'author_reference' not in record
    assert record['preprocessing']['processed_size'] == [36, 24]
    assert app.selectbox(key='sample').disabled
    app.slider(key='lambda_').set_value(.03).run()
    assert app.session_state['result']['metadata']['preprocessing']['source'] == '上传图片'
    app.file_uploader(key='upload').clear().run()
    assert not app.exception and not app.selectbox(key='sample').disabled
    preprocessing = app.session_state['result']['metadata']['preprocessing']
    assert preprocessing['source'] == SOURCE_INFO[DEFAULT_SAMPLE]['label']
    assert preprocessing['attribution']['sha256'] == SOURCE_INFO[DEFAULT_SAMPLE]['sha256']


@pytest.mark.parametrize('sample', list(PAPER_SOURCES))
def test_author_reference_matches_live_full_size_calculation(sample):
    result = compute({'sample': sample})
    record = result['metadata']
    assert record['preprocessing']['processed_size'] == PAPER_SOURCES[sample]['size']
    assert not record['preprocessing']['resized']
    reference = record['author_reference']
    assert reference['parameters_match']
    assert reference['max_abs_8bit'] == reference['different_pixels'] == 0
    changed = compute({'sample': sample, 'lambda_': .01})
    assert not changed['metadata']['author_reference']['parameters_match']
    assert changed['metadata']['author_reference']['different_pixels'] > 0
    assert changed['panels'][1]['image'] != result['panels'][1]['image']
    assert changed['panels'][2]['image'] == result['panels'][2]['image']
    with zipfile.ZipFile(io.BytesIO(result_archive(result))) as archive:
        assert archive.read('author_reference.png') == result['panels'][2]['image']
        assert json.loads(archive.read('parameters.json'))['author_reference'] == reference


def test_preview_resize_and_invalid_inputs():
    stream = io.BytesIO()
    Image.new('RGB', (1024, 64), (80, 100, 120)).save(stream, format='PNG')
    result = compute({}, stream.getvalue())
    assert result['metadata']['preprocessing']['original_size'] == [1024, 64]
    assert result['metadata']['preprocessing']['processed_size'] == [768, 48]
    assert result['metadata']['preprocessing']['resized']
    with pytest.raises(ValueError):
        compute({'kappa': 1})
    with pytest.raises(ValueError):
        compute({'lambda_': float('nan')})
    with pytest.raises(OSError):
        compute({}, b'not an image')


def test_download_contains_computed_images_and_finite_json():
    stream = io.BytesIO()
    Image.new('L', (24, 24), 128).save(stream, format='PNG')
    result = compute({'mode': 'jpeg'}, stream.getvalue())
    archive = result_archive(result)
    with zipfile.ZipFile(io.BytesIO(archive)) as opened:
        assert opened.testzip() is None
        record = json.loads(opened.read('parameters.json'))
        assert record['jpeg']['quality'] == 10
        assert record['metrics']['compressed']['psnr_db'] == 'Infinity'
        for item in result['panels']:
            assert opened.read(item['filename']) == item['image']


@pytest.mark.parametrize('sample', ['jpeg_9', 'jpeg_20'])
def test_existing_jpeg_is_not_recompressed_or_treated_as_ground_truth(sample):
    result = compute({'mode': 'jpeg', 'sample': sample, 'quality': 1, 'lambda_': .003})
    original = load_image(PROJECT/'data/task_examples'/TASK_SOURCES[sample]['file'])
    actual = np.asarray(Image.open(io.BytesIO(result['panels'][0]['image'])))
    np.testing.assert_array_equal(actual, to_uint8(original))
    assert result['metadata']['jpeg'] == dict(input_kind='existing', quality=None, recompressed=False)
    assert list(result['metadata']['metrics']) == ['note']
    assert 'author_reference' not in result['metadata']
    assert result['panels'][-1]['filename'] == 'author_restored.png'
    # 显式选择已有压缩图时，上传也直接恢复，不能沿用内置样例的作者参考。
    uploaded = compute({'mode': 'jpeg', 'sample': sample, 'jpeg_source': 'existing', 'lambda_': .003},
                       (PROJECT/'data/task_examples'/TASK_SOURCES[sample]['file']).read_bytes())
    assert len(uploaded['panels']) == 2
    np.testing.assert_array_equal(np.asarray(Image.open(io.BytesIO(uploaded['panels'][0]['image']))), actual)


def test_numeric_entry_syncs_slider_manual_calculation_and_crop():
    app = start_app()
    app.selectbox(key='sample').set_value('gray_step').run()
    app.checkbox(key='auto').uncheck().run()
    count = app.session_state['compute_count']
    app.number_input(key='lambda__input').set_value(.00317).run()
    assert not app.exception and app.slider(key='lambda_').value == .00317
    assert app.session_state['compute_count'] == count and app.warning
    app.number_input(key='kappa_input').set_value(1.85).run()
    assert app.slider(key='kappa').value == 1.85
    app.number_input(key='beta_max').set_value(10000.).run()
    app.button(key='run').click().run()
    assert app.session_state['result']['metadata']['parameters'] == dict(lambda_=.00317, kappa=1.85, beta_max=10000.)
    app.slider(key='lambda_').set_value(.02).run()
    assert app.number_input(key='lambda__input').value == .02
    count = app.session_state['compute_count']
    app.number_input(key='crop_x_start').set_value(10).run()
    assert app.slider(key='crop_x').value == (10, 75)
    app.slider(key='crop_y').set_value((20, 60)).run()
    assert app.number_input(key='crop_y_start').value == 20
    assert app.number_input(key='crop_y_end').value == 60
    assert app.session_state['compute_count'] == count


def test_numeric_canny_and_quality_inputs_reach_computation():
    app = start_app()
    app.selectbox(key='mode').set_value('边缘提取').run()
    assert app.selectbox(key='sample').value == 'edge_253036'
    app.number_input(key='low_input').set_value(100).run()
    assert app.error and not app.exception
    app.number_input(key='high_input').set_value(180).run()
    assert not app.error and not app.exception
    assert app.slider(key='high').value == 180
    assert app.session_state['result']['metadata']['canny']['low'] == 100
    app.selectbox(key='mode').set_value('JPEG 去伪影').run()
    app.selectbox(key='sample').set_value('clipart_horse').run()
    app.number_input(key='quality_input').set_value(17).run()
    assert not app.exception
    assert app.slider(key='quality').value == 17
    assert app.session_state['result']['metadata']['jpeg']['quality'] == 17
    assert 'compressed' in app.session_state['result']['metadata']['metrics']
    app.selectbox(key='jpeg_source').set_value('existing').run()
    assert app.number_input(key='quality_input').disabled
    assert app.session_state['result']['metadata']['jpeg']['recompressed'] is False


@pytest.mark.parametrize('sample', ['edge_253036', 'edge_stop'])
def test_edge_author_files_are_displayed_and_exported_without_recomputation(sample):
    result = compute({'mode': 'edges', 'sample': sample})
    assert len(result['author_panels']) == 3
    references = TASK_SOURCES[sample]['edge_references']
    assert result['metadata']['author_examples'] == references
    for item, reference in zip(result['author_panels'], references):
        expected = load_image(PROJECT/'data/task_examples'/reference['file'])
        actual = np.asarray(Image.open(io.BytesIO(item['image'])))
        np.testing.assert_array_equal(actual, to_uint8(expected))
    changed = compute({'mode': 'edges', 'sample': sample, 'lambda_': .01})
    assert changed['panels'][1]['image'] != result['panels'][1]['image']
    assert changed['author_panels'] == result['author_panels']
    with zipfile.ZipFile(io.BytesIO(result_archive(result))) as archive:
        for item in result['author_panels']:
            assert archive.read(item['filename']) == item['image']
    stream = io.BytesIO()
    Image.new('RGB', (24, 24), (80, 80, 80)).save(stream, format='PNG')
    uploaded = compute({'mode': 'edges', 'sample': sample}, stream.getvalue())
    assert not uploaded['author_panels']
    assert 'author_examples' not in uploaded['metadata']


def test_page_explicitly_labels_loaded_author_results():
    app = start_app()
    assert app.selectbox(key='sample').options == [SAMPLES[key][0] for key in MODE_SAMPLES['smooth']]
    app.selectbox(key='mode').set_value('边缘提取').run()
    assert app.selectbox(key='sample').options == [SAMPLES[key][0] for key in MODE_SAMPLES['edges']]
    assert not app.exception
    assert any('作者原有结果（官网图片）' in title.value for title in app.subheader)
    assert len(app.session_state['result']['author_panels']) == 3
    app.selectbox(key='mode').set_value('JPEG 去伪影').run()
    assert app.selectbox(key='sample').options == [SAMPLES[key][0] for key in MODE_SAMPLES['jpeg']]
    assert not app.exception
    assert any('我们的现场恢复 · 作者原有结果' in title.value for title in app.subheader)
    assert app.session_state['result']['panels'][2]['filename'] == 'author_restored.png'
    app.selectbox(key='mode').set_value('结构平滑').run()
    assert not app.exception and app.selectbox(key='sample').value == DEFAULT_SAMPLE
    assert app.selectbox(key='sample').options == [SAMPLES[key][0] for key in MODE_SAMPLES['smooth']]
    assert len(set(sum(MODE_SAMPLES.values(), []))) == sum(map(len, MODE_SAMPLES.values()))
