from flask_sqlalchemy import SQLAlchemy


# Flask 应用程序
web_app = None


# 日志服务
log = None


# 数据库
database = SQLAlchemy()


# 服务 ip/port
server_ip = None
server_port = None


# debug 状态
debug = False


# 插件管理工具
plugin_manager = None

# 插件配置
plugin_config = None
