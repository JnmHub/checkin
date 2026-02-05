from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
# 1. 导入 CORS 中间件
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.models import Base
from app.api.v1.endpoints import checkin, employee_admin, login, admin_manage, point_admin, dashboard, geo
from init_db import init_admin

# 自动建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="外勤打卡系统", version="1.0.0")

# 2. 配置 CORS
# 在生产环境下，这里应该写你前端的实际域名，开发环境下可以用 ["*"] 允许所有
origins = [
    "http://localhost:5173",  # Vue 默认开发地址
    "http://127.0.0.1:5173",
    "*"                       # 允许所有来源（仅限开发调试使用）
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # 允许的来源列表
    allow_credentials=True,           # 允许携带 Cookie
    allow_methods=["*"],              # 允许所有方法 (GET, POST, OPTIONS 等)
    allow_headers=["*"],              # 允许所有请求头 (如你自定义的 token 字段)
)

# --- 全局异常拦截 ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail, "data": None}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"code": 422, "msg": "参数格式错误", "data": exc.errors()}
    )

# --- 注册路由 ---
app.include_router(login.router, prefix="/api/v1")
app.include_router(checkin.router, prefix="/api/v1")
app.include_router(employee_admin.router, prefix="/api/v1")
app.include_router(admin_manage.router, prefix="/api/v1")
app.include_router(point_admin.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(geo.router, prefix="/api/v1")
@app.get("/")
async def root():
    return {"code": 200, "msg": "API 服务运行中", "data": None}

init_admin()