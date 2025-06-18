from flask import Flask, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__)

# 字型檔案路徑（請將 NotoSansTC-Regular.ttf 放在同一目錄）
FONT_PATH = 'NotoSansTC-Regular.ttf'
FONT_SIZE = 24

def text_to_bitmap(text, font_size=FONT_SIZE):
    """
    將文字轉換為點陣圖
    """
    try:
        # 載入字型
        if os.path.exists(FONT_PATH):
            font = ImageFont.truetype(FONT_PATH, font_size)
        else:
            # 如果沒有指定字型，使用系統預設字型
            font = ImageFont.load_default()
            print(f"警告: 找不到字型檔案 {FONT_PATH}, 使用預設字型")
        
        # --- Modifying the logic for getting text dimensions and drawing ---
        # Create a dummy image to calculate text size accurately
        # Pillow's getbbox() can sometimes return (0,0,0,0) for empty strings
        # or spaces depending on the font.
        dummy_img = Image.new('1', (1, 1)) # Small dummy image
        dummy_draw = ImageDraw.Draw(dummy_img)

        # Get text size more robustly
        # textbbox returns (left, top, right, bottom)
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        
        # Calculate width and height. Add a small buffer for safety if needed,
        # but generally bbox should be accurate.
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]

        # Ensure minimum dimensions for a blank space or empty string
        # If the text is just spaces, its width might be 0. We need to account for this.
        # Let's assume a space has an approximate width (e.g., 1/2 of FONT_SIZE or specific pixel value)
        # and minimum height of font_size.
        if not text.strip(): # Check if text is only spaces or empty
            # You might need to fine-tune this minimum_space_width
            # based on your font and how much space you want to represent.
            # Here, we're making an educated guess: 1/3 of font size per character.
            estimated_space_width = font_size // 3 
            if width == 0 and len(text) > 0: # If it's pure spaces and current width is 0
                width = estimated_space_width * len(text)
            elif width == 0 and len(text) == 0: # Empty string
                width = 1 # Minimum width
            
            if height == 0: # Ensure minimum height for any text
                height = font_size
        # --- End of modification ---

        # 建立圖像
        image = Image.new('1', (width, height), 0)  # 1-bit 黑白圖像
        draw = ImageDraw.Draw(image)
        
        # 繪製文字
        # Use bbox[0] and bbox[1] to adjust drawing position,
        # as getbbox can return negative offsets for characters that extend left/up
        draw.text((-bbox[0], -bbox[1]), text, font=font, fill=1)
        
        # 轉換為點陣圖陣列
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
    """
    API 端點：取得文字的點陣圖
    參數: text - 要轉換的文字
    """
    text = request.args.get('text', '')
    
    if not text and request.args.get('text') is not None: # Check if 'text' param exists but is empty
        # This handles cases like /api/font?text=
        print("接收到請求: 空白 text 參數")
        return jsonify({
            'error': 'text 參數不能為空字串，若要顯示空白請明確傳遞空白字元',
            'success': False
        }), 400
    elif request.args.get('text') is None: # This handles cases like /api/font
        print("接收到請求: 缺少 text 參數")
        return jsonify({
            'error': '缺少 text 參數',
            'success': False
        }), 400
    
    print(f"接收到請求: '{text}' (原始字串)")
    
    bitmap_data = text_to_bitmap(text)
    
    if bitmap_data['success']:
        print(f"成功轉換: '{text}' ({bitmap_data['width']}x{bitmap_data['height']})")
        return jsonify(bitmap_data)
    else:
        return jsonify(bitmap_data), 500

@app.route('/test', methods=['GET'])
def test():
    """
    測試端點
    """
    return jsonify({
        'message': '字型 API 伺服器運行中',
        'font_path': FONT_PATH,
        'font_exists': os.exists(FONT_PATH)
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
    print("=" * 50)
    
    # 允許區網內其他裝置連線
    app.run(host='0.0.0.0', port=5000, debug=True)