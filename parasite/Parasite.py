from flask import Flask
import pa
from plugins.base import *

app = Flask(__name__)
pa.web_app = app

# 默认加载 base 插件
BasePlugin().on_load()

if __name__ == '__main__':
    app.run(host=pa.server_ip, port=int(pa.server_port), threaded=True)
