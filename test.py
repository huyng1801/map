import xml.etree.ElementTree as ET
import folium
import re
import os
import time
import base64

# === Cấu hình tên file GPX và HTML ===
gpx_file = "duong_di.gpx"   # đổi tên file gpx của bạn tại đây
output_html = "ban_do_day_du.html"

# === Load file GPX và namespace ===
tree = ET.parse(gpx_file)
root = tree.getroot()

ns = {
    'gpx': 'http://www.topografix.com/GPX/1/1',
    'geotracker': 'http://ilyabogdanovich.com/gpx/extensions/geotracker'
}

# === 1. Lọc các điểm dừng >= 10 phút ===
waypoints = []
for wpt in root.findall('gpx:wpt', ns):
    name = wpt.find('gpx:name', ns)
    if name is not None and "Stop for ~" in name.text:
        match = re.search(r'Stop for ~(\d+)', name.text)
        if match:
            minutes = int(match.group(1))
            if minutes >= 20:
                lat = float(wpt.attrib['lat'])
                lon = float(wpt.attrib['lon'])
                ele = wpt.findtext('gpx:ele', default='0', namespaces=ns)
                time = wpt.findtext('gpx:time', default='', namespaces=ns)
                desc = wpt.findtext('gpx:desc', default='', namespaces=ns)
                waypoints.append({
                    'lat': lat,
                    'lon': lon,
                    'name': name.text,
                    'time': time,
                    'ele': float(ele),
                    'desc': desc
                })

# === 2. Lấy các điểm di chuyển từ <trkpt> để vẽ đường ===
track_points = []
for trk in root.findall('gpx:trk', ns):
    for trkseg in trk.findall('gpx:trkseg', ns):
        for trkpt in trkseg.findall('gpx:trkpt', ns):
            lat = float(trkpt.attrib['lat'])
            lon = float(trkpt.attrib['lon'])
            track_points.append((lat, lon))

# === 3. Tạo bản đồ Folium ===
if waypoints:
    center = [waypoints[0]['lat'], waypoints[0]['lon']]
