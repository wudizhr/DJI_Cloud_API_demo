import math
import numpy as np
import matplotlib.pyplot as plt

def visualize_footprint(drone_lat, drone_lon, corners):
    """可视化无人机位置和图像覆盖范围"""
    plt.figure(figsize=(10, 8))
    
    # 提取所有点的经纬度
    lats = [corner[0] for corner in corners] + [corners[0][0]]
    lons = [corner[1] for corner in corners] + [corners[0][1]]
    
    # 绘制图像覆盖范围
    plt.plot(lons, lats, 'b-', linewidth=2, label='图像覆盖范围')
    plt.fill(lons, lats, 'b', alpha=0.1)
    
    # 标记角点
    for i, (lat, lon) in enumerate(corners):
        plt.plot(lon, lat, 'ro', markersize=8)
        plt.text(lon, lat, f' 角点{i+1}', fontsize=12)
    
    # 标记无人机位置
    plt.plot(drone_lon, drone_lat, 'g^', markersize=15, label='无人机位置')
    plt.text(drone_lon, drone_lat, '  无人机', fontsize=12)
    
    plt.xlabel('经度 (°)')
    plt.ylabel('纬度 (°)')
    plt.title('无人机图像覆盖范围')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.axis('equal')
    plt.tight_layout()
    plt.show()

class DroneGeoLocator:
    def __init__(self, sensor_width_mm=8.5, sensor_height_mm=6.4, focal_length_mm=4.0, 
                 image_width_px=4000, image_height_px=3000):
        """
        初始化无人机地理定位器
        
        参数:
        sensor_width_mm: 传感器宽度 (毫米)
        sensor_height_mm: 传感器高度 (毫米)  
        focal_length_mm: 焦距 (毫米)
        image_width_px: 图像宽度 (像素)
        image_height_px: 图像高度 (像素)
        """
        self.sensor_width = sensor_width_mm / 1000.0  # 转换为米
        self.sensor_height = sensor_height_mm / 1000.0  # 转换为米
        self.focal_length = focal_length_mm / 1000.0  # 转换为米
        self.image_width = image_width_px
        self.image_height = image_height_px
        
        # 计算主点坐标（假设图像中心）
        self.cx = image_width_px / 2.0
        self.cy = image_height_px / 2.0
        
        # 计算像素尺寸 (假设像素是正方形的)
        self.pixel_size_x = self.sensor_width / image_width_px
        self.pixel_size_y = self.sensor_height / image_height_px
        
        print(f"初始化完成: 像素尺寸 {self.pixel_size_x*1e6:.2f} × {self.pixel_size_y*1e6:.2f} 微米")
    
    def calculate_gsd(self, altitude):
        """
        计算地面采样距离 (GSD) - 每个像素代表的地面距离
        
        参数:
        altitude: 飞行高度 (米)
        
        返回:
        gsd_x, gsd_y: X和Y方向的地面采样距离 (米/像素)
        """
        gsd_x = (self.pixel_size_x * altitude) / self.focal_length
        gsd_y = (self.pixel_size_y * altitude) / self.focal_length
        
        # print(f"高度 {altitude}米: GSD = {gsd_x:.3f} × {gsd_y:.3f} 米/像素")
        return gsd_x, gsd_y
    
    def pixel_to_geo_coordinates(self, drone_lat, drone_lon, altitude, pixel_x, pixel_y, yaw_deg=0):
        """
        将像素坐标转换为地理坐标
        
        参数:
        drone_lat: 无人机纬度 (度)
        drone_lon: 无人机经度 (度) 
        altitude: 飞行高度 (米)
        pixel_x: 目标像素X坐标 (从左上角开始)
        pixel_y: 目标像素Y坐标 (从左上角开始)
        yaw_deg: 偏航角 (度, 0度表示北, 90度表示东)
        
        返回:
        target_lat, target_lon: 目标点的经纬度坐标
        """
        # 计算地面采样距离
        gsd_x, gsd_y = self.calculate_gsd(altitude)
        
        # 计算像素相对于图像中心的偏移量
        dx_pixels = pixel_x - self.cx  # X方向像素偏移
        dy_pixels = pixel_y - self.cy  # Y方向像素偏移
        
        # print(f"像素偏移: dx={dx_pixels:.1f}, dy={dy_pixels:.1f} 像素")
        
        # 将像素偏移转换为地面距离偏移 (米)
        # 注意: 图像Y轴向下，所以dy取负号
        east_offset_m = dx_pixels * gsd_x
        north_offset_m = -dy_pixels * gsd_y
        
        # print(f"地面偏移 (未旋转): 东={east_offset_m:.2f}米, 北={north_offset_m:.2f}米")
        
        # 如果有偏航角，进行坐标旋转
        if abs(yaw_deg) > 1e-6:
            yaw_rad = math.radians(yaw_deg)
            # 旋转矩阵: 将机体坐标系转换到东北坐标系
            rotated_east = east_offset_m * math.cos(yaw_rad) - north_offset_m * math.sin(yaw_rad)
            rotated_north = east_offset_m * math.sin(yaw_rad) + north_offset_m * math.cos(yaw_rad)
            east_offset_m = rotated_east
            north_offset_m = rotated_north
            # print(f"地面偏移 (旋转后): 东={east_offset_m:.2f}米, 北={north_offset_m:.2f}米")
        
        # 将地面偏移转换为经纬度偏移
        # 注意: 这是近似计算，适用于小范围区域
        
        # 地球半径 (米)
        R = 6371000  # 平均半径
        
        # 纬度变化: 1度 ≈ 111,320米 (常数)
        lat_scale = 111320.0
        
        # 经度变化: 1度 ≈ 111,320 * cos(latitude) 米
        lon_scale = 111320.0 * math.cos(math.radians(drone_lat))
        
        # 计算经纬度变化量
        delta_lat = north_offset_m / lat_scale
        delta_lon = east_offset_m / lon_scale
        
        # 计算目标点经纬度
        target_lat = drone_lat + delta_lat
        target_lon = drone_lon + delta_lon
        
        # print(f"经纬度偏移: Δlat={delta_lat:.6f}°, Δlon={delta_lon:.6f}°")
        
        return target_lat, target_lon
    
    def calculate_image_footprint(self, drone_lat, drone_lon, altitude, yaw_deg=0):
        """
        计算整个图像的四个角点的地理坐标
        """
        corners = []
        corner_pixels = [
            (0, 0),  # 左上
            (self.image_width, 0),  # 右上
            (self.image_width, self.image_height),  # 右下
            (0, self.image_height)  # 左下
        ]
        
        for px, py in corner_pixels:
            lat, lon = self.pixel_to_geo_coordinates(drone_lat, drone_lon, altitude, px, py, yaw_deg)
            corners.append((lat, lon))
        
        return corners

