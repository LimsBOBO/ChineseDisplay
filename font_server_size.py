# --- font_server.py (應與上次提供的一致) ---
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

FONT_PATH = 'NotoSansTC-Regular.ttf'

def text_to_bitmap(text, font_size):
    try:
        if os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, font_size)
        else:
            font = ImageFont.load_default()
            print(f"警告: 找不到字型檔案 {FONT_PATH}, 使用預設字型 (大小: {font_size})")
        
        dummy_img = Image.new('1', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        if not text.strip(): 
            estimated_space_width = font_size // 3
            if width == 0 and len(text) > 0:
                width = estimated_space_width * len(text)
            elif width == 0 and len(text) == 0:
                width = 1 
            
            if height == 0:
                height = font_size 

        image = Image.new('1', (width, height), 0)
        draw = ImageDraw.Draw(image)
        draw.text((-bbox[0], -bbox[1]), text, font=font, fill=1)
        
        bitmap = []
        for y in range(height):
            row = []
            for x in range(width):
                pixel = image.getpixel((x, y))
                row.append(1 if pixel else 0)
            bitmap.append(row)
        
        return {
            'bitmap': bitmap,
            'width': width,
            'height': height,
            'success': True
        }
    
    except Exception as e:
        print(f"轉換錯誤: {e}")
        return {
            'error': str(e),
            'success': False
        }

@app.route('/api/font', methods=['GET'])
def get_font_bitmap():
    text = request.args.get('text', '')
    try:
        font_size = int(request.args.get('font_size', 24))
        if not (1 <= font_size <= 128):
            raise ValueError("Font size out of valid range.")
    except (ValueError, TypeError) as e:
        print(f"警告: font_size 參數無效 ({request.args.get('font_size')}), 使用預設值 24. 錯誤: {e}")
        font_size = 24

    if not text and request.args.get('text') is not None:
        print("接收到請求: 空白 text 參數")
        return jsonify({
            'error': 'text 參數不能為空字串，若要顯示空白請明確傳遞空白字元',
            'success': False
        }), 400
    elif request.args.get('text') is None:
        print("接收到請求: 缺少 text 參數")
        return jsonify({
            'error': '缺少 text 參數',
            'success': False
        }), 400
    
    print(f"接收到請求: '{text}' (原始字串), 字體大小: {font_size}")
    
    bitmap_data = text_to_bitmap(text, font_size)
    
    if bitmap_data['success']:
        print(f"成功轉換: '{text}' ({bitmap_data['width']}x{bitmap_data['height']})")
        return jsonify(bitmap_data)
    else:
        return jsonify(bitmap_data), 500

@app.route('/test', methods=['GET'])
def test():
    return jsonify({
        'message': '字型 API 伺服器運行中',
        'font_path': FONT_PATH,
        'font_exists': os.path.exists(FONT_PATH)
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Flask 字型 API 伺服器啟動中...")
    print(f"📁 字型檔案: {FONT_PATH}")
    print(f"✅ 字型存在: {os.path.exists(FONT_PATH)}")
    print("🌐 測試網址: http://localhost:5000/test")
    print("📝 API 使用: http://localhost:5000/api/font?text=你好")
    print("📝 測試空白字元: http://localhost:5000/api/font?text=%20%20%20 (三個空白)")
    print("📝 測試中文字元與空白: http://localhost:5000/api/font?text=你好%20世界")
    print("📝 測試不同字體大小: http://localhost:5000/api/font?text=你好&font_size=16")
    print("📝 測試不同字體大小: http://localhost:5000/api/font?text=測試文字&font_size=32")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)