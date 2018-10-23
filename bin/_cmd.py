import click
from termcolor import cprint
import sys


@click.group()
def main():
    """parasite 启动命令行管理工具"""

    pass


@main.command()
@click.option('--quiet', '-q', is_flag=True, default=False)
def update(quiet):
    """更新插件包"""

    if not quiet:
        cprint('更新成功', 'blue')


# noinspection PyShadowingBuiltins
@main.command()
@click.argument('plugin_name', required=True, default='')
def search(plugin_name):
    """查找插件包"""

    cprint('搜索成功', 'blue')


if __name__ == '__main__':
    main()
