from fastapi import APIRouter, HTTPException, status, Body, Depends, Query
from typing import List, Optional
from app.api.deps import SessionDep, CurrentAdmin  # 使用简化后的指令
from app.models import Employee
from app.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate, Result  # 导入统一响应模型
from app.utils.pwd import get_password_hash
from app.core.cache import session_manager

router = APIRouter(prefix="/admin/employees", tags=["管理端-员工管理"])


@router.post("/", response_model=Result[EmployeeOut], status_code=status.HTTP_201_CREATED)
def create_employee(
        obj_in: EmployeeCreate,
        db: SessionDep,
        admin: CurrentAdmin  # 🔒 只有管理员有权创建
):
    """
    管理员分发账号：创建新员工
    """
    # 1. 检查账号是否重复
    existing_employee = db.query(Employee).filter(Employee.account == obj_in.account).first()
    if existing_employee:
        raise HTTPException(status_code=400, detail="该账号已存在，请更换")

    # 2. 创建实例（修正了密码加密 Bug）
    db_obj = Employee(
        name=obj_in.name,
        account=obj_in.account,
        password_hash=get_password_hash(obj_in.password),  # ✅ 存储哈希值，严禁明文
        is_active=True
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)

    return Result.success(data=db_obj, msg="员工账号分发成功")


@router.get("/", response_model=Result[List[EmployeeOut]])
def list_employees(
        db: SessionDep,
        admin: CurrentAdmin,
        name: Optional[str] = Query(None, description="按姓名模糊搜索"),
        account: Optional[str] = Query(None, description="按账号模糊搜索"),
        skip: int = 0,
        limit: int = 100
):
    """
    获取员工列表，支持按姓名或账号搜索
    """
    # 1. 开启查询
    query = db.query(Employee)

    # 2. 动态添加搜索过滤条件
    if name:
        # 相当于 SQL: WHERE name LIKE '%name%'
        query = query.filter(Employee.name.contains(name))
    if account:
        # 相当于 SQL: WHERE account LIKE '%account%'
        query = query.filter(Employee.account.contains(account))

    # 3. 分页并执行
    employees = query.offset(skip).limit(limit).all()

    return Result.success(data=employees)


@router.put("/{emp_id}", response_model=Result[EmployeeOut])
def update_employee(
        emp_id: int,
        obj_in: EmployeeUpdate,
        db: SessionDep,
        admin: CurrentAdmin
):
    """
    修改员工信息或禁用账号
    """
    db_obj = db.query(Employee).filter(Employee.id == emp_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="未找到该员工")

    update_data = obj_in.model_dump(exclude_unset=True)

    # 核心：如果管理员禁用了该账号，必须立即清空该用户的内存凭证
    if update_data.get("is_active") is False:
        session_manager.clear_user_sessions(emp_id, "employee")

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return Result.success(data=db_obj, msg="资料更新成功")


@router.post("/{emp_id}/reset_password", response_model=Result)
def reset_employee_password(
        emp_id: int,
        db: SessionDep,
        admin: CurrentAdmin,
        new_password: str = Body(..., embed=True),

):
    """
    管理员强制重置员工密码
    """
    employee = db.query(Employee).filter(Employee.id == emp_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")

    # 1. 更新加密密码
    employee.password_hash = get_password_hash(new_password)
    db.add(employee)
    db.commit()

    # 2. 核心：密码变动，强制该员工所有设备下线
    session_manager.clear_user_sessions(emp_id, "employee")

    return Result.success(msg=f"已重置员工 {employee.name} 的密码，并强制其重新登录")


@router.delete("/{emp_id}", response_model=Result)
def delete_employee(
        emp_id: int,
        db: SessionDep,
        admin: CurrentAdmin
):
    """
    删除员工账号
    """
    db_obj = db.query(Employee).filter(Employee.id == emp_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="未找到该员工")

    # 删除前先清理缓存凭证
    session_manager.clear_user_sessions(emp_id, "employee")

    db.delete(db_obj)
    db.commit()
    return Result.success(msg="员工账号已物理删除")
