import sys
import os
import ast
import tempfile
import re
from .download_source import pa_root, download_parasite, download_plugin, is_plugin_in_extra_path
from .pycharm_project import add_parasite_path_inspector, ignore_parasite


def debug_plugin(plugin_path, config_file=None, extra_plugin_paths=None):
    if not config_file:
        if not os.path.exists(config_file):
            raise FileNotFoundError('file not exists \'{0}\''.format(config_file))

    """调试插件"""
    manifest_file = os.path.join(plugin_path, '__manifest__.py')
    try:
        with open(manifest_file) as f:
            manifest = ast.literal_eval(f.read())
    except Exception as e:
        str(e)
        raise FileNotFoundError('can NOT found __manifest__.py file in plugin path: {0}'
                                .format(plugin_path), 'red')

    project_path = os.path.join(plugin_path, '.parasite')

    download_parasite(project_path)

    extra_plugins = []

    if 'depends' in manifest:
        with tempfile.TemporaryDirectory() as temp_path:
            for depend_plugin in manifest['depends']:
                is_extra_plugin, extra_plugin_path = is_plugin_in_extra_path(depend_plugin,
                                                                             extra_plugin_paths)
                if is_extra_plugin:
                    extra_plugins.append(extra_plugin_path)
                else:
                    download_plugin(pa_root, depend_plugin, temp_path, project_path)

    extra_plugins.append(os.path.realpath(plugin_path))

    # 修改工程文件
    idea_path = os.path.realpath(os.path.join(plugin_path, '..'))
    project_name = os.path.basename(idea_path)
    add_parasite_path_inspector(idea_path, project_name)
    ignore_parasite(idea_path, project_name)

    # 更改环境变量，启动调试
    py_file = os.path.realpath(os.path.join(project_path, 'Parasite.py'))
    with open(py_file) as f:
        content = f.read()
        try:
            content = re.sub('if __name__ == \'__main__\':', 'if True:', content)
        except Exception as e:
            str(e)
    with open(py_file, 'w') as f:
        f.write(content)

    sys.path.insert(0, os.path.realpath(project_path))
    sys.argv = [
        py_file,
        '-c',
        'config.conf' if config_file is None else os.path.realpath(config_file),
        '--extra_plugin={0}'.format(','.join(extra_plugins))
    ]
    os.chdir(project_path)

    print('debuging plugin \'{0} ({1})\'...'.format(manifest['name'], manifest['version']))
    exec('import Parasite')
