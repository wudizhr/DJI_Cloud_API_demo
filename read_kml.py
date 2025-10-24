import xml.etree.ElementTree as ET
import re

def parse_kml_to_uav_files(kml_file_path):
    # 解析KML文件
    tree = ET.parse(kml_file_path)
    root = tree.getroot()
    
    # 命名空间
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # 初始化三个无人机的数据字典
    uav_data = {
        '1号机': [],
        '2号机': [],
        '3号机': []
    }
    
    # 查找所有Placemark元素
    for placemark in root.findall('.//kml:Placemark', ns):
        name_elem = placemark.find('kml:name', ns)
        if name_elem is not None:
            name = name_elem.text
            
            # 检查是否是无人机航点
            if '号机' in name:
                # 提取无人机编号和点编号
                match = re.match(r'(\d+)号机(\d+)号点', name)
                if match:
                    uav_num = match.group(1)
                    point_num = int(match.group(2))
                    
                    # 查找坐标
                    coordinates_elem = placemark.find('.//kml:coordinates', ns)
                    if coordinates_elem is not None:
                        coords = coordinates_elem.text.strip()
                        # 解析坐标：经度,纬度,高度
                        lon, lat, alt = coords.split(',')
                        
                        # 添加到对应的无人机数据中
                        uav_key = f'{uav_num}号机'
                        uav_data[uav_key].append((point_num, float(lat), float(lon)))
    
    # 对每个无人机的航点按编号排序
    for uav_key in uav_data:
        uav_data[uav_key].sort(key=lambda x: x[0])
    
    # 写入文件
    for uav_num in ['1', '2', '3']:
        uav_key = f'{uav_num}号机'
        filename = f'uav{uav_num}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            for point_num, lat, lon in uav_data[uav_key]:
                # 格式化为与示例相同的格式
                f.write(f"{point_num}.\t{lat:.7f}\t{lon:.7f}\n")
        
        print(f"已生成文件: {filename}，包含 {len(uav_data[uav_key])} 个航点")

# 使用示例
if __name__ == "__main__":
    kml_file = "fly_to_points.kml"  # 替换为你的KML文件路径
    parse_kml_to_uav_files(kml_file)