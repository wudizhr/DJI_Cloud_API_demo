from geopy.distance import geodesic
from geopy.point import Point

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

# 使用示例
if __name__ == "__main__":
    # 示例：北京天安门坐标
    lat, lon = 39.9087, 116.3976
    
    # 向东移动100米，向北移动50米
    new_lat, new_lon = move_coordinates(lat, lon, 100, 50)
    
    print(f"原始坐标: ({lat}, {lon})")
    print(f"移动后坐标: ({new_lat:.6f}, {new_lon:.6f})")