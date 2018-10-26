from termcolor import cprint
import sys
import os
import ast
import tempfile
import re
from parasite.bin.download_source import pa_root, download_parasite, download_plugin


def debug_plugin(plugin_path):
    """调试插件"""
    if len(plugin_path) == 0:
        cprint('usage: {0} debug <plugin_path>'.format(sys.argv[0]), 'red')
        sys.exit(1)

    manifest_file = os.path.join(plugin_path, '__manifest__.py')
    try:
        with open(manifest_file) as f:
            manifest = ast.literal_eval(f.read())
    except Exception as e:
        str(e)
        cprint('can NOT found __manifest__.py file in plugin path: {0}'.format(plugin_path), 'red')
        sys.exit(1)

    project_path = os.path.join(plugin_path, '.parasite')
    # if os.path.exists(project_path):
    #     shutil.rmtree(project_path)

    download_parasite(project_path)

    if 'depends' in manifest:
        with tempfile.TemporaryDirectory() as temp_path:
            for depend_plugin in manifest['depends']:
                try:
                    download_plugin(pa_root, depend_plugin, temp_path, project_path)
                except Exception as e:
                    cprint(str(e), 'red')
                    sys.exit(1)

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
        'config.conf',
        '--extra_plugin={0}'.format(os.path.realpath(plugin_path))
    ]
    os.chdir(project_path)

    print('debuging plugin \'{0} ({1})\'...'.format(manifest['name'], manifest['version']))
    exec('import Parasite')
