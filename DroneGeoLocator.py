import math
import numpy as np
import matplotlib.pyplot as plt

class DroneGeoLocator:
    def __init__(self, sensor_width_mm=8.5, sensor_height_mm=6.4, focal_length_mm=4.0, 
                 image_width_px=4000, image_height_px=3000):
        """
        增强版无人机地理定位器 - 支持视场区域映射
        """
        self.sensor_width = sensor_width_mm / 1000.0
        self.sensor_height = sensor_height_mm / 1000.0
        self.focal_length = focal_length_mm / 1000.0
        self.image_width = image_width_px
        self.image_height = image_height_px
        
        # 计算像素尺寸
        self.pixel_size_x = self.sensor_width / image_width_px
        self.pixel_size_y = self.sensor_height / image_height_px
        
        # 默认使用全画幅
        self.liveview_region = {
            'left': 0.0, 'top': 0.0, 
            'right': 1.0, 'bottom': 1.0
        }

        self.set_liveview_region(
            bottom = 0.57754391431808472,
            left = 0.41962304711341858,
            right = 0.584352672100067,
            top = 0.41050803661346436
        )
        
        print(f"初始化完成: 传感器 {sensor_width_mm}×{sensor_height_mm}mm, 焦距 {focal_length_mm}mm")
    
    def set_liveview_region(self, left, top, right, bottom):
        """
        设置liveview中的视场区域（标准化坐标）
        
        参数:
        left, top, right, bottom: 在[0,1]范围内的标准化坐标
        """
        self.liveview_region = {
            'left': left, 'top': top, 
            'right': right, 'bottom': bottom
        }
        print(f"设置视场区域: left={left:.3f}, top={top:.3f}, right={right:.3f}, bottom={bottom:.3f}")
    
    def _pixel_to_sensor_coords(self, pixel_x, pixel_y):
        """
        将像素坐标转换到传感器物理坐标
        """
        # 将liveview区域映射到传感器坐标
        sensor_x = (pixel_x / self.image_width) * (self.liveview_region['right'] - self.liveview_region['left']) + self.liveview_region['left']
        sensor_y = (pixel_y / self.image_height) * (self.liveview_region['bottom'] - self.liveview_region['top']) + self.liveview_region['top']
        
        # 转换为物理坐标（米），原点在传感器中心
        phys_x = (sensor_x - 0.5) * self.sensor_width
        phys_y = (0.5 - sensor_y) * self.sensor_height  # Y轴反转
        
        return phys_x, phys_y
    
    def calculate_gsd(self, altitude):
        """计算地面采样距离"""
        gsd_x = (self.pixel_size_x * altitude) / self.focal_length
        gsd_y = (self.pixel_size_y * altitude) / self.focal_length
        return gsd_x, gsd_y
    
    def pixel_to_geo_coordinates(self, drone_lat, drone_lon, altitude, pixel_x, pixel_y, yaw_deg=0):
        """
        增强版像素到地理坐标转换（考虑liveview区域）
        """
        # 计算传感器物理坐标
        sensor_x, sensor_y = self._pixel_to_sensor_coords(pixel_x, pixel_y)
        
        # 计算地面偏移（透视投影）
        # 使用相似三角形原理
        east_offset_m = (sensor_x * altitude) / self.focal_length
        north_offset_m = (sensor_y * altitude) / self.focal_length
        
        # 偏航角旋转
        if abs(yaw_deg) > 1e-6:
            yaw_rad = math.radians(yaw_deg)
            rotated_east = east_offset_m * math.cos(yaw_rad) - north_offset_m * math.sin(yaw_rad)
            rotated_north = east_offset_m * math.sin(yaw_rad) + north_offset_m * math.cos(yaw_rad)
            east_offset_m = rotated_east
            north_offset_m = rotated_north
        
        # 转换为经纬度
        return self._offset_to_geocoords(drone_lat, drone_lon, east_offset_m, north_offset_m)
    
    def _offset_to_geocoords(self, base_lat, base_lon, east_m, north_m):
        """将东北方向偏移转换为经纬度"""
        lat_scale = 111320.0  # 1度纬度 ≈ 111.32km
        lon_scale = 111320.0 * math.cos(math.radians(base_lat))
        
        delta_lat = north_m / lat_scale
        delta_lon = east_m / lon_scale
        
        target_lat = base_lat + delta_lat
        target_lon = base_lon + delta_lon
        
        return target_lat, target_lon
    
    def calculate_effective_fov(self):
        """
        计算有效的视场角（考虑liveview区域）
        """
        # 计算实际使用的传感器尺寸
        effective_width = self.sensor_width * (self.liveview_region['right'] - self.liveview_region['left'])
        effective_height = self.sensor_height * (self.liveview_region['bottom'] - self.liveview_region['top'])
        
        # 计算视场角
        hfov = 2 * math.atan(effective_width / (2 * self.focal_length))
        vfov = 2 * math.atan(effective_height / (2 * self.focal_length))
        
        return math.degrees(hfov), math.degrees(vfov)
    
    def calculate_image_footprint(self, drone_lat, drone_lon, altitude, yaw_deg=0):
        """
        计算实际显示区域的四个角点
        """
        corners = []
        # liveview区域的四个角点
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
    # 初始化定位器
    locator = DroneGeoLocator(
        sensor_width_mm=8.5,
        sensor_height_mm=6.4, 
        focal_length_mm=168.0,
        image_width_px=8000,
        image_height_px=6000
    )
    
    # 设置您提供的liveview区域数据
    locator.set_liveview_region(
        left=0.0567445233464241,
        top=0.04445141926407814, 
        right=0.94628465175628662,
        bottom=0.9464452862739563
    )
    
    # 无人机状态
    drone_lat = 31.2304
    drone_lon = 121.4737
    altitude = 100.0
    yaw = -45.0
    
    print("=" * 60)
    print("增强版无人机地理定位计算")
    print("=" * 60)
    
    # 计算有效视场角
    hfov, vfov = locator.calculate_effective_fov()
    print(f"有效视场角: {hfov:.2f}° × {vfov:.2f}°")
    print(f"使用的传感器区域: {locator.liveview_region['right'] - locator.liveview_region['left']:.1%} × {locator.liveview_region['bottom'] - locator.liveview_region['top']:.1%}")
    print()
    
    # 计算图像中心
    center_x, center_y = locator.image_width // 2, locator.image_height // 2
    center_lat, center_lon = locator.pixel_to_geo_coordinates(
        drone_lat, drone_lon, altitude, center_x, center_y, yaw
    )
    print(f"图像中心: ({center_lat:.6f}°, {center_lon:.6f}°)")
    
    # 计算覆盖范围
    corners = locator.calculate_image_footprint(drone_lat, drone_lon, altitude, yaw)
    corner_names = ["左上", "右上", "右下", "左下"]
    for i, (lat, lon) in enumerate(corners):
        print(f"{corner_names[i]}: ({lat:.6f}°, {lon:.6f}°)")