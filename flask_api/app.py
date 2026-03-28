from flask_openapi3 import OpenAPI, Info
from flask import redirect
from flask_cors import CORS
# 导入功能模块的蓝图
from api.chat import chat_bp
from api.image import image_bp

# 1. 初始化项目
info = Info(title="AI Chat API", version="1.0.0")
app = OpenAPI(__name__, info=info)

# 启用 CORS（允许 VitePress 文档站跨域访问）
CORS(app)

# 2. 注册模块 (APIBlueprint 会自动将 tags 汇合进文档)
app.register_api(chat_bp)
app.register_api(image_bp)

# 3. 根路由重定向
@app.route('/')
def index():
    return redirect('/openapi/scalar')

if __name__ == '__main__':
    # 注意：debug=True 时热重载会监听所有模块文件的修改
    app.run(host='0.0.0.0', port=5000, debug=True)
