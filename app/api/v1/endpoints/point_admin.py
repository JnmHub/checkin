from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from sqlalchemy.orm import joinedload

from app.api.deps import SessionDep, CurrentAdmin
from app.models import CheckInPoint, Employee
from app.schemas import PointCreate, PointOut, Result

router = APIRouter(prefix="/admin/points", tags=["管理端-打卡点管理"])


@router.post("/", response_model=Result[PointOut])
def create_point(obj_in: PointCreate, db: SessionDep, admin: CurrentAdmin):
    # 1. 提取员工 ID 列表并查询对应实例
    employee_list = db.query(Employee).filter(Employee.id.in_(obj_in.employee_ids)).all()

    # 2. 创建点位并关联员工
    db_obj = CheckInPoint(
        title=obj_in.title,
        address=obj_in.address,
        latitude=obj_in.latitude,
        longitude=obj_in.longitude,
        radius=obj_in.radius,
        employees=employee_list  # 建立关联
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return Result.success(data=db_obj)

@router.get("/", response_model=Result[List[PointOut]])
def list_points(db: SessionDep, admin: CurrentAdmin, keyword: Optional[str] = Query(None)):
    """获取打卡点列表（支持名称模糊搜索）"""
    points = db.query(CheckInPoint).options(joinedload(CheckInPoint.employees)).all()
    return Result.success(data=points)
    query = db.query(CheckInPoint)
    if keyword:
        query = query.filter(CheckInPoint.title.contains(keyword))
    return Result.success(data=query.all())

@router.delete("/{point_id}", response_model=Result)
def delete_point(point_id: int, db: SessionDep, admin: CurrentAdmin):
    """删除打卡点"""
    db_obj = db.query(CheckInPoint).filter(CheckInPoint.id == point_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="点位不存在")
    db.delete(db_obj)
    db.commit()
    return Result.success(msg="删除成功")


@router.put("/{point_id}", response_model=Result[PointOut])
def update_point(
        point_id: int,
        obj_in: PointCreate,
        db: SessionDep,
        admin: CurrentAdmin
):
    # 1. 查询现有的点位
    db_obj = db.query(CheckInPoint).filter(CheckInPoint.id == point_id).first()
    if not db_obj:
        return Result.fail(msg="点位不存在")

    # 2. 更新基础字段
    update_data = obj_in.model_dump(exclude={"employee_ids"})
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    # 3. 【关键】同步多对多关系
    # 查询前端传来的 ID 对应的所有员工对象
    new_employees = db.query(Employee).filter(Employee.id.in_(obj_in.employee_ids)).all()

    # 直接赋值，SQLAlchemy 会自动处理关联表（中间表）的增删
    db_obj.employees = new_employees

    db.commit()
    db.refresh(db_obj)
    return Result.success(data=db_obj)

