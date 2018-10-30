import os
import ast
import git
import shutil
import tempfile

pa_root = os.path.join(os.getenv("HOME"), '.parasite/repos/master/Specs/')
parasite_git_url = 'https://github.com/LeiQiao/Parasite.git'


def download_parasite(output_dir):
    parasite_file = os.path.join(output_dir, 'Parasite.py')
    if os.path.exists(parasite_file):
        return

    print('downloading Parasite...')
    with tempfile.TemporaryDirectory() as temp_dir:
        git.Repo.clone_from(url=parasite_git_url, to_path=temp_dir)
        shutil.copytree(os.path.join(temp_dir, 'parasite'), output_dir)


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
        raise ImportError('load plugin \'{0} ({1})\' failed, you can run \'update\' to reload plugin.'
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


def get_plugin_manifest_path(plugin_root, plugin_name):
    manifest_path, manifest, _, _ = __get_plugin_manifest(plugin_root, plugin_name)
    return manifest_path


def __get_plugin_manifest(plugin_root, plugin_name):
    name_and_version = plugin_name.split(':')
    plugin_name = name_and_version[0].strip()
    if len(name_and_version) > 1:
        plugin_version = name_and_version[1].strip()
    else:
        plugin_version = None

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
    manifest_path = os.path.join(plugin_path, '__manifest__.py')
    try:
        with open(manifest_path) as f:
            manifest = ast.literal_eval(f.read())
    except Exception as e:
        str(e)
        raise ImportError('load plugin \'{0} ({1})\' failed, you can run \'update\' to reload plugin.'
                          .format(plugin_name, plugin_version))
    return manifest_path, manifest, plugin_name, plugin_version


def get_all_depend_manifest(plugin_root, manifest_file):
    all_depend_manifest = {}

    for file in manifest_file:
        with open(file) as f:
            manifest = ast.literal_eval(f.read())
        for depend_name in manifest['depends']:
            all_depend_manifest = __merge_manifest(all_depend_manifest,
                                                   __get_all_depend_manifest(plugin_root, depend_name))
        all_depend_manifest = __merge_manifest(all_depend_manifest, {manifest['name']: manifest})

    return all_depend_manifest


def __get_all_depend_manifest(plugin_root, plugin_name, depend_by=None):
    _, manifest, _, plugin_version = __get_plugin_manifest(plugin_root, plugin_name)

    # 防止循环引用
    if depend_by is None:
        depend_by = []
    else:
        for by in depend_by:
            # 循环引用
            if plugin_name == by[0]:
                def x(a): return '{0} ({1})'.format(a[0], (a[1] if a[1] is not None else 'any'))
                raise RecursionError('recursive dependency: {0} -> {1})'
                                     .format(' -> '.join(x(i) for i in depend_by),
                                             x((plugin_name, plugin_version))))
    # 将当前插件名压入循环引用队列
    new_depend_by = depend_by[:]
    new_depend_by.append((plugin_name, plugin_version))

    # 获取所有依赖的 manifest
    all_depend_manifest = {plugin_name: manifest}
    if 'depends' in manifest:
        for dname in manifest['depends']:
            __merge_manifest(all_depend_manifest, __get_all_depend_manifest(plugin_root, dname, new_depend_by))

    return all_depend_manifest


def __merge_manifest(manifest_dict, other_manifest_dict):
    for depend_name, depend_manifest in other_manifest_dict.items():
        if depend_name in manifest_dict:
            if manifest_dict[depend_name]['version'] == depend_manifest['version']:
                continue
            raise RecursionError('conflit dependency: \'{0}\' have two different version '
                                 '({1}) ({2})'
                                 .format(depend_name,
                                         manifest_dict[depend_name]['version'],
                                         depend_manifest['version']))
        else:
            manifest_dict[depend_name] = depend_manifest
    return manifest_dict
