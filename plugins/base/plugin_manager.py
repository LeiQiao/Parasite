import os
import pa
from .models import Plugins
from pa.plugin import Plugin
import importlib
import ast


class PluginManager:
    all_installed_plugins = []

    def start(self, base_plugin, base_plugin_path):
        base_plugin.manifest = self._load_plugin_manifest(base_plugin_path)
        self.all_installed_plugins.append(base_plugin)
        self.load_plugins()

    def load_plugins(self):
        base_plugin = self.get_plugin('base')

        # 创建插件表，并将 base 插件写入表中
        if not Plugins.__table__.exists(pa.database.engine):
            Plugins.__table__.create(pa.database.engine)

            base_plugin_record = Plugins(name=base_plugin.manifest['name'],
                                         version=base_plugin.manifest['version'],
                                         installed=1)
            pa.database.session.add(base_plugin_record)
            pa.database.session.commit()
        else:
            # 升级基础插件
            base_plugin_record = Plugins.query.filter_by(name=base_plugin.manifest['name'], installed=1).first()
            if base_plugin_record is not None and \
                    base_plugin_record.version != base_plugin.manifest['version']:
                base_plugin.on_upgrade(base_plugin_record.version)

        # 遍历插件文件夹获取所有所有插件
        plugin_path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
        loaded_plugins = []
        for root, dirs, files in os.walk(plugin_path):
            if plugin_path != root:
                continue
            for plugin_name in dirs:
                # trim '__pacache__' etc.
                if plugin_name.startswith('__'):
                    continue
                self._load_plugin(plugin_name)
                loaded_plugins.append(plugin_name)
        try:
            all_plugins = Plugins.query.all()
            removed_plugins = []
            for plugin in all_plugins:
                if plugin.name in loaded_plugins:
                    continue
                removed_plugins.append(plugin.id)
        except Exception as e:
            str(e)
            pa.log.error('loading plugin: unable load all installed plugins')
            raise e

        if len(removed_plugins) > 0:
            try:
                Plugins.query.filter(Plugins.id.in_(removed_plugins)).delete(synchronize_session='fetch')
                pa.database.session.commit()
            except Exception as e:
                str(e)
                pa.log.error('unable remove non exists plugin')
                raise e

    @staticmethod
    def get_plugin(plugin_name):
        for installed_plugin in PluginManager.all_installed_plugins:
            if installed_plugin.manifest['name'] == plugin_name:
                return installed_plugin
        return None

    @staticmethod
    def _load_plugin_manifest(plugin_path):
        # 读取模块和描述信息
        try:
            with open(os.path.join(plugin_path, '__manifest__.py')) as f:
                manifest = ast.literal_eval(f.read())
                return manifest
        except Exception as e:
            str(e)
            pa.log.warning('loading plugin: \'{0}\' is not a plugin or missing __manifest__.py file, skip'
                           .format(os.path.basename(plugin_path)))
            return None

    def _load_plugin(self, plugin_name, depend_by=None):
        if len(plugin_name) == 0:
            return

        if self.get_plugin(plugin_name) is not None:
            return

        installed_plugin = Plugins.query.filter_by(name=plugin_name).first()
        # 插件已卸载
        if installed_plugin is not None and installed_plugin.installed == 0:
            return

        plugin = importlib.import_module('plugins.{0}'.format(plugin_name))
        manifest = self._load_plugin_manifest(os.path.dirname(plugin.__file__))
        if manifest is None:
            return

        # 加载模块的依赖模块
        for depend_name in manifest['depends']:
            if depend_by is None:
                depend_by = []
            else:
                # 循环依赖
                if plugin_name in depend_by:
                    raise RecursionError('recursive dependency: {0} -> {1}'.format(' -> '.join(depend_by), plugin_name))
            new_depend_by = depend_by[:]
            new_depend_by.append(plugin_name)
            self._load_plugin(depend_name, new_depend_by)

        # 获取模块的入口对象
        plugin_class = None
        for attribute_name in dir(plugin):
            if attribute_name.startswith('__'):
                continue
            attribute_value = getattr(plugin, attribute_name)
            if isinstance(attribute_value, type) and issubclass(attribute_value, Plugin):
                plugin_class = attribute_value
        if plugin_class is None:
            raise ModuleNotFoundError('plugin \'{0}\' has not found enterance'.format(manifest['name']))

        plugin = plugin_class(plugin_name=plugin_name, manifest=manifest)

        # 添加到已加载的插件列表
        self.all_installed_plugins.append(plugin)

        # 查看模块是否已经安装
        if installed_plugin is None:
            # 安装插件
            plugin.on_before_install()
            plugin.on_install()
            plugin.on_after_install()
            new_plugin = Plugins(name=manifest['name'],
                                 version=manifest['version'],
                                 installed=1)
            pa.database.session.add(new_plugin)
            pa.database.session.commit()
        elif installed_plugin.version != manifest['version']:
            # 升级插件
            plugin.on_upgrade(installed_plugin.version)
            installed_plugin.version = manifest['version']
            pa.database.session.commit()

        # 加载模块
        plugin.on_before_load()
        plugin.on_load()
        plugin.on_after_load()
