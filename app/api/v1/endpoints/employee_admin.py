from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.models import Employee
from app.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate

router = APIRouter(prefix="/admin/employees", tags=["管理端-员工管理"])


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(obj_in: EmployeeCreate, db: Session = Depends(deps.get_db)):
    """
    管理员分发账号：创建新员工
    """
    # 检查账号是否重复
    existing_employee = db.query(Employee).filter(Employee.account == obj_in.account).first()
    if existing_employee:
        raise HTTPException(status_code=400, detail="该账号已存在，请更换")

    # 创建实例
    db_obj = Employee(
        name=obj_in.name,
        account=obj_in.account,
        password_hash=obj_in.password,
        is_active=True
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get("/", response_model=List[EmployeeOut])
def list_employees(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db)):
    """
    获取员工列表
    """
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


@router.put("/{emp_id}", response_model=EmployeeOut)
def update_employee(emp_id: int, obj_in: EmployeeUpdate, db: Session = Depends(deps.get_db)):
    """
    修改员工信息或禁用账号
    """
    db_obj = db.query(Employee).filter(Employee.id == emp_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="未找到该员工")

    # 动态更新字段
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.delete("/{emp_id}")
def delete_employee(emp_id: int, db: Session = Depends(deps.get_db)):
    """
    删除员工账号（物理删除）
    """
    db_obj = db.query(Employee).filter(Employee.id == emp_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="未找到该员工")

    db.delete(db_obj)
    db.commit()
    return {"msg": "删除成功"}