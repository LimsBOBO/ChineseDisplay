# --- oled_display.py (最終確認版本) ---

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

    def __init__(self, scl_pin, sda_pin, font_api_url, width=128, height=64, scroll_mode=True):
        """
        初始化顯示器類別。

        Args:
            scl_pin (int): I2C SCL 接腳編號。
            sda_pin (int): I2C SDA 接腳編號。
            font_api_url (str): 用於取得字型點陣圖的 Flask API 位址。
            width (int, optional): OLED 寬度。預設為 128。
            height (int, optional): OLED 高度。預設為 64。
            scroll_mode (bool, optional): 是否啟用跑馬燈模式。預設為 True。
        """
        self.scl_pin = scl_pin
        self.sda_pin = sda_pin
        self.width = width
        self.height = height
        self.font_api_url = font_api_url
        self.scroll_mode = scroll_mode

        self.i2c = None
        self.oled = None
        self.wlan = network.WLAN(network.STA_IF)

        # 自動初始化OLED
        if not self._init_oled():
            raise RuntimeError("OLED 初始化失敗！")

    def _init_oled(self):
        """ (內部方法) 初始化 I2C 和 OLED 顯示器。"""
        try:
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

    def _fetch_font_bitmap(self, text):
        """ (內部方法) 從 Flask API 取得字型點陣圖。"""
        try:
            encoded_text = self._urlencode_chinese(text)
            url = self.font_api_url + encoded_text

            # 關鍵的偵錯輸出，再次確認
            print(f"DEBUG: 原始文字: '{text}'")
            print(f"DEBUG: 編碼後 URL: '{url}'") # 這裡必須顯示 %20

            response = urequests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                response.close()
                if data.get('success', False):
                    return data
            print(f"❌ HTTP 錯誤或 API 錯誤: {response.status_code}")
            response.close()
            return None
        except Exception as e:
            print(f"❌ 請求字型時發生錯誤: {e}")
            return None

    def _render_bitmap(self, bitmap_data, speed=0.08):
        """ (內部方法) 根據 scroll_mode 決定如何繪製點陣圖。"""
        bitmap = bitmap_data['bitmap']
        width = bitmap_data['width']
        height = bitmap_data['height']
        y_offset = (self.height - height) // 2

        if self.scroll_mode:
            # 跑馬燈模式
            total_scroll_width = self.width + width
            for offset in range(total_scroll_width):
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

    def display(self, texts, delay_between_texts=1):
        """
        在 OLED 上顯示一系列文字。這就是你主要會呼叫的方法。

        Args:
            texts (list or str): 一個包含多個字串的列表，或單一字串。
            delay_between_texts (int, optional): 每則訊息之間的延遲秒數。預設為 1。
        """
        if isinstance(texts, str):
            texts = [texts] # 如果傳入的是單一字串，也把它當成列表處理

        print("\n🎯 開始顯示文字...")
        for text in texts:
            print(f"--- 正在處理: {text} ---")
            self.show_message("Fetching Font...", text, font_size=1)
            font_data = self._fetch_font_bitmap(text)

            if font_data:
                self._render_bitmap(font_data)
                print(f"✅ '{text}' 顯示完成")
            else:
                print(f"❌ '{text}' 顯示失敗")
                self.show_message("Font Error!", "Check API server", clear_after=2)

            time.sleep(delay_between_texts)
        print("🎉 所有文字顯示完畢!")

    def show_message(self, line1, line2="", font_size=1, clear_after=0):
        """
        在螢幕上顯示簡單的英文字串訊息。

        Args:
            line1 (str): 第一行文字。
            line2 (str): 第二行文字 (可選)。
            font_size (int): 字體大小 (1=8px高, 2=16px高)。
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
