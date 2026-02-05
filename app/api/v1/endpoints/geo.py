import httpx
from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CurrentEmployee
from app.core.config import settings
from app.schemas import Result

router = APIRouter(prefix="/geo", tags=["地理位置服务"])


@router.get("/regeo", response_model=Result)
async def reverse_geocoding(
        current_employee: CurrentEmployee,
        lat: float = Query(..., description="纬度"),
        lon: float = Query(..., description="经度")
):
    """
    逆地理编码：经纬度转文字地址
    """
    # 高德逆地理编码 API 地址
    url = "https://restapi.amap.com/v3/geocode/regeo"

    params = {
        "key": settings.AMAP_WEB_KEY,
        "location": f"{lon},{lat}",  # 高德要求格式：经度,纬度
        "extensions": "base",  # 只返回基本地址信息
        "output": "JSON"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=5.0)
            res_data = response.json()

        # 校验高德返回状态 (1代表成功)
        if res_data.get("status") == "1":
            regeocode = res_data.get("regeocode", {})
            address = regeocode.get("formatted_address", "未知地址")

            # 返回给前端
            return Result.success(data={"address": address})
        else:
            error_info = res_data.get("info", "请求高德接口失败")
            raise HTTPException(status_code=400, detail=f"逆地理编码失败: {error_info}")

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"地图服务连接超时: {str(e)}")