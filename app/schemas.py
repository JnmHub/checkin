from pydantic import BaseModel, model_validator
from typing import Optional, Any, Generic, TypeVar, T, List
from datetime import datetime


class Config:
    from_attributes = True  # 允许 SQLAlchemy 对象直接转换

    T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """
    全局统一响应格式
    """
    code: int = 200  # 业务状态码 (200:成功, 400:业务错误, 401:未登录, 500:系统错误)
    msg: str = "success"  # 提示信息
    data: Optional[T] = None  # 实际业务数据

    @classmethod
    def success(cls, data: Any = None, msg: str = "success"):
        """成功响应的快捷方式"""
        return {"code": 200, "msg": msg, "data": data}

    @classmethod
    def error(cls, code: int = 400, msg: str = "error"):
        """失败响应的快捷方式"""
        return {"code": code, "msg": msg, "data": None}


class PasswordUpdate(BaseModel):
    old_password: str  # 旧密码，用于身份二次确认
    new_password: str  # 新密码


# 响应模型基类
class PointBase(BaseModel):
    title: str
    address: str
    latitude: float
    longitude: float
    radius: int = 500
    employee_ids: List[int] = []


class PointCreate(BaseModel):
    title: str
    address: str
    latitude: float
    longitude: float
    radius: int
    employee_ids: List[int] = [] # 接收员工 ID 列表


class PointOut(BaseModel):
    id: int
    title: str
    address: str
    latitude: float
    longitude: float
    radius: int
    # 确保字段名与你返回的 JSON 一致
    employee_ids: List[int] = []

    @model_validator(mode='before')
    @classmethod
    def map_relationship_to_ids(cls, data: Any) -> Any:
        # 如果 data 是 SQLAlchemy 模型实例
        if hasattr(data, "employees"):
            # 将关联的 Employee 对象列表转为 ID 列表
            # 注意：这里需要确保查询时使用了 joinedload
            data.employee_ids = [emp.id for emp in data.employees]
        return data

    class Config:
        from_attributes = True


# --- 员工相关 Schema ---

class EmployeeBase(BaseModel):
    name: str  # 员工姓名
    account: str  # 登录账号


class EmployeeCreate(EmployeeBase):
    password: str  # 创建时只需要姓名和账号


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeOut(EmployeeBase):
    id: int
    is_active: bool
    wechat_openid: Optional[str] = None  # 初始为空，登录后绑定

    class Config:
        from_attributes = True  # 必须加上这一行

# --- 管理员相关 Schema ---

class AdminBase(BaseModel):
    username: str

class AdminCreate(AdminBase):
    password: str

class AdminUpdate(BaseModel):
    username: Optional[str] = None

class AdminOut(AdminBase):
    id: int
    class Config:
        from_attributes = True

class AdminPasswordUpdate(BaseModel):
    old_password: str  # 当前密码
    new_password: str  # 新密码