import math

def get_haversine_distance(lat1, lon1, lat2, lon2):
    """
    计算两点经纬度之间的距离（单位：米）
    """
    R = 6371000  # 地球半径
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    res = 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return res