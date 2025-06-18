#中文顯示工具，目前最大只能承受11個中文字


# Example usage in your main.py on the MicroPython board
from oled_display import OledChineseDisplay
import time



WIFI_SSID = "moto-2G"
WIFI_PASSWORD = "04230524"
# Assuming your Flask server is at 192.168.1.100 (replace with your server's IP)
FONT_API_URL = "http://192.168.140.134:5000/api/font?text="



# Initialize the display
oled_display = OledChineseDisplay(
    scl_pin=22,  # Replace with your SCL pin
    sda_pin=21,  # Replace with your SDA pin
    font_api_url=FONT_API_URL,
    scroll_mode=True # or False, depending on your preference
)

# Connect to Wi-Fi
wifi_connected = oled_display.connect_wifi(WIFI_SSID, WIFI_PASSWORD)

if wifi_connected:
    oled_display.display(["你好      世界", "Hello World", "空白 測試"])
    time.sleep(3)
    oled_display.display(["   三個空白   "]) # Test with multiple leading/trailing spaces
else:
    print("無法連接 Wi-Fi，請檢查設定。")
