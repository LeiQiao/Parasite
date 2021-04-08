import os
from .download_source import pa_root, parasite_git_url, get_all_depend_manifest
from .download_source import get_plugin_manifest_path as __get_plugin_manifest_path
import ast
import git
import shutil


def get_plugin_manifest_path(plugin_name):
    manifest_path, _, _, _ = __get_plugin_manifest_path(pa_root, plugin_name)
    return manifest_path


def deploy_sh(project_name, manifest_file, config_file=None,
              extra_plugin_paths=None, resource_file=None, output=None, tar_name=None):
    """创建部署脚本"""
    output_name = '{0}.sh'.format(project_name)
    if output is not None and len(output) > 0:
        if os.path.isdir(output) or os.path.basename(output) == '':
            output_dir = output
        else:
            output_dir = os.path.dirname(output)
            if len(output_dir) == 0:
                output_dir = './'
            output_name = os.path.basename(output)
    else:
        output_dir = os.getcwd()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    sh_content = '#!/bin/bash\n\n'
    sh_content += 'project_name={0}\n'.format(project_name)
    sh_content += '\n\n'

    # 添加 Parasite 的下载代码
    sh_content += 'echo -e "\033[36m clone Parasite... \033[0m"\n'
    sh_content += 'git clone {0} Parasite.git\n'.format(parasite_git_url)
    sh_content += 'rc=$?\n'
    sh_content += 'if [[ $rc != 0 ]]; then\n'
    sh_content += '    echo -e "[31m unable download Parasite [0m"\n'
    sh_content += '    exit $rc\n'
    sh_content += 'fi\n'
    sh_content += 'cp -r Parasite.git/parasite $project_name\n'
    sh_content += 'rm -rf Parasite.git'
    sh_content += '\n\n'

    # 构建依赖插件包
    all_depend_manifest = get_all_depend_manifest(pa_root, manifest_file, extra_plugin_paths)
    index = 1
    depend_length = len(all_depend_manifest.keys())
    downloaded_source = {}
    for depend_name, manifest in all_depend_manifest.items():
        sh_content += 'echo -e "\033[36m installing plugins \'{0}\'...({1}/{2}) \033[0m"\n'\
                      .format(depend_name, index, depend_length)
        if 'git' in manifest['source']:
            git_address = manifest['source']['git']
            if len(git_address) == 0:
                raise ModuleNotFoundError('plugin {0} donot have an git repository.'.format(manifest['name']))
            branch = manifest['source']['branch'] if 'branch' in manifest['source'] else 'master'
            source_path_name = '{0}-{1}'.format(os.path.basename(git_address),
                                                branch)
            source_url = 'git clone -b {0} {1} {2}'\
                         .format(branch,
                                 manifest['source']['git'],
                                 source_path_name)
        else:
            raise NotImplementedError('only support \'git\' for revision control tool.')
        # 下载插件代码
        if source_url not in downloaded_source:
            sh_content += '{0}\n'.format(source_url)
            sh_content += 'rc=$?\n'
            sh_content += 'if [[ $rc != 0 ]]; then\n'
            sh_content += '    echo -e "[31m unable download plugin \'{0}\' [0m"\n'.format(depend_name)
            sh_content += '    exit $rc\n'
            sh_content += 'fi\n'
            downloaded_source[source_url] = source_path_name
        # 设置子目录
        if 'path' in manifest['source'] and len(manifest['source']['path']) > 0:
            source_path = '{0}/{1}/{2}'.format(source_path_name, manifest['source']['path'], depend_name)
        else:
            source_path = '{0}/{1}'.format(source_path_name, depend_name)
        # 将代码拷贝到插件目录下
        sh_content += 'cp -r \"{0}\" $project_name/plugins/\n'.format(source_path)
        sh_content += '\n\n'
        index += 1
    # 清除下载的代码目录
    for source, path_name in downloaded_source.items():
        sh_content += 'rm -rf {0}\n'.format(path_name)
    sh_content += '\n\n'

    # 配置文件
    if config_file is not None:
        str_content = ''
        with open(config_file, 'rb') as f:
            content = f.read()
            for i in range(len(content)):
                str_content += '\\\\x{:02X}'.format(content[i])
        sh_content += 'echo -e "\033[36m writing \'config.conf\'... \033[0m"\n'
        sh_content += 'echo -e {0} > $project_name/config.conf\n'.format(str_content)
        sh_content += '\n\n'

    # 资源文件
    if resource_file is not None:
        index = 1
        resource_length = len(resource_file.keys())
        for file, dest_path in resource_file.items():
            str_content = ''
            origin_file_name = os.path.basename(file)
            with open(file, 'rb') as f:
                content = f.read()
                for i in range(len(content)):
                    str_content += '\\\\x{:02X}'.format(content[i])
            file_names = []
            if isinstance(dest_path, list):
                file_names = dest_path
            else:
                file_names.append(dest_path)

            for file_name in file_names:
                if len(file_name) > 0:
                    if os.path.isdir(file_name) or os.path.basename(file_name) == '':
                        file_name = os.path.join(file_name, origin_file_name)
                else:
                    file_name = origin_file_name

                sh_content += 'echo -e "\033[36m writing resource file \'{0}\'... ({1}/{2}) \033[0m"\n'\
                              .format(file_name, index, resource_length)
                sh_content += 'if [ ! -d "$project_name/{0}" ]; then\n'.format(os.path.dirname(file_name))
                sh_content += '    mkdir -p "$project_name/{0}"\n'.format(os.path.dirname(file_name))
                sh_content += 'fi\n'
                sh_content += 'echo -e {0} > \"$project_name/{1}\"\n'.format(str_content, file_name)
                sh_content += '\n\n'
                index += 1

    # 打包
    sh_content += 'echo -e "\033[36m packaging ${project_name}.tar... \033[0m"\n'
    if tar_name is not None:
        if tar_name[-4:].lower() != '.tar':
            tar_name = tar_name + '.tar'
        sh_content += 'tar cf {0} $project_name\n'.format(tar_name)
    else:
        sh_content += 'tar cf $project_name.tar $project_name\n'
    sh_content += 'rm -rf $project_name\n'

    # 保存
    with open(os.path.join(output_dir, output_name), 'w') as f:
        f.write(sh_content)