# 使用示例
if __name__ == "__main__":
    # 初始化定位器 (使用典型消费级无人机参数)
    locator = DroneGeoLocator(
        sensor_width_mm=8.5,      # 典型1/1.5英寸传感器
        sensor_height_mm=6.4,     # 典型1/1.5英寸传感器
        focal_length_mm=168.0,      # 长焦镜头
        image_width_px=8000,      # 4K图像宽度
        image_height_px=6000      # 4K图像高度
    )
    
    # 无人机状态
    drone_lat = 31.2304    # 纬度 (例如: 上海)
    drone_lon = 121.4737   # 经度
    altitude = 100.0       # 高度 (米)
    yaw = -45.0             # 偏航角 (度)
    
    print("=" * 50)
    print("无人机地理定位计算")
    print("=" * 50)
    print(f"无人机位置: ({drone_lat:.4f}°, {drone_lon:.4f}°)")
    print(f"飞行高度: {altitude}米")
    print(f"偏航角: {yaw}°")
    print()
    
    # 示例1: 计算图像中心点
    print(">>> 计算图像中心点:")
    center_lat, center_lon = locator.pixel_to_geo_coordinates(
        drone_lat, drone_lon, altitude, locator.cx, locator.cy, yaw
    )
    print(f"图像中心: ({center_lat:.6f}°, {center_lon:.6f}°)")
    print()
    
    # 示例2: 计算特定像素点的坐标
    print(">>> 计算特定像素点 (1000, 1500):")
    target_x, target_y = 1000, 1500
    target_lat, target_lon = locator.pixel_to_geo_coordinates(
        drone_lat, drone_lon, altitude, target_x, target_y, yaw
    )
    print(f"像素点({target_x}, {target_y}): ({target_lat:.6f}°, {target_lon:.6f}°)")
    print()
    
    # 示例3: 计算图像覆盖范围
    print(">>> 计算图像四角坐标:")
    corners = locator.calculate_image_footprint(drone_lat, drone_lon, altitude, yaw)
    for i, (lat, lon) in enumerate(corners):
        corner_names = ["左上", "右上", "右下", "左下"]
        print(f"{corner_names[i]}: ({lat:.6f}°, {lon:.6f}°)")
    
    print()
    print("=" * 50)
    print("计算完成")
    print("=" * 50)
    # visualize_footprint(drone_lat, drone_lon, corners)