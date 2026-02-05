import io
from datetime import datetime, time
from typing import List

import httpx
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from starlette import status
from starlette.responses import StreamingResponse

from app.api import deps
from app.api.deps import get_current_employee, CurrentEmployee, SessionDep, CurrentUser
from app.core.config import minio_client, settings  # 假设你把 MinIO 配置放到了 core
import uuid

from app.models import Employee, CheckInPoint, CheckInRecord
from app.schemas import Result, PointOut, CheckInRecordOut
from app.utils.geo import get_haversine_distance

# 创建路由对象，可以统一加前缀和标签
router = APIRouter(prefix="/checkin", tags=["员工打卡模块"])



# app/api/v1/endpoints/checkin.py

@router.get("/my_points", response_model=Result[List[PointOut]])
def get_my_points(current_employee: CurrentEmployee, db: SessionDep):
    """
    员工端接口：获取当前登录员工拥有的打卡点
    """
    return Result.success(data=current_employee.checkin_points)


@router.post("/upload")
async def employee_checkin(
        db: SessionDep,
        current_employee: CurrentEmployee,
        point_id: int = Form(..., description="打卡点ID"),
        lat: float = Form(..., description="实际打卡纬度"),
        lon: float = Form(..., description="实际打卡经度"),
        address: str = Form(..., description="打卡位置"),
        file: UploadFile = File(..., description="打卡现场照片")
):
    """
    完善后的打卡接口：包含重复打卡校验、距离校验、MinIO存储及入库
    """
    # 1. 基础校验：文件类型
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只能上传图片文件")

    # # 2. 【核心新增】重复打卡校验：判断该员工今天是否已在当前点位打过卡
    # today_start = datetime.combine(datetime.now().date(), time.min)
    # today_end = datetime.combine(datetime.now().date(), time.max)
    #
    # existing_record = db.query(CheckInRecord).filter(
    #     CheckInRecord.employee_id == current_employee.id,
    #     CheckInRecord.point_id == point_id,
    #     CheckInRecord.create_time >= today_start,
    #     CheckInRecord.create_time <= today_end
    # ).first()
    #
    # if existing_record:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="您今日已在此点位完成打卡，请勿重复提交"
    #     )

    # 3. 距离安全校验
    point = db.query(CheckInPoint).filter(CheckInPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="打卡点不存在")

    actual_distance = get_haversine_distance(lat, lon, point.latitude, point.longitude)
    if actual_distance > (point.radius + 50):  # 允许50米GPS偏差
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"打卡位置异常：距离目标点 {round(actual_distance)}米，超出范围"
        )

    # 4. MinIO 存储处理
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_name = f"checkin/{current_employee.id}/{uuid.uuid4()}.{ext}"

    try:
        # 确保存储桶存在
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)

        minio_client.put_object(
            settings.MINIO_BUCKET,
            file_name,
            file.file,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片存档失败: {str(e)}")

    # 5. 存入数据库
    new_record = CheckInRecord(
        employee_id=current_employee.id,
        point_id=point_id,
        photo_url=file_name,
        lat=lat,
        lon=lon,
        location_name=address or "位置解析失败"
    )

    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    return Result.success(data={
        "record_id": new_record.id,
        "distance": round(actual_distance, 2)
    }, msg="打卡成功！")

@router.get("/my_records", response_model=Result[List[CheckInRecordOut]])
def get_my_records(
    db: SessionDep,
    current_employee: CurrentEmployee,
    limit: int = 20,
    skip: int = 0
):
    """
    获取当前员工的打卡历史记录
    """
    # 联表查询，获取打卡记录及其对应的点位名称
    records = db.query(
        CheckInRecord.id,
        CheckInRecord.create_time,
        CheckInRecord.location_name,
        CheckInRecord.photo_url,
        CheckInRecord.point_id,
        CheckInPoint.title.label("point_title")
    ).join(
        CheckInPoint, CheckInRecord.point_id == CheckInPoint.id
    ).filter(
        CheckInRecord.employee_id == current_employee.id
    ).order_by(
        CheckInRecord.create_time.desc() # 按时间倒序
    ).offset(skip).limit(limit).all()

    return Result.success(data=records)


@router.get("/view_photo")
async def view_photo(
        current_user: CurrentUser,
        photo_path: str = Query(..., description="MinIO中的文件路径")
):
    """
    后端中转图片流：高性能、高安全性方案
    """
    response = None
    try:
        # 1. 安全性检查（可选）：确保路径只在 checkin 目录下
        if not photo_path.startswith("checkin/"):
             raise HTTPException(status_code=403, detail="非法访问路径")

        # 2. 从 MinIO 获取流式对象
        # 注意：不要使用 .read()，直接获取响应对象
        response = minio_client.get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=photo_path
        )

        # 3. 这里的 response 是一个类文件对象（Iterable）
        # StreamingResponse 可以直接接收这个生成器进行流式返回，内存占用极低
        return StreamingResponse(
            response,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "max-age=3600" # 建议加上缓存控制，减轻后端压力
            }
        )

    except Exception as e:
        # 打印日志方便调试
        print(f"读取图片失败: {photo_path}, 错误: {str(e)}")
        raise HTTPException(status_code=404, detail="图片不存在或无法读取")

