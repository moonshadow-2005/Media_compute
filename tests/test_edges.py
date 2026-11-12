import numpy as np
import pytest
from PIL import Image

from edge_application import add_edges, canny, contour_measures
from main import run_smoothing


def test_same_detector_and_major_contour_retention(tmp_path):
    y, x = np.indices((48, 80))
    clean = np.where(x < 40, .25, .75)
    source = np.clip(clean + .025*np.cos(np.pi*x/2)*np.cos(np.pi*y/2), 0, 1)
    input_path = tmp_path / 'input.png'
    Image.fromarray(np.rint(source*255).astype(np.uint8)).save(input_path)
    output = tmp_path / 'run'
    run_smoothing(input_path, output)
    record = add_edges(output)
    assert record['shared_parameters'] == dict(low=20., high=40., apertureSize=3, L2gradient=True)
    before = np.asarray(Image.open(output/'edges_input.png')) > 0
    after = np.asarray(Image.open(output/'edges_smoothed.png')) > 0
    assert before.sum() > after.sum()
    assert contour_measures(after, canny(clean))['reference_coverage_within_1px'] > .95
    with pytest.raises(ValueError):
        canny(source, low=100, high=20)


def test_no_contours_reference_is_explicit():
    assert contour_measures(np.zeros((5, 7), bool), np.zeros((5, 7), bool))['reference_coverage_within_1px'] is None
