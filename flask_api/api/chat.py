from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

# 定义 Tag
chat_tag = Tag(name="ChatService", description="AI 聊天相关接口")
# 创建蓝图
chat_bp = APIBlueprint('chat', __name__, url_prefix='/api/chat', abp_tags=[chat_tag])

# 数据结构
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的聊天内容", json_schema_extra={"example": "你好"})
    model_id: str = Field("gpt-4", description="使用的模型ID")
    is_stream: bool = Field(True, description="是否开启流式传输模式")

class ChatResponse(BaseModel):
    success: bool
    reply: str = Field(..., description="AI 的回复内容")

# 接口
@chat_bp.post('/', responses={"200": ChatResponse})
def chat(body: ChatRequest):
    """发送聊天消息"""
    return {"success": True, "reply": f"收到了你的消息: {body.message}"}

@chat_bp.get('/history')
def get_history():
    """获取聊天历史"""
    return {"success": True, "data": []}

@chat_bp.get('/end')
def end_chat():
    """
    结束当前对话
    """
    return {"success": True}
