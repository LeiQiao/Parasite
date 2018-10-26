import click
from termcolor import cprint
import os
import git
import re
import ast
from .download_source import pa_root, download_parasite, download_plugin
import sys
import tempfile


@click.group()
def main():
    """parasite 启动命令行管理工具"""

    pass


@main.command()
def update():
    """更新插件包"""
    # 创建插件包的管理路径
    clone = not os.path.exists(os.path.join(pa_root, '.git'))
    os.makedirs(pa_root, exist_ok=True)

    # 从 git 上更新所有插件包描述
    print('正在从 matser 中更新插件包 ...')
    if clone:
        git.Repo.clone_from(url='https://github.com/LeiQiao/Parasite-Repo.git', to_path=pa_root)
    else:
        result = git.Git(pa_root).checkout()
        print(result)

    cprint('更新成功', 'blue')


# noinspection PyShadowingBuiltins
@main.command()
@click.argument('plugin_name', required=False, default='')
def search(plugin_name):
    """查找插件包"""
    if len(plugin_name) == 0:
        cprint('usage: {0} search plugin_name'.format(sys.argv[0]), 'red')
        sys.exit(1)

    if not os.path.exists(pa_root):
        cprint('请先更新插件库后搜索', 'red')
        sys.exit(1)

    str_search_result = ''

    plugins = os.listdir(pa_root)
    for full_plugin_name in plugins:
        if re.match(plugin_name, full_plugin_name):
            versions = os.listdir(os.path.join(pa_root, full_plugin_name))
            versions.sort(reverse=True)
            if len(versions) == 0:
                continue

            manifest = os.path.join(pa_root, full_plugin_name, versions[0], '__manifest__.py')
            try:
                with open(manifest) as f:
                    manifest = ast.literal_eval(f.read())
            except Exception as e:
                str(e)
                continue
            str_search_result += '\033[32m-> {0} ({1})\033[0m\n'.format(full_plugin_name, versions[0])
            str_search_result += '\t{0}\n'.format(manifest['description'])
            str_search_result += '\t- Homepage: {0}\n'.format(manifest['website'])
            if 'git' in manifest['source']:
                str_search_result += '\t- Source:   {0}\n'.format(manifest['source']['git'])
            elif 'svn' in manifest['source']:
                str_search_result += '\t- Source:   {0}\n'.format(manifest['source']['svn'])
            elif isinstance(manifest['source'], str):
                str_search_result += '\t- Source:   {0}\n'.format(manifest['source'])
            str_search_result += '\t- Versions: {0}\n'.format(', '.join(versions))
            str_search_result += '\n'

    cprint(str_search_result)


@main.command()
@click.argument('project_name', required=True, default='')
@click.argument('plugin_name', required=False, default='')
@click.option('--output', default='./')
def install(project_name, plugin_name, output):
    """创建工程，安装必要的插件"""
    if len(project_name) == 0 or len(plugin_name) == 0:
        cprint('usage: {0} install <project_name> <plugin name>[, <plugin name>[, <plugin name>[...]]] '
               '[--output=<output dir>]'.format(sys.argv[0]), 'red')
        sys.exit(1)

    project_path = os.path.join(output, project_name)

    if os.path.exists(project_path):
        cprint('fatal: destination path \'{0}\' already exists and is not an empty directory.'
               .format(project_name), 'red')
        sys.exit(1)

    download_parasite(project_path)

    plugins = plugin_name.split(',')
    with tempfile.TemporaryDirectory() as temp_path:
        for plugin in plugins:
            try:
                download_plugin(pa_root, plugin, temp_path, project_path)
            except Exception as e:
                cprint(str(e), 'red')
                sys.exit(1)

    cprint('创建成功', 'blue')


if __name__ == '__main__':
    main()