elif track_points:
    center = track_points[len(track_points) // 2]
else:
    center = [0, 0]

m = folium.Map(
    location=center, 
    zoom_start=6.5,
    tiles='OpenStreetMap',
    zoom_control=True,
    scrollWheelZoom=True,
    dragging=True,
    tap=True,
    tap_tolerance=15,
    world_copy_jump=False,
    close_popup_on_click=True,
    bounce_at_zoom_limits=True,
    keyboard=True,
    keyboard_pan_offset=80,
    keyboard_zoom_offset=1,
    zoom_delta=0.5,
    zoom_snap=0.5,
    prefer_canvas=True,  # Tối ưu rendering
    crs='EPSG3857'  # Đảm bảo projection đúng
)

# === 4. Vẽ đường di chuyển (polyline) ===
if track_points:
    folium.PolyLine(
        track_points, 
        color="blue", 
        weight=4,  # Tăng độ dày để rõ hơn
        opacity=0.9,
        smoothFactor=1.0,  # Tối ưu smooth
        noClip=False  # Đảm bảo không bị clip
    ).add_to(m)

# === 5. Thêm marker các điểm dừng >= 10p ===
for wp in waypoints:
    # Xử lý thời gian
    time_str = wp['time'].replace('T', ' ').replace('Z', '') if wp['time'] else 'Không rõ'
    
    # Xử lý chi tiết
    desc_lines = wp['desc'].split('\n') if wp['desc'] else []
    formatted_desc = ""
    for line in desc_lines:
        if 'Elevation:' in line:
            formatted_desc += f"🏔️ Độ cao: {line.split(':')[1].strip()}<br>"
        elif 'Time from start:' in line:
            formatted_desc += f"⏱️ Thời gian từ lúc bắt đầu: {line.split(':')[1].strip()}<br>"
        elif 'Distance from start:' in line:
            formatted_desc += f"📍 Khoảng cách từ điểm xuất phát: {line.split(':')[1].strip()}<br>"
    
    popup_html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.4;">
        <h4 style="margin: 0 0 10px 0; color: #d63031;">🛑 {wp['name'].replace('Stop for ~', 'Dừng khoảng ').replace(' min', ' phút')}</h4>
        <div style="margin: 5px 0;">
            <strong>🕐 Thời gian:</strong> {time_str}
        </div>
        <div style="margin: 5px 0;">
            <strong>📏 Độ cao:</strong> {wp['ele']:.1f} m
        </div>
        <div style="margin: 10px 0; padding: 8px; background-color: #f8f9fa; border-radius: 4px; font-size: 12px;">
            {formatted_desc}
        </div>
    </div>
    """
    folium.Marker(
        location=(wp['lat'], wp['lon']),
        popup=folium.Popup(popup_html, max_width=300),
        icon=folium.Icon(
            color='red',
            icon='stop-circle',
            prefix='fa',
            icon_color='white'
        )
    ).add_to(m)

# === 6. Lưu ra file HTML ===
m.save(output_html)
print(f"✅ Đã tạo bản đồ HTML có cả tuyến đường: {output_html}")

# === 7. Thêm chức năng xuất ảnh JPG ===
def add_export_image_feature():
    """Thêm chức năng xuất ảnh vào HTML"""
    
    # Đọc file HTML đã tạo
    with open(output_html, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # JavaScript và CSS cho xuất ảnh
    export_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<script>
window.onload = function() {
    setTimeout(function() {
        // Đợi map hoàn toàn sẵn sàng
        if (typeof window[Object.keys(window).find(key => key.startsWith('map_'))] !== 'undefined') {
            console.log('🗺️ Map đã tải xong, sẵn sàng xuất ảnh');
        }
        
        // Tạo container cho nút xuất
        var buttonContainer = document.createElement('div');
        buttonContainer.style.position = 'fixed';
        buttonContainer.style.top = '10px';
        buttonContainer.style.right = '10px';
        buttonContainer.style.zIndex = '9999';
        buttonContainer.style.display = 'flex';
        buttonContainer.style.flexDirection = 'column';
        buttonContainer.style.gap = '5px';
        
        // Nút xuất JPG chất lượng cao
        var exportJpgBtn = document.createElement('button');
        exportJpgBtn.innerHTML = '📸 Xuất JPG Siêu Nét';
        exportJpgBtn.style.padding = '12px 16px';
        exportJpgBtn.style.fontSize = '14px';
        exportJpgBtn.style.backgroundColor = '#28a745';
        exportJpgBtn.style.color = 'white';
        exportJpgBtn.style.border = 'none';
        exportJpgBtn.style.borderRadius = '5px';
        exportJpgBtn.style.cursor = 'pointer';
        exportJpgBtn.style.boxShadow = '0 3px 6px rgba(0,0,0,0.2)';
        exportJpgBtn.style.fontWeight = 'bold';
        
        // Hàm xuất ảnh JPG
        function exportImage() {
            var originalText = exportJpgBtn.innerHTML;
            
            exportJpgBtn.innerHTML = '⏳ Đang xuất...';
            exportJpgBtn.disabled = true;
            
            // Cấu hình chất lượng phù hợp
            var options = {
                scale: 1.0,  // Scale 1:1 không nhân lên
                useCORS: true,
                allowTaint: true,
                backgroundColor: '#ffffff',
                width: window.innerWidth,   // Dùng kích thước window
                height: window.innerHeight,
                logging: false,
                removeContainer: false,
                onclone: function(clonedDoc) {
                    // Ẩn nút export trong clone
                    var container = clonedDoc.querySelector('[data-export-container]');
                    if (container) container.style.display = 'none';
                    
                    // Đảm bảo map render đúng
                    var mapDiv = clonedDoc.querySelector('.leaflet-container');
                    if (mapDiv) {
                        mapDiv.style.transform = 'none';
                        mapDiv.style.position = 'relative';
                    }
                }
            };
            
            html2canvas(document.body, options).then(function(canvas) {
                // Tạo filename với timestamp
                var now = new Date();
                var timestamp = now.getFullYear() + 
                    String(now.getMonth() + 1).padStart(2, '0') + 
                    String(now.getDate()).padStart(2, '0') + '_' +
                    String(now.getHours()).padStart(2, '0') + 
                    String(now.getMinutes()).padStart(2, '0');
                
                var filename = 'ban_do_viet_nam_' + timestamp + '.jpg';
                
                // Tạo link download
                var link = document.createElement('a');
                link.download = filename;
                link.href = canvas.toDataURL('image/jpeg', 0.95);
                
                // Trigger download
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                // Reset button
                exportJpgBtn.innerHTML = '✅ Đã xuất xong!';
                setTimeout(function() {
                    exportJpgBtn.innerHTML = originalText;
                    exportJpgBtn.disabled = false;
                }, 2000);
                
                console.log('📁 Đã xuất: ' + filename);
                console.log('📐 Kích thước: ' + canvas.width + 'x' + canvas.height + ' pixels');
                
            }).catch(function(error) {
                console.error('Export error:', error);
                exportJpgBtn.innerHTML = '❌ Lỗi xuất';
                setTimeout(function() {
                    exportJpgBtn.innerHTML = originalText;
                    exportJpgBtn.disabled = false;
                }, 3000);
            });
        }
        
        // Sự kiện click
        exportJpgBtn.onclick = exportImage;
        
        // Thêm nút vào container
        buttonContainer.appendChild(exportJpgBtn);
        buttonContainer.setAttribute('data-export-container', 'true');
        
        document.body.appendChild(buttonContainer);
        
        console.log('🎯 Bản đồ sẵn sàng! Nhấn nút "Xuất JPG Siêu Nét" để tải ảnh.');
        
    }, 3000);  // Tăng thời gian chờ để map load hoàn toàn
};

// Thêm CSS tối ưu
var style = document.createElement('style');
style.textContent = `
    /* Tối ưu cho xuất ảnh */
    body {
        margin: 0;
        padding: 0;
        background: white;
    }
    
    /* Ẩn attribution khi xuất */
    .leaflet-control-attribution {
        font-size: 10px !important;
        background: rgba(255, 255, 255, 0.8) !important;
    }
    
    /* Hover effect cho nút */
    [data-export-container] button:hover {
        transform: translateY(-2px);
        transition: all 0.2s ease;
    }
    
    [data-export-container] button:active {
        transform: translateY(0);
    }
`;
document.head.appendChild(style);
</script>

<style>
/* CSS bổ sung cho giao diện đẹp */
.leaflet-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Tối ưu popup */
.leaflet-popup-content {
    margin: 8px 12px !important;
}

.leaflet-popup-content h4 {
    margin-top: 0 !important;
}
</style>
"""
    
    # Thêm script vào HTML
    html_content = html_content.replace('</body>', export_script + '</body>')
    
    # Ghi lại file HTML
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

# Thực thi thêm chức năng xuất ảnh
add_export_image_feature()

print("🎉 Đã thêm chức năng xuất ảnh!")
print("📝 Hướng dẫn sử dụng:")
print("   1. Mở file HTML bằng trình duyệt")
print("   2. Đợi bản đồ tải xong (3 giây)")
print("   3. Nhấn nút '📸 Xuất JPG Siêu Nét' ở góc phải")
print("   4. Ảnh JPG sẽ tự động tải về với timestamp")
print("   5. Độ phân giải: Theo kích thước cửa sổ trình duyệt")
print("💡 Lưu ý: Nếu đường vẽ vẫn lệch, hãy zoom/pan bản đồ trước khi xuất")
