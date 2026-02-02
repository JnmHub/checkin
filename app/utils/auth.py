from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from app.core.config import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    生成 JWT Token
    :param data: 包含用户 ID 等信息的数据字典
    :param expires_delta: 有效时长
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 如果不传，默认使用 config 里的过期时间
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # 注入过期时间字段 exp
    to_encode.update({"exp": expire})
    # 使用 SECRET_KEY 进行签名加密
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """
    校验 Token 是否合法且未过期
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload  # 返回解密后的内容，如 {"sub": "employee_id"}
    except JWTError:
        return None