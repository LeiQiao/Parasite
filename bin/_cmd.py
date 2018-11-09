import click
from termcolor import cprint
import os
import git
import re
import ast
from bin.download_source import pa_root, parasite_config_url
import sys
import requests


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
        result = git.Git(pa_root).pull()
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


INIT_FILE_CONTENT = """from .{0} import {1}
"""
MANIFEST_FILE_CONTENT = """# noinspection PyStatementEffect
{{
    'name': '{0}',
    'summary': '',
    'description': '',
    'author': '',
    'website': '',
    'source': {{'git': '', 'branch': ''}},

    'category': '',
    'version': '0.1',

    # any plugin necessary for this one to work correctly
    'depends': ['base']
}}
"""
PLUGIN_FILE_CONTENT = """from pa.plugin import Plugin


class {0}(Plugin):
    pass
"""
DEPLOY_FILE_CONTENT = """import click
from pa.bin import debug_plugin
from pa.bin import deploy_sh


@click.group()
def main():
    \"\"\"parasite 插件调试及部署工具\"\"\"
    pass


@main.command()
def debug():
    \"\"\"调试\"\"\"
    debug_plugin(
        # 插件所在的相对路径
        '../{0}/',
        # 数据库等配置信息
        '../deploy/config.conf'
    )


@main.command()
def build_deploy_sh():
    \"\"\"生成部署脚本\"\"\"
    deploy_sh(
        # 工程名称
        '{0}',
        # 需要部署的插件的 manifest 文件
        ['../{0}/__manifest__.py'],
        # 数据库等配置信息
        '../deploy/config.conf',
        # 需要拷贝的资源文件
        {{
            # '<resource file>': '<target path/>[target name]',
        }},
        # 部署脚本的输出位置
        output='../deploy/{0}.sh'
    )


if __name__ == '__main__':
    main()
"""


@main.command()
@click.argument('project_name', required=True, default='')
@click.argument('plugin_name', required=False, default='')
@click.option('--output', default='./')
def create(project_name, plugin_name, output):
    """创建工程，生成工程的目录及调试和部署文件"""
    if len(project_name) == 0 or len(plugin_name) == 0:
        cprint('usage: {0} install <project_name> <plugin name> '
               '[--output=<output dir>]'.format(sys.argv[0]), 'red')
        sys.exit(1)

    project_root = os.path.join(output, project_name)

    if os.path.exists(project_root):
        cprint('fatal: destination path \'{0}\' already exists and is not an empty directory.'
               .format(project_name), 'red')
        sys.exit(1)

    # 创建示例工程文件
    init_file_content = INIT_FILE_CONTENT.format(project_name, plugin_name)
    manifest_file_content = MANIFEST_FILE_CONTENT.format(project_name)
    plugin_file_content = PLUGIN_FILE_CONTENT.format(plugin_name)

    project_path = os.path.join(project_root, project_name)
    os.makedirs(project_path)
    with open(os.path.join(project_path, '__init__.py'), 'w') as f:
        f.write(init_file_content)
    with open(os.path.join(project_path, '__manifest__.py'), 'w') as f:
        f.write(manifest_file_content)
    with open(os.path.join(project_path, '{0}.py'.format(project_name)), 'w') as f:
        f.write(plugin_file_content)

    # 创建示例工程的部署和调试脚本
    deploy_file_content = DEPLOY_FILE_CONTENT.format(project_name)
    config_file_response = requests.get(parasite_config_url)
    if config_file_response.status_code != 200:
        cprint('创建失败，无法下载配置文件模板', 'red')
        sys.exit(1)
    config_file_content = config_file_response.text

    deploy_path = os.path.join(project_root, 'deploy')
    os.makedirs(deploy_path)
    with open(os.path.join(deploy_path, 'run.py'), 'w') as f:
        f.write(deploy_file_content)
    with open(os.path.join(deploy_path, 'config.conf'), 'w') as f:
        f.write(config_file_content)

    cprint('创建成功', 'blue')


if __name__ == '__main__':
    main()
