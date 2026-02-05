from fastapi import Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import Generator, Optional, Any, Coroutine, Annotated, Type

from sqlalchemy.testing.pickleable import User

from app.db.session import SessionLocal
from app.models import Employee, Admin
from app.core.config import settings
from app.core.cache import session_manager  # 导入你的内存缓存器


# 1. 数据库会话生成器
def get_db() -> Generator:
    """
    创建一个数据库连接，并在请求结束后自动关闭。
    这是 SQLAlchemy 在 FastAPI 中的标准用法。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

SessionDep = Annotated[Session, Depends(get_db)]
# 2. 核心：验证 Token 并获取当前员工 (从缓存+数据库双重校验)
async def get_current_employee(
        db: Session = Depends(get_db),
        # 从请求头中获取名为 token 的字段
        token: str = Header(..., description="登录时分发的 access_token")
) -> type[Employee]:
    """
    所有“员工端”需要登录的接口都依赖此函数。
    """
    # 定义通用的 401 异常
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="登录凭证已失效，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # --- 第一步：内存缓存校验 ---
    # 直接看内存里有没有这个牌，以及是否过期
    session_data = session_manager.get_session(token)
    if not session_data:
        # 如果缓存里没有（可能被管理员强制踢出、或已登出、或已过期）
        raise unauthorized_exception

    # 校验角色，确保不是管理员拿管理端的 Token 来刷员工接口
    if session_data.get("role") != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，非员工账号"
        )

    # --- 第二步：JWT 解密（二次确认数据完整性） ---
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        employee_id: str = payload.get("sub")
        if employee_id is None:
            raise unauthorized_exception
    except JWTError:
        # 如果 JWT 签名不对，虽然缓存过了，但也要防篡改
        raise unauthorized_exception

    # --- 第三步：数据库实时状态校验 ---
    # 这一步是为了防止：员工虽然在线，但管理员刚刚将其设为 is_active = False
    employee = db.query(Employee).filter(Employee.id == int(employee_id)).first()

    if not employee:
        # 账号不存在，顺手清理脏缓存
        session_manager.delete_session(token)
        raise HTTPException(status_code=404, detail="员工账号不存在")

    if not employee.is_active:
        # 如果账号被禁用，立即清理该用户在内存里的所有凭证
        session_manager.clear_user_sessions(employee.id, "employee")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您的账号已被禁用，请联系管理员"
        )

    # 验证通过，返回员工对象
    return employee


CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]

async def get_current_user(
        token: Optional[str] = Header(None, description="登录凭证"),
        query_token: Optional[str] = Query(None, description="登录凭证"),
):
    finsh_token = token or query_token
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="管理员登录失效",
        headers={"WWW-Authenticate": "Bearer"},
    )
    session_data = session_manager.get_session(finsh_token)
    if not session_data:
        raise unauthorized_exception
    return session_data

CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_current_admin(
    db: SessionDep,
    token: str = Header(..., description="管理员 access_token")
) -> Type[Admin]:
    """
    专门校验管理员身份的门卫
    """
    unauthorized_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="管理员登录失效",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. 查缓存
    session_data = session_manager.get_session(token)
    if not session_data or session_data.get("role") != "admin":
        raise unauthorized_exception

    # 2. 查数据库确认管理员还存在
    admin_id = session_data.get("user_id")
    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin:
        raise unauthorized_exception

    return admin

# --- 封装管理员极简指令 ---
CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]