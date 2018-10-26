import os
import ast
import git
import shutil


pa_root = os.path.join(os.getenv("HOME"), '.parasite/repos/master/Specs/')


def download_parasite(output_dir):
    parasite_file = os.path.join(output_dir, 'Parasite.py')
    if os.path.exists(parasite_file):
        return

    print('downloading Parasite...')
    git.Repo.clone_from(url='https://github.com/LeiQiao/Parasite.git', to_path=output_dir)


def download_plugin(plugin_root, plugin_name, temp_dir, output_dir):
    name_and_version = plugin_name.split(':')
    plugin_name = name_and_version[0].strip()
    if len(name_and_version) > 1:
        plugin_version = name_and_version[1].strip()
    else:
        plugin_version = None

    plugin_dir = os.path.join(output_dir, 'plugins', plugin_name)
    if os.path.exists(plugin_dir):
        manifest_file = os.path.join(plugin_dir, '__manifest__.py')
        manifest = None
        try:
            with open(manifest_file) as f:
                manifest = ast.literal_eval(f.read())
        except Exception as e:
            str(e)
        if manifest and (manifest['version'] == plugin_version or plugin_version is None):
            return
        shutil.rmtree(plugin_dir)

    if plugin_version is not None:
        print('downloading plugin \'{0} ({1})\'...'.format(plugin_name, plugin_version))
    else:
        print('downloading plugin \'{0}\'...'.format(plugin_name))

    plugin_path = os.path.join(plugin_root, plugin_name)
    if not os.path.exists(plugin_path):
        raise ModuleNotFoundError('plugin \'{0}\' not exist'.format(plugin_name))
    versions = os.listdir(plugin_path)
    if len(versions) == 0:
        raise ModuleNotFoundError('plugin \'{0}\' not exist'.format(plugin_name))
    if plugin_version is None:
        plugin_version = versions[0]
    elif plugin_version not in versions:
        raise ModuleNotFoundError('given version not exist \'{0}\' ({1})'
                                  .format(plugin_name, plugin_version))

    plugin_path = os.path.join(plugin_path, plugin_version)
    try:
        with open(os.path.join(plugin_path, '__manifest__.py')) as f:
            manifest = ast.literal_eval(f.read())
    except Exception as e:
        str(e)
        raise ImportError('load plugin \'{0}({1})\' failed, you can run \'update\' to reload plugin.'
                          .format(plugin_name, plugin_version))

    depends = []
    if 'depends' in manifest:
        depends = manifest['depends']
    for depend in depends:
        download_plugin(plugin_root, depend, temp_dir, output_dir)

    if 'git' in manifest['source']:
        if 'branch' in manifest['source']:
            branch = manifest['source']['branch']
        else:
            branch = 'master'
        git_path = os.path.join(temp_dir, os.path.basename(manifest['source']['git']), branch)
        if not os.path.exists(os.path.join(git_path, '.git')):
            if os.path.exists(git_path):
                shutil.rmtree(git_path)
            git.Repo.clone_from(url=manifest['source']['git'], to_path=git_path, branch=branch)
        if 'path' in manifest['source']:
            git_path = os.path.join(git_path, manifest['source']['path'])
        git_path = os.path.join(git_path, plugin_name)
        shutil.copytree(git_path, plugin_dir)
