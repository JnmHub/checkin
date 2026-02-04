from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db.session import engine
from app.models import Base
from app.api.v1.endpoints import checkin, employee_admin, login, admin_manage

# 自动建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="外勤打卡系统", version="1.0.0")

# --- 全局异常拦截：确保错误返回也是统一格式 ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """拦截所有 HTTPException (如 401, 403, 404)"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail, "data": None}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """拦截参数校验错误 (Pydantic 报错)"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "msg": "参数格式错误", "data": exc.errors()}
    )

# --- 注册路由 ---
app.include_router(login.router, prefix="/api/v1")
app.include_router(checkin.router, prefix="/api/v1")
app.include_router(employee_admin.router, prefix="/api/v1")
app.include_router(admin_manage.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"code": 200, "msg": "API 服务运行中", "data": None}