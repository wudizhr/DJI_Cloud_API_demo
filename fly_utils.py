import uuid
from geopy.distance import geodesic
from geopy.point import Point

def generate_uuid():
    """生成标准UUID格式的随机ID"""
    return str(uuid.uuid4())

def move_coordinates(lat, lon, distance_east, distance_north):
    """
    根据当前经纬度移动指定距离
    
    Args:
        lat: 当前纬度（度）
        lon: 当前经度（度）
        distance_east: 向东移动距离（米），负值表示向西
        distance_north: 向北移动距离（米），负值表示向南
    
    Returns:
        tuple: (新纬度, 新经度)
    """
    # 创建起点
    start = Point(latitude=lat, longitude=lon)
    
    # 先向北移动
    if distance_north != 0:
        bearing_north = 0 if distance_north > 0 else 180
        point_north = geodesic(kilometers=abs(distance_north)/1000).destination(
            start, bearing=bearing_north
        )
    else:
        point_north = start
    
    # 再向东移动
    if distance_east != 0:
        bearing_east = 90 if distance_east > 0 else 270
        final_point = geodesic(kilometers=abs(distance_east)/1000).destination(
            point_north, bearing=bearing_east
        )
    else:
        final_point = point_north
    
    return final_point.latitude, final_point.longitude

class FlightState:
    def __init__(self, lon=0, lat=0, height=0):
        self.lon = lon
        self.lat = lat
        self.height = height
        self.mode_code = -1