from fastapi import APIRouter, Depends
from datetime import datetime, time
from sqlalchemy import func
from app.api.deps import SessionDep, CurrentAdmin
from app.models import CheckInRecord, Employee
from app.schemas import Result
from app.core.cache import session_manager # 假设你之前的 Session 管理器

router = APIRouter(prefix="/admin/dashboard", tags=["管理端-工作台数据"])

@router.get("/stats", response_model=Result)
def get_dashboard_stats(db: SessionDep, current: CurrentAdmin):
    """
    获取工作台统计数据
    """
    # 1. 计算今日零点时间
    today_start = datetime.combine(datetime.now().date(), time.min)

    # 2. 统计今日签到人数 (去重，同一个员工多次签到只算一人)
    today_checkin_count = db.query(func.count(func.distinct(CheckInRecord.employee_id)))\
        .filter(CheckInRecord.create_time >= today_start)\
        .scalar() or 0

    # 3. 统计在线员工数
    # 如果你的 session_manager 支持获取活跃连接数
    # 这里假设 key 的格式是 "session:employee:*"
    online_employee_count = session_manager.get_active_count(prefix="employee")

    return Result.success(data={
        "today_checkin_count": today_checkin_count,    # 对应 128
        "online_employee_count": online_employee_count # 对应 45
    })