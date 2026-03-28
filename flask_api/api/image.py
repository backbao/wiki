from flask_openapi3 import APIBlueprint, Tag
from pydantic import BaseModel, Field

# 定义 Tag
image_tag = Tag(name="ImageService", description="AI 绘图相关接口")
# 创建蓝图
image_bp = APIBlueprint('image', __name__, url_prefix='/api/image', abp_tags=[image_tag])

class ImageRequest(BaseModel):
    prompt: str = Field(..., description="画图的提示词", json_schema_extra={"example": "一只有翅膀的猫"})
    size: str = Field("1024x1024", description="图片分辨率")

class ImageResponse(BaseModel):
    image_url: str = Field(..., description="生成好的图片地址")

@image_bp.post('/generate', responses={"200": ImageResponse})
def generate_image(body: ImageRequest):
    """
    根据提示词生成图片
    """
    return {"image_url": "https://example.com/generated-image.jpg"}
