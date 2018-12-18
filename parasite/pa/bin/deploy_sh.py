import os
from .download_source import pa_root, parasite_git_url, get_all_depend_manifest
from .download_source import get_plugin_manifest_path as __get_plugin_manifest_path


def get_plugin_manifest_path(plugin_name):
    manifest_path, _, _, _ = __get_plugin_manifest_path(pa_root, plugin_name)
    return manifest_path


def deploy_sh(project_name, manifest_file, config_file=None,
              extra_plugin_paths=None, resource_file=None, output=None):
    """创建部署脚本"""
    output_name = '{0}.sh'.format(project_name)
    if output is not None and len(output) > 0:
        if os.path.isdir(output) or os.path.basename(output) == '':
            output_dir = output
        else:
            output_dir = os.path.dirname(output)
            output_name = os.path.basename(output)
    else:
        output_dir = os.getcwd()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    sh_content = '#!/bin/bash\n\n'
    sh_content += 'project_name={0}\n'.format(project_name)
    sh_content += '\n\n'

    # 添加 Parasite 的下载代码
    sh_content += 'echo -e "\033[34m clone Parasite... \033[0m"\n'
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
        sh_content += 'echo -e "\033[34m installing plugins \'{0}\'...({1}/{2}) \033[0m"\n'\
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
        sh_content += 'echo -e "\033[34m writing \'config.conf\'... \033[0m"\n'
        sh_content += 'echo -e {0} > $project_name/config.conf\n'.format(str_content)
        sh_content += '\n\n'

    # 资源文件
    if resource_file is not None:
        index = 1
        resource_length = len(resource_file.keys())
        for file, dest_path in resource_file.items():
            str_content = ''
            file_name = os.path.basename(file)
            with open(file, 'rb') as f:
                content = f.read()
                for i in range(len(content)):
                    str_content += '\\\\x{:02X}'.format(content[i])
            if len(dest_path) > 0:
                if os.path.isdir(dest_path) or os.path.basename(dest_path) == '':
                    file_name = '{0}/{1}'.format(dest_path, file_name)
                else:
                    file_name = dest_path
            sh_content += 'echo -e "\033[34m writing resource file \'{0}\'... ({1}/{2}) \033[0m"\n'\
                          .format(file_name, index, resource_length)
            sh_content += 'if [ ! -d "$project_name/{0}" ]; then\n'.format(os.path.dirname(file_name))
            sh_content += '    mkdir -p "$project_name/{0}"\n'.format(os.path.dirname(file_name))
            sh_content += 'fi\n'
            sh_content += 'echo -e {0} > \"$project_name/{1}\"\n'.format(str_content, file_name)
            sh_content += '\n\n'
            index += 1

    # 打包
    sh_content += 'echo -e "\033[34m packaging ${project_name}.tar... \033[0m"\n'
    sh_content += 'tar cf $project_name.tar $project_name\n'
    sh_content += 'rm -rf $project_name\n'

    # 保存
    with open(os.path.join(output_dir, output_name), 'w') as f:
        f.write(sh_content)
