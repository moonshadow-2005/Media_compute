"""统一入口：图片平滑、参数复现、边缘提取、JPEG 去伪影与离线演示。"""

import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name, help_text in [
        ('smooth', '平滑灰度或彩色图片'), ('replay', '按运行包记录复现'),
        ('edges', '同参数 Canny 边缘对照'), ('jpeg', 'JPEG 压缩伪影处理'),
        ('demo', '生成离线展示，可选重算全部实验'),
    ]:
        commands.add_parser(name, help=help_text, add_help=False)
    args, remaining = parser.parse_known_args(argv)
    if args.command == 'jpeg':
        from l0_smoothing.jpeg import main as run
        run(remaining)
    elif args.command == 'demo':
        from l0_smoothing.demo import main as run
        run(remaining)
    else:
        from l0_smoothing.pipeline import main as run
        run([args.command, *remaining])


if __name__ == '__main__':
    main()
