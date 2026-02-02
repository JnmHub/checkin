from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from app.api.deps import get_current_employee, CurrentEmployee
from app.core.config import minio_client, settings  # 假设你把 MinIO 配置放到了 core
import uuid

from app.models import Employee

# 创建路由对象，可以统一加前缀和标签
router = APIRouter(prefix="/checkin", tags=["员工打卡模块"])


@router.post("/upload")
async def employee_checkin(
        current_employee: CurrentEmployee,
        employee_id: int = Form(..., description="员工ID"),
        lat: float = Form(..., description="打卡纬度"),
        lon: float = Form(..., description="打卡经度"),
        file: UploadFile = File(..., description="打卡现场照片")
):
    """
    员工打卡接口：上传照片并记录位置
    """
    # 校验文件类型（简单示例）
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # 生成唯一文件名
    file_name = f"{uuid.uuid4()}.jpg"

    try:
        # 上传到 MinIO
        minio_client.put_object(
            settings.MINIO_BUCKET,
            file_name,
            file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type
        )
        return {"status": "success", "photo_key": file_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储失败: {str(e)}")