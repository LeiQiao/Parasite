import ast
import os
import re
import sys

import click
import git
import requests
from termcolor import cprint

if __name__ == '__main__':
    from parasite.pa.bin.download_source import pa_root, parasite_config_url
    from parasite.pa.bin.pycharm_project import create_temp_project
else:
    from .download_source import pa_root, parasite_config_url
    from .pycharm_project import create_temp_project


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
        git.Repo.clone_from(url='git@172.31.13.131:parasite/Parasite-Repo.git', to_path=pa_root)
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
        if re.search(plugin_name, full_plugin_name):
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
    __pluginname__ = '{1}'
    pass
"""
DEPLOY_FILE_CONTENT = """import click
import sys
for path in sys.path:
    if path.endswith('.parasite'):
        sys.path.pop(sys.path.index(path))
        sys.path.append(path)
        break


@click.group()
def main():
    \"\"\"parasite 插件调试及部署工具\"\"\"
    pass


@main.command()
def debug():
    \"\"\"调试\"\"\"
    from pa.bin import debug_plugin
    debug_plugin(
        # 插件所在的相对路径
        '../{0}/',
        # 数据库等配置信息
        '../deploy/config.conf',
        # 与当前插件一起开发的本地插件所在的路径
        ['../']
    )


@main.command()
def build_deploy_sh():
    \"\"\"生成部署脚本\"\"\"
    from pa.bin import deploy_sh
    deploy_sh(
        # 工程名称
        '{0}',
        # 需要部署的插件的 manifest 文件
        ['../{0}/__manifest__.py'],
        # 数据库等配置信息
        '../deploy/config.conf',
        # 与当前插件一起开发的本地插件所在的路径
        ['../'],
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
@click.argument('plugin_name', required=True, default='')
@click.option('--output', default='./')
def create(project_name, plugin_name, output):
    """创建工程，生成工程的目录及调试和部署文件"""
    if len(project_name) == 0:
        cprint('usage: {0} create <project_name> [plugin name] '
               '[--output=<output dir>]'.format(sys.argv[0]), 'red')
        sys.exit(1)

    project_root = os.path.expanduser(os.path.join(output, project_name))

    if os.path.exists(project_root):
        cprint('fatal: destination path \'{0}\' already exists and is not an empty directory.'
               .format(project_name), 'red')
        sys.exit(1)

    if len(plugin_name) == 0:
        plugin_name = '{0}_plugin'.format(to_underscore(project_name))
        class_name = '{0}Plugin'.format(to_camel(project_name))
    else:
        class_name = to_camel(plugin_name)

    # 创建插件
    os.makedirs(project_root)
    create_plugin_at(plugin_name, class_name, project_root)

    # 创建示例工程的部署和调试脚本
    deploy_file_content = DEPLOY_FILE_CONTENT.format(plugin_name)
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

    # 创建 pycharm 的工程文件夹 .idea
    create_temp_project(project_root, project_name, plugin_name)

    cprint('创建成功', 'blue')


@main.command()
@click.argument('plugin_name', required=True, default='')
@click.option('--output', default='./')
def create_plugin(plugin_name, output):
    """创建插件"""
    if len(plugin_name) == 0:
        cprint('usage: {0} create_plugin plugin_name '
               '[--output=<output dir>]'.format(sys.argv[0]), 'red')
        sys.exit(1)

    class_name = to_camel(plugin_name)

    project_root = os.path.expanduser(output)
    create_plugin_at(plugin_name, class_name, project_root)

    cprint('创建成功', 'blue')


def create_plugin_at(plugin_name, class_name, output):
    project_root = output
    if not os.path.exists(project_root):
        cprint('fatal: destination path \'{0}\' not exists.'
               .format(project_root), 'red')
        sys.exit(1)

    # 创建示例工程文件
    init_file_content = INIT_FILE_CONTENT.format(plugin_name, class_name)
    manifest_file_content = MANIFEST_FILE_CONTENT.format(plugin_name)
    plugin_file_content = PLUGIN_FILE_CONTENT.format(class_name, plugin_name)

    project_path = os.path.join(project_root, plugin_name)
    os.makedirs(project_path)
    with open(os.path.join(project_path, '__init__.py'), 'w') as f:
        f.write(init_file_content)
    with open(os.path.join(project_path, '__manifest__.py'), 'w') as f:
        f.write(manifest_file_content)
    with open(os.path.join(project_path, '{0}.py'.format(plugin_name)), 'w') as f:
        f.write(plugin_file_content)


def to_underscore(name):
    underscore_name = ''
    for i in range(len(name)):
        cr = name[i]
        if 'A' <= cr <= 'Z':
            if i > 0 and ('a' <= name[i-1] <= 'z'):
                underscore_name += '_{0}'.format(cr.lower())
            else:
                underscore_name += '{0}'.format(cr.lower())
        else:
            underscore_name += cr
    return underscore_name


def to_camel(name):
    camel_name = ''
    for i in range(len(name)):
        if i == 0:
            if 'a' <= name[0] <= 'z':
                camel_name += name[0].upper()
            else:
                camel_name += name[0]
            continue
        prev_cr = name[i-1]
        cr = name[i]
        if cr == '_':
            continue
        if prev_cr == '_':
            camel_name += cr.upper()
        else:
            camel_name += cr
    return camel_name


if __name__ == '__main__':
    main()
