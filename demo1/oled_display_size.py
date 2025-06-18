# --- oled_display.py (整合成功版本和新功能) ---

import network
import urequests
import time
from machine import Pin, I2C
import ssd1306

class OledChineseDisplay:
    """
    一個用於在 SSD1306 OLED 顯示器上顯示中文的類別。

    它透過一個外部的 Flask API 來取得中文字的點陣圖資料，
    並支援靜態顯示與跑馬燈捲動模式。
    """

    # 在這裡新增 default_font_size 參數
    def __init__(self, scl_pin, sda_pin, font_api_url, width=128, height=64, scroll_mode=True, default_font_size=24):
        """
        初始化顯示器類別。

        Args:
            scl_pin (int): I2C SCL 接腳編號。
            sda_pin (int): I2C SDA 接腳編號。
            font_api_url (str): 用於取得字型點陣圖的 Flask API 位址。
            width (int, optional): OLED 寬度。預設為 128。
            height (int, optional): OLED 高度。預設為 64。
            scroll_mode (bool, optional): 是否啟用跑馬燈模式。預設為 True。
            default_font_size (int, optional): 預設的字體大小。預設為 24。
        """
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        self.width = width
        self.height = height
        self.font_api_url = font_api_url
        self.scroll_mode = scroll_mode
        self.default_font_size = default_font_size # 新增預設字體大小屬性
        self.chinese_font_cache = {} # 新增一個快取字典 { (char, font_size): bitmap_data }
        
        self.i2c = None
        self.oled = None
        self.wlan = network.WLAN(network.STA_IF)

        # 自動初始化OLED
        if not self._init_oled():
            raise RuntimeError("OLED 初始化失敗！")

    def _init_oled(self):
        """ (內部方法) 初始化 I2C 和 OLED 顯示器。"""
        try:
            # 保持 I2C 頻率為 400000，因為這是您成功運行的頻率
            self.i2c = I2C(0, scl=Pin(self.scl_pin), sda=Pin(self.sda_pin), freq=400000) 
            self.oled = ssd1306.SSD1306_I2C(self.width, self.height, self.i2c)
            print("✅ OLED 初始化成功")
            self.show_message("System Booting...", "OLED Ready")
            time.sleep(1)
            return True
        except Exception as e:
            print(f"❌ OLED 初始化失敗: {e}")
            return False

    def connect_wifi(self, ssid, password, timeout=30):
        """
        連接到 Wi-Fi 網路。
        Args:
            ssid (str): Wi-Fi 的 SSID。
            password (str): Wi-Fi 的密碼。
            timeout (int, optional): 連線逾時秒數。預設為 30。
        Returns:
            bool: 連線成功返回 True，失敗返回 False。
        """
        self.wlan.active(True)
        if self.wlan.isconnected():
            print("✅ 已連接到 Wi-Fi")
            return True
        
        print(f"🔄 正在連接到 {ssid}...")
        self.show_message("Connecting WiFi", ssid)
        
        self.wlan.connect(ssid, password)
        
        start_time = time.time()
        while not self.wlan.isconnected():
            if time.time() - start_time > timeout:
                print("❌ Wi-Fi 連接逾時")
                self.show_message("WiFi Failed!", "Timeout")
                return False
            time.sleep(0.5)
        
        ip = self.wlan.ifconfig()[0]
        print(f"\n✅ Wi-Fi 連接成功! IP位址: {ip}")
        self.show_message("WiFi Connected!", ip, clear_after=2)
        return True

    @staticmethod
    def _urlencode_chinese(text):
        """ (靜態方法) 將文字中的所有 URL 不安全字符（包括中文字元和空白）轉換為 URL 編碼。"""
        safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"
        encoded_result = ""
        for char in text:
            if char in safe_chars:
                encoded_result += char
            else:
                utf8_bytes = char.encode('utf-8')
                for byte in utf8_bytes:
                    encoded_result += f"%{byte:02X}"
        return encoded_result

    # 新增 _fetch_single_char_bitmap 函數以支援快取和 font_size 傳遞
    def _fetch_single_char_bitmap(self, char, font_size):
        """ (內部方法) 專門用於從 Flask API 獲取單個字元的點陣圖（帶快取）。"""
        cache_key = (char, font_size)
        if cache_key in self.chinese_font_cache:
            return self.chinese_font_cache[cache_key]

        try:
            encoded_char = self._urlencode_chinese(char)
            # Flask API 現在會接收 font_size 參數
            url = f"{self.font_api_url}text={encoded_char}&font_size={font_size}"
            
            response = urequests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                response.close()
                if data.get('success', False):
                    self.chinese_font_cache[cache_key] = data
                    return data
            print(f"❌ HTTP 錯誤或 API 錯誤 ({char}): {response.status_code}")
            response.close()
            return None
        except Exception as e:
            print(f"❌ 請求單個字元 '{char}' 時發生錯誤: {e}")
            return None

    # 修改 _fetch_font_bitmap 以使用 _fetch_single_char_bitmap 和 font_size
    def _fetch_font_bitmap(self, text, font_size=None):
        """ (內部方法) 從 Flask API 取得整個字串的點陣圖，並利用字元快取和拼接。"""
        actual_font_size = font_size if font_size is not None else self.default_font_size
        
        full_bitmap_data = {
            'bitmap': [],
            'width': 0,
            'height': 0,
            'success': True
        }
        
        all_char_bitmaps = []
        max_height = 0
        total_width = 0

        # 計算總寬度並獲取每個字元的點陣圖數據
        for char in text:
            char_data = self._fetch_single_char_bitmap(char, actual_font_size)
            if char_data and char_data['success']:
                all_char_bitmaps.append(char_data)
                total_width += char_data['width']
                if char_data['height'] > max_height:
                    max_height = char_data['height']
            else:
                print(f"❌ 無法獲取字元 '{char}' 的點陣圖，可能導致顯示不完整或失敗。")
                full_bitmap_data['success'] = False
                return None # 任何字元獲取失敗就返回None

        if not all_char_bitmaps:
            print("警告: 沒有字元可以顯示或所有字元獲取失敗。")
            return None # 如果沒有任何字元

        # 初始化一個大的點陣圖緩衝區來拼接所有字元
        full_bitmap = [[0 for _ in range(total_width)] for _ in range(max_height)]

        current_x = 0
        for char_data in all_char_bitmaps:
            char_bitmap = char_data['bitmap']
            char_width = char_data['width']
            char_height = char_data['height']
            
            # 計算垂直偏移量，實現底部對齊
            y_offset_for_char = max_height - char_height 
            
            # 將每個字元的點陣圖繪製到大點陣圖上
            for y in range(char_height):
                for x in range(char_width):
                    if char_bitmap[y][x]:
                        full_bitmap[y_offset_for_char + y][current_x + x] = 1
            current_x += char_width
            
        full_bitmap_data['bitmap'] = full_bitmap
        full_bitmap_data['width'] = total_width
        full_bitmap_data['height'] = max_height

        return full_bitmap_data
            
    # 修改 _render_bitmap 以支援可變跑馬燈速度
    def _render_bitmap(self, bitmap_data, speed=0.08): 
        """ (內部方法) 根據 scroll_mode 決定如何繪製點陣圖。"""
        bitmap = bitmap_data['bitmap']
        width = bitmap_data['width']
        height = bitmap_data['height']
        y_offset = (self.height - height) // 2 # 將文字垂直居中

        if self.scroll_mode:
            # 跑馬燈模式
            total_scroll_width = self.width + width
            scroll_step = 2 # 每次移動 2 像素，可以調整
            
            for offset in range(0, total_scroll_width + scroll_step, scroll_step):
                self.oled.fill(0)
                for y in range(height):
                    for x in range(width):
                        if bitmap[y][x]:
                            px = self.width - offset + x
                            py = y_offset + y
                            if 0 <= px < self.width:
                                self.oled.pixel(px, py, 1)
                self.oled.show()
                time.sleep(speed) 
        else:
            # 靜態居中顯示
            self.oled.fill(0)
            x_offset = (self.width - width) // 2
            for y in range(height):
                for x in range(width):
                    if bitmap[y][x]:
                        self.oled.pixel(x_offset + x, y_offset + y, 1)
            self.oled.show()
                
    # 修改 display 以支援 font_size 和 scroll_speed 參數
    def display(self, texts, delay_between_texts=1, font_size=None, scroll_speed=0.08):
        """
        在 OLED 上顯示一系列文字。這是你主要會呼叫的方法。

        Args:
            texts (list or str): 一個包含多個字串的列表，或單一字串。
            delay_between_texts (int, optional): 每則訊息之間的延遲秒數。預設為 1。
            font_size (int, optional): 要使用的字體大小。如果未提供，則使用初始化時的 default_font_size。
            scroll_speed (float, optional): 跑馬燈捲動速度。預設為 0.08。
        """
        if isinstance(texts, str):
            texts = [texts]

        print("\n🎯 開始顯示文字...")
        for text in texts:
            print(f"--- 正在處理: {text} ---")
            # show_message 這裡也應傳入 font_size，但目前 show_message 只支援 1 或 2，所以暫不傳遞實際字體大小
            self.show_message("Fetching Font...", text, font_size=1) 
            
            font_data = self._fetch_font_bitmap(text, font_size) 
            
            if font_data:
                self._render_bitmap(font_data, speed=scroll_speed) 
                print(f"✅ '{text}' 顯示完成")
            else:
                print(f"❌ '{text}' 顯示失敗")
                self.show_message("Font Error!", "Check API server", clear_after=2)
            
            time.sleep(delay_between_texts)
        print("🎉 所有文字顯示完畢!")

    # 新增 display_small_text 函數
    def display_small_text(self, texts, delay_between_texts=1, half_size_multiplier=0.5, scroll_speed=0.08):
        """
        以比預設字體小一半的大小顯示中文文字。

        Args:
            texts (list or str): 一個包含多個字串的列表，或單一字串。
            delay_between_texts (int, optional): 每則訊息之間的延遲秒數。預設為 1。
            half_size_multiplier (float, optional): 縮小倍數。0.5 表示縮小一半。
            scroll_speed (float, optional): 跑馬燈捲動速度。預設為 0.08。
        """
        smaller_font_size = max(1, int(self.default_font_size * half_size_multiplier))
        print(f"INFO: 將使用字體大小: {smaller_font_size}")
        self.display(texts, delay_between_texts=delay_between_texts, font_size=smaller_font_size, scroll_speed=scroll_speed)

    def show_message(self, line1, line2="", font_size=1, clear_after=0):
        """
        在螢幕上顯示簡單的英文字串訊息。
        Args:
            line1 (str): 第一行文字。
            line2 (str): 第二行文字 (可選)。
            font_size (int): 字體大小 (1=8px高, 2=16px高)。 # 這裡的 font_size 是指 SSD1306 驅動本身的內建字體大小
            clear_after (int): 顯示後幾秒自動清除。0為不清除。
        """
        self.oled.fill(0)
        char_height = 8 * font_size
        self.oled.text(line1, 0, 0)
        if line2:
            self.oled.text(line2, 0, char_height + 2)
        self.oled.show()
        if clear_after > 0:
            time.sleep(clear_after)
            self.clear()

    def clear(self):
        """ 清除螢幕。"""
        self.oled.fill(0)
        self.oled.show()