def package_tar(project_name, manifest_file, config_file=None,
                extra_plugin_paths=None, resource_file=None, tar_name=None):
    all_manifest = get_all_depend_manifest(pa_root, manifest_file, extra_plugin_paths)

    # 创建换从工作文件夹
    if not os.path.exists('.pa.cache'):
        os.makedirs('.pa.cache', exist_ok=True)

    if not os.path.exists('.pa.cache/gits'):
        os.makedirs('.pa.cache/gits', exist_ok=True)

    if not os.path.exists('.pa.cache/gits/Parasite'):
        print('\033[36m downloading Parasite... \033[0m')
        git.Repo.clone_from(url=parasite_git_url, to_path='.pa.cache/gits/Parasite')
    else:
        print('\033[36m updating Parasite... \033[0m')
        g = git.cmd.Git('.pa.cache/gits/Parasite')
        g.reset('--hard')
        g.pull()

    # 开始打包
    project_path = os.path.join('.pa.cache', project_name)
    project_plugin_path = os.path.join(project_path, 'plugins')
    if os.path.exists(project_path):
        shutil.rmtree(project_path, ignore_errors=True)

    shutil.copytree('.pa.cache/gits/Parasite/parasite', project_path)

    # 复制配置文件
    if config_file is not None:
        print('\033[36m writing \'config.conf\'... \033[0m')
        shutil.copyfile(config_file, os.path.join(project_path, 'config.conf'))

    # 资源文件
    if resource_file is not None:
        index = 1
        resource_length = len(resource_file.keys())
        for file, dest_path in resource_file.items():
            origin_file_name = os.path.basename(file)
            file_names = []
            if isinstance(dest_path, list):
                file_names = dest_path
            else:
                file_names.append(dest_path)

            for file_name in file_names:
                if len(file_name) > 0:
                    if os.path.isdir(file_name) or os.path.basename(file_name) == '':
                        file_name = os.path.join(file_name, origin_file_name)
                else:
                    file_name = origin_file_name

                if file_name[0] == '/':
                    file_name = file_name[1:]

                print("\033[36m writing resource file \'{0}\'... \033[0m".format(
                    file_name, index, resource_length))

                file_name = os.path.join(project_path, file_name)
                dest_path = os.path.dirname(file_name)

                if not os.path.exists(dest_path):
                    os.makedirs(dest_path, exist_ok=True)
                shutil.copyfile(file, file_name)

    cached_gits = {}
    for d in os.listdir('.pa.cache/gits'):
        # if d == 'Parasite':
        #     continue
        git_path = os.path.join('.pa.cache/gits', d)
        g = git.cmd.Git(git_path)
        url = g.config('remote.origin.url')
        try:
            branch = g.rev_parse('--abbrev-ref', 'HEAD')
        except Exception as e:
            _ = e
            shutil.rmtree(git_path, ignore_errors=True)
            continue
        cached_gits[url] = {
            'branch': branch,
            'path': git_path,
            'pulled': False
        }

    for plugin_name, manifest in all_manifest.items():
        if 'git' in manifest['source']:
            git_address = manifest['source']['git']
            if len(git_address) == 0:
                raise ModuleNotFoundError('plugin {0} donot have an git repository.'.format(manifest['name']))
            git_branch = manifest['source']['branch'] if 'branch' in manifest['source'] else 'master'
            # 设置子目录
            if 'path' in manifest['source'] and len(manifest['source']['path']) > 0:
                git_source_path = os.path.join(manifest['source']['path'], plugin_name)
            else:
                git_source_path = plugin_name
        else:
            raise NotImplementedError('only support \'git\' for revision control tool.')

        src_plugin_path = ''
        for extra_path in extra_plugin_paths:
            plugin_paths = os.listdir(extra_path)
            for plugin_path in plugin_paths:
                try:
                    with open(os.path.join(extra_path, plugin_path, '__manifest__.py')) as f:
                        m2 = ast.literal_eval(f.read())
                except Exception as e:
                    _ = e
                    continue

                if m2['name'] == manifest['name'] and m2['version'] == manifest['version']:
                    src_plugin_path = os.path.join(extra_path, plugin_path)
                    break
            if len(src_plugin_path) > 0:
                break

        if len(src_plugin_path) == 0:
            for git_url, cached_git in cached_gits.items():
                if git_url != git_address:
                    continue
                g = git.cmd.Git(cached_git['path'])
                if git_branch != cached_git['branch']:
                    g.check_out(git_branch)
                    cached_git['branch'] = git_branch
                if not cached_git['pulled']:
                    print('\033[36m updating {0}... \033[0m'.format(os.path.basename(git_url)))
                    g.reset('--hard')
                    g.pull()
                    cached_git['pulled'] = True
                src_plugin_path = os.path.join(cached_git['path'], git_source_path)
                break

        if len(src_plugin_path) == 0:
            git_path = os.path.join('.pa.cache/gits', os.path.basename(git_address))

            if not os.path.exists(git_path):
                print('\033[36m downloading {0} from {1}... \033[0m'.format(plugin_name, git_address))
                git.Repo.clone_from(url=git_address, to_path=git_path, branch=git_branch)
            else:
                print('\033[36m updating {0} from {1}... \033[0m'.format(plugin_name, git_address))
                g = git.cmd.Git(git_path)
                g.pull('origin', git_branch)

            cached_gits[git_address] = {
                'branch': git_branch,
                'path': git_path,
                'pulled': True
            }

            src_plugin_path = os.path.join(git_path, git_source_path)

        if len(src_plugin_path) == 0:
            raise FileNotFoundError('unable found plugin {0}'.format(plugin_name))

        print('\033[36m installing plugin \'{0}\'... \033[0m'.format(plugin_name))
        shutil.copytree(src_plugin_path, os.path.join(project_plugin_path, plugin_name))

    # 打包
    output_name = '{0}.tar.bz2'.format(project_name)
    if tar_name is not None and len(tar_name) > 0:
        if os.path.isdir(tar_name) or os.path.basename(tar_name) == '':
            output_dir = tar_name
        else:
            output_dir = os.path.dirname(tar_name)
            if len(output_dir) == 0:
                output_dir = './'
            output_name = os.path.basename(tar_name)
    else:
        output_dir = os.getcwd()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    print('\033[36m packaging {0}... \033[0m'.format(output_name))
    if output_name is not None:
        if output_name[-8:].lower() != '.tar.bz2':
            output_name = output_name + '.tar.bz2'
    os.system("cd .pa.cache && tar cJf {0} {1} && cd ..".format(
        output_name,
        project_name))
    shutil.move(os.path.join('.pa.cache', output_name), os.path.join(output_dir, output_name))

    # clean up
    shutil.rmtree(project_path, ignore_errors=True)

    print('\033[36m done \033[0m')
