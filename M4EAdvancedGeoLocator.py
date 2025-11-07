class M4EAdvancedGeoLocator:
    """支持变焦的M4E地理定位器"""
    
    def __init__(self):
        # 完整的相机配置
        self.camera_configs = {
            'wide_angle': {
                'sensor_width': 17.3,    # mm
                'sensor_height': 13.0,   # mm
                'image_width': 5184,     # 像素
                'image_height': 3888,    # 像素
                'focal_length_equiv': 24,# 等效焦距 mm
                'fov': 84,               # 视野角度
                'zoom_range': [1, 2],    # 变焦范围
                'name': '广角相机(4/3 CMOS)'
            },
            'medium_tele': {
                'sensor_width': 9.6,     # mm
                'sensor_height': 7.2,    # mm
                'image_width': 8000,     # 像素
                'image_height': 6000,    # 像素
                'focal_length_equiv': 70,# 等效焦距 mm
                'fov': 35,               # 视野角度
                'zoom_range': [3, 5],    # 变焦范围
                'name': '中长焦相机(1/1.3" CMOS)'
            },
            'telephoto': {
                'sensor_width': 8.5,     # mm
                'sensor_height': 6.4,    # mm
                'image_width': 8000,     # 像素
                'image_height': 6000,    # 像素
                'focal_length_equiv': 168,# 等效焦距 mm
                'fov': 15,               # 视野角度
                'zoom_range': [6, 7],    # 变焦范围
                'name': '长焦相机(1/1.5" CMOS)'
            }
        }
        
        self.current_zoom = 1
        self.current_camera = 'wide_angle'
        
    def set_zoom(self, zoom_level):
        """设置变焦倍数并自动切换相机"""
        if not (1 <= zoom_level <= 7):
            raise ValueError("变焦倍数必须在1-7倍之间")
        
        # 根据变焦倍数选择相机
        if zoom_level <= 2:
            new_camera = 'wide_angle'
        elif zoom_level <= 5:
            new_camera = 'medium_tele' 
        else:
            new_camera = 'telephoto'
        
        # 如果切换了相机，更新配置
        if new_camera != self.current_camera:
            self.current_camera = new_camera
            print(f"相机切换: {self.camera_configs[new_camera]['name']}")
        
        self.current_zoom = zoom_level
        config = self.camera_configs[self.current_camera]
        
        print(f"当前设置: 变焦 {zoom_level}x, {config['name']}")
        print(f"等效焦距: {config['focal_length_equiv']}mm, 视野: {config['fov']}°")
        
    def calculate_performance(self, altitude):
        """计算当前设置下的性能指标"""
        config = self.camera_configs[self.current_camera]
        
        # 计算像素尺寸
        pixel_size_x = config['sensor_width'] / config['image_width']
        pixel_size_y = config['sensor_height'] / config['image_height']
        
        # 计算GSD
        gsd_x = (pixel_size_x * altitude) / (config['focal_length_equiv'] / 1000)
        gsd_y = (pixel_size_y * altitude) / (config['focal_length_equiv'] / 1000)
        
        # 计算地面覆盖范围
        ground_width = (config['sensor_width'] / 1000 * altitude) / (config['focal_length_equiv'] / 1000)
        ground_height = (config['sensor_height'] / 1000 * altitude) / (config['focal_length_equiv'] / 1000)
        
        return {
            'gsd_x': gsd_x,
            'gsd_y': gsd_y,
            'ground_width': ground_width,
            'ground_height': ground_height,
            'pixel_size_x': pixel_size_x,
            'pixel_size_y': pixel_size_y
        }

# 测试变焦系统的性能
def test_zoom_performance():
    """测试不同变焦倍数下的性能"""
    locator = M4EAdvancedGeoLocator()
    altitude = 200  # 飞行高度200米
    
    print("M4E在不同变焦倍数下的性能对比 (高度: 200米)")
    print("=" * 80)
    print(f"{'变焦':<6} {'相机':<15} {'GSD(cm/像素)':<15} {'地面覆盖(m)':<20} {'视野角度':<10}")
    print("-" * 80)
    
    for zoom in [1, 3, 5, 7]:
        locator.set_zoom(zoom)
        perf = locator.calculate_performance(altitude)
        
        camera_name = locator.camera_configs[locator.current_camera]['name']
        fov = locator.camera_configs[locator.current_camera]['fov']
        
        print(f"{zoom}x    {camera_name:<15} "
              f"{perf['gsd_x']*100:.1f}×{perf['gsd_y']*100:.1f}  "
              f"{perf['ground_width']:.0f}×{perf['ground_height']:.0f}    "
              f"{fov}°")

test_zoom_performance()