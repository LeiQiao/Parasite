import pa
from plugins.base import *

# 默认加载 base 插件
BasePlugin().on_load()

if True:
    pa.web_app.run(host=pa.server_ip, port=int(pa.server_port), threaded=True)
