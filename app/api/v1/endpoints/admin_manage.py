from fastapi import APIRouter, HTTPException, status, Body, Depends, Query
from typing import List, Optional
from app.api.deps import SessionDep, CurrentAdmin
from app.models import Admin
from app.schemas import AdminCreate, AdminOut, AdminUpdate, Result, PasswordUpdate, AdminPasswordUpdate
from app.utils.pwd import get_password_hash, verify_password
from app.core.cache import session_manager

router = APIRouter(prefix="/admin/manage", tags=["管理端-管理员管理"])


@router.post("/", response_model=Result[AdminOut])
def create_admin(
        obj_in: AdminCreate,
        db: SessionDep,
        current: CurrentAdmin
):
    """创建管理员"""
    existing = db.query(Admin).filter(Admin.username == obj_in.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户名已存在")

    db_obj = Admin(
        username=obj_in.username,
        password_hash=get_password_hash(obj_in.password)  # 必须加密
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return Result.success(data=db_obj, msg="管理员创建成功")


@router.get("/", response_model=Result[List[AdminOut]])
def list_admins(
        db: SessionDep,
        current: CurrentAdmin,
        username: Optional[str] = Query(None, description="按用户名模糊搜索"),
        skip: int = 0,
        limit: int = 20
):
    """
    获取管理员列表，支持按用户名搜索
    """
    query = db.query(Admin)

    # 动态过滤
    if username:
        query = query.filter(Admin.username.contains(username))

    admins = query.offset(skip).limit(limit).all()

    return Result.success(data=admins)


@router.put("/{admin_id}", response_model=Result[AdminOut])
def update_admin(
        admin_id: int,
        obj_in: AdminUpdate,
        db: SessionDep,
        current: CurrentAdmin
):
    """编辑管理员信息（如修改用户名）"""
    db_obj = db.query(Admin).filter(Admin.id == admin_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="管理员不存在")

    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return Result.success(data=db_obj)


@router.post("/{admin_id}/password", response_model=Result)
def change_admin_password(
        db: SessionDep,
        current: CurrentAdmin,
        admin_id: int,
        new_password: str = Body(..., embed=True),

):
    """修改管理员密码"""
    db_obj = db.query(Admin).filter(Admin.id == admin_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 1. 更新加密密码
    db_obj.password_hash = get_password_hash(new_password)
    db.add(db_obj)
    db.commit()

    # 2. 核心：强制该管理员所有登录失效，要求重新登录
    session_manager.clear_user_sessions(admin_id, "admin")

    return Result.success(msg="密码已修改，相关设备已强制下线")


@router.delete("/{admin_id}", response_model=Result)
def delete_admin(
        admin_id: int,
        db: SessionDep,
        current: CurrentAdmin
):
    """删除管理员"""
    # 防止管理员删掉自己
    if admin_id == current.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的管理员账号")

    db_obj = db.query(Admin).filter(Admin.id == admin_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="管理员不存在")

    # 删除前清理缓存
    session_manager.clear_user_sessions(admin_id, "admin")

    db.delete(db_obj)
    db.commit()
    return Result.success(msg="管理员账号已移除")

@router.post("/password_myself", response_model=Result)
def change_admin_password_myself(
    obj_in: AdminPasswordUpdate, # 使用新定义的 Schema
    db: SessionDep,
    current: CurrentAdmin,
):
    """
    修改管理员密码（带原密码验证）
    """
    admin_id = current.id

    db_obj = db.query(Admin).filter(Admin.id == admin_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 3. 【核心】验证原密码是否正确
    if not verify_password(obj_in.old_password, db_obj.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误，请重新输入")

    # 4. 更新加密后的新密码
    db_obj.password_hash = get_password_hash(obj_in.new_password)
    db.add(db_obj)
    db.commit()

    # 5. 强制清除 Session，让所有设备重新登录
    session_manager.clear_user_sessions(admin_id, "admin")

    return Result.success(msg="密码已更新，请重新登录")