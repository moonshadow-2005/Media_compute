import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from image_io import load_image
from main import replay, run_smoothing


@pytest.mark.parametrize('mode', ['L', 'RGB'])
def test_cli_image_roundtrip_and_replay(tmp_path, mode):
    source = tmp_path / '中文输入.png'
    shape = (12, 19) if mode == 'L' else (12, 19, 3)
    pixels = np.random.default_rng(6).integers(0, 256, shape, dtype=np.uint8)
    Image.fromarray(pixels).save(source)
    output = tmp_path / '首次结果'
    command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'main.py')]
    subprocess.run(command + ['smooth', str(source), '--output', str(output),
                             '--lambda', '0.01', '--kappa', '1.5'], check=True)
    record = json.loads((output / 'run.json').read_text())
    assert record['shape'] == list(shape)
    assert record['parameters']['kappa'] == 1.5
    assert np.load(output / 'smoothed.npy').shape == shape
    source.unlink()  # 运行包不依赖原始文件路径，移动目录后仍可复现。
    moved = tmp_path / '移动后的运行包'
    output.rename(moved)
    subprocess.run(command + ['replay', str(moved / 'run.json'), '--output', str(tmp_path / 'replay')], check=True)
    assert (moved / 'smoothed.png').read_bytes() == (tmp_path / 'replay/smoothed.png').read_bytes()


def test_replay_rejects_changed_input_and_run_refuses_overwrite(tmp_path):
    source = tmp_path / 'input.png'
    Image.new('L', (12, 13), 100).save(source)
    output = tmp_path / 'run'
    run_smoothing(source, output)
    with pytest.raises(ValueError, match='非空'):
        run_smoothing(source, output)
    Image.new('L', (12, 13), 200).save(output / 'input.png')
    with pytest.raises(ValueError, match='SHA256'):
        replay(output / 'run.json', tmp_path / 'replay')


def test_transparency_on_white_and_high_bit_depth_rejection(tmp_path):
    source = tmp_path / 'alpha.png'
    Image.new('RGBA', (2, 3), (255, 0, 0, 0)).save(source)
    np.testing.assert_array_equal(load_image(source), np.ones((3, 2, 3)))
    Image.fromarray(np.ones((2, 3), dtype=np.uint16)).save(source)
    with pytest.raises(ValueError, match='高位深'):
        load_image(source)
