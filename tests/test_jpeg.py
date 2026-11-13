import numpy as np
import pytest
from PIL import Image

from l0_smoothing.image_io import load_image
from l0_smoothing.jpeg import restore_jpeg


def test_jpeg_pipeline_uses_real_compressed_input_and_records_parameters(tmp_path):
    y, x = np.indices((24, 32))
    pixels = np.where(y > x*.6 + 2, 220, 35).astype(np.uint8)
    clean = tmp_path / 'clean.png'
    Image.fromarray(pixels).save(clean)
    output = tmp_path / 'jpeg'
    record = restore_jpeg(clean, output, quality=10, lambdas=(.003, .03))
    assert (output / 'compressed.jpg').read_bytes()[:2] == b'\xff\xd8'
    assert not np.array_equal(load_image(clean), load_image(output / 'compressed.jpg'))
    assert record['quality'] == 10 and record['subsampling'] == 0
    assert [r['lambda_'] for r in record['runs']] == [.003, .03]
    for run in record['runs']:
        assert load_image(output / run['output']).shape == pixels.shape
        assert run['iterations'] > 0 and run['elapsed_seconds'] > 0
    assert (output / 'crop_comparison.png').exists()
    with pytest.raises(ValueError):
        restore_jpeg(clean, tmp_path/'bad', quality=0)
