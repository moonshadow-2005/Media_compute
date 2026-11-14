import io
import json
import zipfile

import numpy as np
import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

from l0_smoothing.core import smooth
from l0_smoothing.image_io import load_image, to_uint8
from l0_smoothing.interactive import DEFAULT_SAMPLE, PHOTO_SOURCES, PROJECT, compute
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
    app.slider(key='low').set_value(100).run()
    assert app.error and not app.exception
    assert 'low < high' in app.error[0].value
    app.slider(key='high').set_value(150).run()
    assert not app.error and not app.exception
    assert app.session_state['result']['metadata']['canny']['high'] == 150
    app.selectbox(key='mode').set_value('JPEG 去伪影').run()
    app.slider(key='quality').set_value(30).run()
    app.slider(key='lambda_').set_value(.01).run()
    record = app.session_state['result']['metadata']
    assert not app.exception and record['jpeg']['quality'] == 30
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
    assert record['preprocessing']['processed_size'] == [36, 24]
    assert app.selectbox(key='sample').disabled
    app.slider(key='lambda_').set_value(.03).run()
    assert app.session_state['result']['metadata']['preprocessing']['source'] == '上传图片'
    app.file_uploader(key='upload').clear().run()
    assert not app.exception and not app.selectbox(key='sample').disabled
    preprocessing = app.session_state['result']['metadata']['preprocessing']
    assert preprocessing['source'] == PHOTO_SOURCES[DEFAULT_SAMPLE]['label']
    assert preprocessing['attribution']['sha256'] == PHOTO_SOURCES[DEFAULT_SAMPLE]['sha256']


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
