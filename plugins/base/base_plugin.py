import pa
from pa.plugin import Plugin
import getopt
import sys
import os
from fishbase.fish_common import conf_as_dict
from fishbase.fish_file import check_sub_path_create
from fishbase.fish_logger import logger as fishbase_logger, set_log_file
from .plugin_manager import PluginManager
from sqlalchemy import inspect
import importlib


class BasePlugin(Plugin):
    def __init__(self, **kwargs):
        super(BasePlugin, self).__init__(**kwargs)
        if pa.plugin_manager is not None and pa.plugin_manager.get_plugin('base') is not None:
                raise ValueError('realloc base plugin')

    def on_load(self):
        self.start_log_service()
        self.load_config()

    @staticmethod
    def start_log_service():
        # 创建必须的log文件夹
        check_sub_path_create('log')
        # 日志文件路径
        set_log_file(os.path.join(os.path.abspath('log'), 'server.log'))
        pa.log = fishbase_logger
        # add stdout log output
        import logging
        logger = logging.getLogger()
        logger.addHandler(logging.StreamHandler())

    def load_config(self):
        opts, args = getopt.getopt(sys.argv[1:], 'c:', ['debug'])

        # 调试状态
        if 'debug' in args:
            pa.debug = True

        config_file = None
        for opt in opts:
            if opt[0] == '-c':
                config_file = opt[1]
        if config_file is None:
            pa.log.info('no config file.')
            return

        success, config_info, _ = conf_as_dict(config_file)
        if not success:
            raise ValueError('config file format error.')

        # 设置全局变量
        pa.server_ip = config_info['server']['ip']
        pa.server_port = config_info['server']['port']

        # 加载数据库
        self.load_database(config_info['base']['db_uri'])

        # 加载插件
        if pa.plugin_manager is None:
            pa.plugin_manager = PluginManager()

        # 插件的配置项
        if pa.plugin_config is None:
            pa.plugin_config = {}
        for key in config_info.keys():
            if key == 'base' or key == 'server':
                continue
            pa.plugin_config[key] = {}
            for conf_key, conf_value in config_info[key].items():
                pa.plugin_config[key][conf_key] = conf_value

        # 将 base 加入到插件列表中
        pa.plugin_manager.start(self, os.path.dirname(__file__))

    @staticmethod
    def load_database(db_uri):
        pa.web_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
        pa.web_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        # pa.web_app.config["SQLALCHEMY_ECHO"] = True
        pa.database.app = pa.web_app
        pa.database.init_app(pa.web_app)

    @Plugin.before_install
    def install_tables(self):
        # 获取模块的数据库表
        plugin = importlib.import_module('plugins.{0}'.format(self.plugin_name))
        plugin_tables = []
        for attribute_name in dir(plugin):
            if attribute_name.startswith('__'):
                continue
            attribute_value = getattr(plugin, attribute_name)
            if isinstance(attribute_value, type) and issubclass(attribute_value, pa.database.Model):
                plugin_tables.append(attribute_value)

        for table in plugin_tables:
            BasePlugin._install_table(table)

    @staticmethod
    def _install_table(table):
        # 如果表记录为空则尝试删除原表重新创建新表
        try:
            if table.__table__.exists(pa.database.engine):
                sql = 'select count(*) from {0};'.format(table.__tablename__)
                record_count = pa.database.session.execute(sql).fetchall()[0][0]
                if record_count == 0:
                    table.__table__.drop(pa.database.engine)
        except Exception as e:
            pa.log.info('unable drop table {0} {1}'.format(table.__tablename__, e))

        if not table.__table__.exists(pa.database.engine):
            table.__table__.create(pa.database.engine)
            return

        # 获取原表和新表的列
        iengine = inspect(pa.database.engine)
        old_cols = iengine.get_columns(table.__tablename__)
        new_cols = inspect(table).attrs
        if len(old_cols) != len(new_cols):
            raise TypeError('exists table has {0} columns but new table needs {1} columns in table \'{2}\''
                            .format(len(old_cols), len(new_cols), table.__tablename__))
        # 对比原表和新表的列是否一致，不一致则报错
        for new_col_conf in new_cols:
            new_col = None
            for column in new_col_conf.columns:
                if column.key == new_col_conf.key:
                    new_col = column
                    break
            old_col = None
            for oc in old_cols:
                if oc['name'] == new_col_conf.key:
                    old_col = oc
                    break
            if old_col is None or new_col is None:
                raise TypeError('column \'{0}\' is not exist in table \'{1}\''
                                .format(new_col_conf.key, table.__tablename__))

            for key in old_col.keys():
                if not hasattr(new_col, key):
                    raise TypeError('type \'{0}\' not defined in {1}.{2}'
                                    .format(key, table.__tablename__, new_col_conf.key))
                old_col_value = old_col[key]
                new_col_value = getattr(new_col, key)

                if not BasePlugin._check_columns_match(key, old_col_value, new_col_value):
                    raise TypeError('type \'{0}\' not match ({1} != {2}) in {3}.{4}'
                                    .format(key, old_col_value, new_col_value, table.__tablename__, new_col_conf.key))
        # 检查表结构一致则跳过建表
        pass

    @staticmethod
    def _check_columns_match(key, old_column_value, new_column_value):
        if key == 'type':
            matching = (old_column_value.Comparator == new_column_value.Comparator)
            if matching and (hasattr(old_column_value, 'length') or hasattr(new_column_value, 'length')):
                old_column_value_length = getattr(old_column_value, 'length', 0)
                new_column_value_length = getattr(new_column_value, 'length', 0)
                matching = (old_column_value_length == new_column_value_length)
        elif key == 'autoincrement':
            matching = True
        elif key == 'primary_key':
            matching = (old_column_value == 1)
            matching = (matching == new_column_value)
        elif key == 'default':
            matching = True
        elif key == 'nullable':
            matching = True
        else:
            matching = (old_column_value == new_column_value)
        return matching
