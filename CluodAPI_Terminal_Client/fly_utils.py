import uuid
from geopy.distance import geodesic
from geopy.point import Point
import time

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

class Time_counter:
    def __init__(self, last_time=0, now_time=0):
        self.last_time = last_time
        self.now_time = now_time
        self.update_last()
        self.update_now()

    def update_last(self):
        self.last_time = self.now_time

    def update_now(self):
        self.now_time = time.time()

    def get_time_minus(self):
        return self.now_time - self.last_time

class FlightState:
    mode_dict = {0:"待机",1:"起飞准备",2:"起飞准备完毕",3:"手动飞行",
                 4:"自动起飞",5:"航线飞行",6:"全景拍照",7:"智能跟随",
                 8:"ADS-B 躲避",9:"自动返航",10:"自动降落",11:"强制降落",
                 12:"三桨叶降落",13:"升级中",14:"未连接",15:"APAS",
                 16:"虚拟摇杆状态",17:"指令飞行"}
    def __init__(self):
        self.lon = None
        self.lat = None
        self.height = None
        self.attitude_head = None
        self.mode_code = None
        self.takeoff_height = None
        self.battery_percentage = None
        self.device_sn = None
        self.elevation = None

    def get_uav_info_str(self):
        # 将每个属性单独成行，便于在终端或 TUI 中分行显示
        lines = [
            f"经度: {self.lon if self.lon is not None else '未知'}",
            f"纬度: {self.lat if self.lat is not None else '未知'}",
            f"高度: {self.height:.2f} 米" if self.height is not None else '高度: 未知',
            f"相对起飞高度: {self.elevation:.2f} 米" if self.elevation is not None else '相对起飞高度: 未知',
            f"航向: {self.attitude_head if self.attitude_head is not None else '未知'} 度",
            f"模式: {self.mode_dict.get(self.mode_code, '未知模式') if self.mode_code is not None else '未知'}",
            f"电池电量: {self.battery_percentage if self.battery_percentage is not None else '未知'}%",
            f"设备SN: {self.device_sn if self.device_sn is not None else '未知'}",
        ]
        return "\n".join(lines)


def get_points_from_txt(filename, height):
    coordinates = []
    with open(filename, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('['):
                parts = line.split()
                if len(parts) >= 3:
                    # 文件中格式：序号 纬度 经度
                    # 转换为：[经度, 纬度]
                    latitude = float(parts[2])
                    longitude = float(parts[1])
                    coordinates.append([longitude, latitude, height])
    return coordinates