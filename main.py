from fastapi import FastAPI
from app.db.session import engine # 导入数据库引擎
from app.models import Base        # 导入模型基类
from app.api.v1.endpoints import checkin, employee_admin # 导入所有业务模块

# 1. 启动时自动在 MySQL 中创建表 (如果没有的话)
# 这行代码非常关键，它会扫描 app.models 里所有的类并同步到 MySQL
Base.metadata.create_all(bind=engine)

app = FastAPI(title="外勤打卡系统", version="1.0.0")

# 2. 像拼乐高一样把路由统一注册进来
# 所有的员工打卡相关接口：/api/v1/checkin/...
app.include_router(checkin.router, prefix="/api/v1")

# 所有的管理员操作员工接口：/api/v1/admin/employees/...
app.include_router(employee_admin.router, prefix="/api/v1")

@app.get("/")
async def root():
    """服务根路径测试"""
    return {"status": "running", "msg": "API 服务运行中"}