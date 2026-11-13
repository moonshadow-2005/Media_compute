import base64
import io
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from l0_smoothing.demo import PROJECT, build_demo


def test_offline_demo_images_and_every_parameter_selection(tmp_path):
    output = tmp_path / 'index.html'
    data = build_demo(PROJECT / 'results', output)
    assert [len(data[k]) for k in ['smooth', 'edges', 'jpeg']] == [18, 3, 16]
    for rows in data.values():
        for row in rows:
            for value in row.values():
                if isinstance(value, str) and value.startswith('data:image/png;base64,'):
                    Image.open(io.BytesIO(base64.b64decode(value.split(',', 1)[1]))).verify()
    html = output.read_text(encoding='utf-8')
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://', html)
    if not shutil.which('node'):
        pytest.skip('Node 不可用，已验证嵌入图像；交互绑定检查需要 Node')
    # 用最小 DOM 接口执行原始页面脚本，遍历每个选择，验证图片与数字确实切换。
    script = re.findall(r'<script>(.*?)</script>', html, flags=re.S)[0]
    test_js = r'''
const vm=require('node:vm');
const fs=require('node:fs');
const payload=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const nodes={};
const defaults={'smooth-name':'color_landscape','smooth-lambda':'0.02','smooth-kappa':'2','edge-name':'color_landscape','jpeg-name':'color_landscape','jpeg-quality':'10','jpeg-lambda':'0.01'};
const document={getElementById(id){return nodes[id]??=( {value:defaults[id],textContent:id==='demo-data'?JSON.stringify(payload.data):'',addEventListener(type,fn){this[type]=fn;}} );}};
vm.runInNewContext(payload.script,{document});
for(const row of payload.data.smooth){nodes['smooth-name'].value=row.name;nodes['smooth-lambda'].value=String(row.lambda);nodes['smooth-kappa'].value=String(row.kappa);nodes['smooth-name'].change();if(nodes['smooth-output'].src!==row.output||nodes['smooth-info'].textContent!==row.info)throw Error('平滑切换失败');}
for(const row of payload.data.edges){nodes['edge-name'].value=row.name;nodes['edge-name'].change();if(nodes['edge-comparison'].src!==row.comparison)throw Error('边缘切换失败');}
for(const row of payload.data.jpeg){nodes['jpeg-name'].value=row.name;nodes['jpeg-quality'].value=String(row.quality);nodes['jpeg-lambda'].value=String(row.lambda);nodes['jpeg-name'].change();if(nodes['jpeg-restored'].src!==row.restored||nodes['jpeg-info'].textContent!==row.info)throw Error('JPEG 切换失败');}
console.log('37 组参数选择均匹配对应图像和指标。');
'''
    (tmp_path / 'check.js').write_text(test_js, encoding='utf-8')
    (tmp_path / 'payload.json').write_text(json.dumps({'data': data, 'script': script}), encoding='utf-8')
    subprocess.run(['node', str(tmp_path / 'check.js'), str(tmp_path / 'payload.json')], check=True)
