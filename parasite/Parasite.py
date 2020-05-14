import pa
from plugins.base import *

# 默认加载 base 插件
BasePlugin().on_load()

# web app 用于 uwsgi 等服务加载
web_app = pa.web_app
