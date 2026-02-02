from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 响应模型基类
class PointBase(BaseModel):
    title: str
    latitude: float
    longitude: float
    radius: int = 500

class PointCreate(PointBase):
    address: str

class PointOut(PointBase):
    id: int
    class Config:
        from_attributes = True # 允许从 SQLAlchemy 模型转换



# --- 员工相关 Schema ---

class EmployeeBase(BaseModel):
    name: str     # 员工姓名
    account: str  # 登录账号

class EmployeeCreate(EmployeeBase):
    password: str # 创建时只需要姓名和账号

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeOut(EmployeeBase):
    id: int
    is_active: bool
    wechat_openid: Optional[str] = None # 初始为空，登录后绑定

    class Config:
        from_attributes = True # 允许 SQLAlchemy 对象直接转换