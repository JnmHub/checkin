from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
import httpx  # 用于发送异步网络请求
from app.api import deps
from app.models import Employee
from app.utils.auth import create_access_token
from app.utils.pwd import verify_password
from app.core.config import settings
from app.core.cache import session_manager  # 导入刚才写的内存缓存器

router = APIRouter(prefix="/auth", tags=["身份鉴权"])


@router.post("/wechat_login")
async def wechat_login(
        account: str = Body(..., description="管理员分发的账号"),
        password: str = Body(..., description="初始密码或设置后的密码"),
        code: str = Body(..., description="微信小程序通过 uni.login 拿到的 code"),
        db: Session = Depends(deps.get_db)
):
    """
    员工登录并绑定微信 OpenID，同时写入内存缓存
    """

    # 1. 查找员工
    employee = db.query(Employee).filter(Employee.account == account).first()

    # 2. 基础校验：账号存在性 & 密码正确性
    if not employee or not verify_password(password, employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误"
        )

    # 3. 校验账号状态
    if not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已被管理员禁用"
        )

    # 4. 拿着 code 去微信服务器换取 openid
    wechat_url = "https://api.weixin.qq.com/sns/jscode2session"
    # 注意：这里确保你的 settings 里面有这些字段，或者先写死测试
    params = {
        "appid": getattr(settings, "WECHAT_APPID", "你的小程序AppID"),
        "secret": getattr(settings, "WECHAT_SECRET", "你的小程序AppSecret"),
        "js_code": code,
        "grant_type": "authorization_code"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(wechat_url, params=params)
            res_data = response.json()

        if "openid" not in res_data:
            err_msg = res_data.get("errmsg", "未知微信接口错误")
            raise HTTPException(status_code=400, detail=f"微信登录失败: {err_msg}")

        openid = res_data["openid"]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"微信服务连接失败: {str(e)}")

    # 5. 绑定/校验 OpenID 逻辑
    if not employee.wechat_openid:
        # 第一次登录：进行静默绑定
        employee.wechat_openid = openid
        db.add(employee)
        db.commit()
    elif employee.wechat_openid != openid:
        # 已有绑定记录，但当前微信号不对
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账号已在其他微信上绑定，如需更换请联系管理员"
        )

    # 6. 生成 JWT 令牌
    # 过期时间从配置中读取 (单位：分钟)
    expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(data={"sub": str(employee.id)})

    # 7. 【核心新增】同步写入内存缓存
    # 将分钟转换为秒，确保缓存有效期与 Token 载明的过期时间完全一致
    session_manager.set_session(
        token=access_token,
        user_id=employee.id,
        role="employee",
        expire_in_seconds=expire_minutes * 60
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "employee_info": {
            "id": employee.id,
            "name": employee.name,
            "account": employee.account
        }
    }