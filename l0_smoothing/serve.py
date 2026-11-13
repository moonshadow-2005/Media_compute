"""启动本机 Streamlit Demo。"""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8501)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('端口应在 1 到 65535 之间')
    if importlib.util.find_spec('streamlit') is None:
        parser.exit(2, '请先运行 python3 -m pip install -r requirements.txt\n')
    project = Path(__file__).resolve().parents[1]
    command = [sys.executable, '-m', 'streamlit', 'run', str(project/'l0_smoothing/streamlit_app.py'),
               '--server.address', '127.0.0.1', '--server.port', str(args.port),
               '--server.headless', 'true', '--browser.gatherUsageStats', 'false',
               '--server.maxUploadSize', '8', '--server.fileWatcherType', 'none']
    print(f'Streamlit Demo：http://localhost:{args.port}；保持终端运行，Ctrl+C 停止。', flush=True)
    try:
        completed = subprocess.run(command, cwd=project)
    except KeyboardInterrupt:
        return
    if completed.returncode:
        parser.exit(completed.returncode, 'Streamlit 启动失败，请查看上方错误。\n')


if __name__ == '__main__':
    main()
