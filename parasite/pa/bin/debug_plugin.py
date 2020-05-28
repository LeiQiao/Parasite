import sys
import os
import ast
import tempfile
import re
from .download_source import pa_root, download_parasite, download_plugin, is_plugin_in_extra_path
from .pycharm_project import add_parasite_path_inspector, ignore_parasite


def test_manifest(path):
    manifest_file = os.path.join(path, '__manifest__.py')
    if not os.path.exists(manifest_file):
        return False

    try:
        with open(manifest_file) as f:
            manifest = ast.literal_eval(f.read())
            if 'name' not in manifest:
                return False
            if 'source' not in manifest:
                return False
            if 'version' not in manifest or manifest['version'] == '':
                return False
    except Exception as e:
        _ = e
        return False
    return True



def get_all_plugin_from_path(path):
    all_plugins = []
    path = os.path.realpath(path)
    for root, dirs, files in os.walk(path):
        if path != root:
            continue
        for plugin_name in dirs:
            # trim '__pacache__', '.DB_Store' etc.
            if plugin_name.startswith('__') or plugin_name.startswith('.'):
                continue
            plugin_path = os.path.join(path, plugin_name)
            if test_manifest(plugin_path):
                all_plugins.append(plugin_path)
    return all_plugins



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
                                .format(plugin_path))

    project_path = os.path.join(plugin_path, '.parasite')

    download_parasite(project_path)

    extra_plugins = get_all_depend_extra_plugins_and_download_plugin(manifest, project_path, extra_plugin_paths)
    extra_plugins.append(os.path.realpath(plugin_path))

    for extra_plugin_path in extra_plugin_paths:
        aps = get_all_plugin_from_path(extra_plugin_path)
        for p in aps:
            if p not in extra_plugins:
                extra_plugins.append(p)

    # 修改工程文件
    idea_path = os.path.realpath(os.path.join(plugin_path, '..'))
    project_name = os.path.basename(idea_path)
    plugin_name = os.path.basename(plugin_path)
    add_parasite_path_inspector(idea_path, project_name, plugin_name)
    parasite_path = os.path.relpath(project_path, idea_path)
    ignore_parasite(idea_path, parasite_path)

    # 更改环境变量，启动调试
    py_file = os.path.realpath(os.path.join(project_path, 'Parasite.py'))
    # with open(py_file) as f:
    #     content = f.read()
    #     try:
    #         content = re.sub('if __name__ == \'__main__\':', 'if True:', content)
    #     except Exception as e:
    #         str(e)
    # with open(py_file, 'w') as f:
    #     f.write(content)

    sys.path.insert(0, os.path.realpath(project_path))
    sys.argv = [
        py_file,
        '-c',
        'config.conf' if config_file is None else os.path.realpath(config_file),
        '--extra_plugin={0}'.format(','.join(extra_plugins)),
        'debug'
    ]
    os.chdir(project_path)

    print('debuging plugin \'{0} ({1})\'...'.format(manifest['name'], manifest['version']))
    exec('import Parasite')


def get_all_depend_extra_plugins_and_download_plugin(manifest, project_path, extra_plugin_paths):
    extra_plugins = []
    if 'depends' in manifest:
        with tempfile.TemporaryDirectory() as temp_path:
            for depend_plugin in manifest['depends']:
                is_extra_plugin, extra_plugin_path = is_plugin_in_extra_path(depend_plugin,
                                                                             extra_plugin_paths)
                if is_extra_plugin:
                    extra_plugins.append(extra_plugin_path)

                    manifest_file = os.path.join(extra_plugin_path, '__manifest__.py')
                    try:
                        with open(manifest_file) as f:
                            manifest = ast.literal_eval(f.read())
                    except Exception as e:
                        str(e)
                        raise FileNotFoundError('can NOT found __manifest__.py file in plugin path: {0}'
                                                .format(extra_plugin_path))
                    insert_pos = len(extra_plugins)-1
                    for ep in get_all_depend_extra_plugins_and_download_plugin(manifest,
                                                                               project_path,
                                                                               extra_plugin_paths):
                        if ep in extra_plugins:
                            continue
                        extra_plugins.insert(insert_pos, ep)
                        insert_pos += 1
                else:
                    download_plugin(pa_root, depend_plugin, temp_path, project_path)
    return extra_plugins
