# main.py
from oled_display_size import OledChineseDisplay # 確保這裡導入的是 oled_display
import time

# 請確保這是您的 Flask 伺服器實際的 IP 位址
FONT_API_BASE_URL = "http://192.168.140.134:5000/api/font?" 

# 設定您的 Wi-Fi 資訊
WIFI_SSID = "moto-2G"
WIFI_PASSWORD = "04230524"

oled_display = None # 先初始化為 None，以便在 finally 塊中檢查

try:
    # 初始化顯示器
    oled_display = OledChineseDisplay(
        scl_pin=22,  # 替換為您的 SCL Pin，例如 22
        sda_pin=21,  # 替換為您的 SDA Pin，例如 21
        font_api_url=FONT_API_BASE_URL,
        scroll_mode=False,
        default_font_size=24 # 設定一個預設的「標準」字體大小
    )

    # 連接 Wi-Fi
    wifi_connected = oled_display.connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    if wifi_connected:
        print("\n--- 開始顯示不同大小的文字範例 ---")
        
        # 顯示預設大小的文字 (font_size=24)
        oled_display.display(["這是預設大小的字！"], delay_between_texts=2) 
        

    else:
        print("無法連接 Wi-Fi，請檢查設定。")

finally:
    # 確保無論程式如何結束，都嘗試釋放資源
    if oled_display: # 只有當 oled_display 實例化成功後才調用 deinit
        print("\n--- 程式結束，正在釋放資源 ---")
        oled_display.clear()
    print("所有操作完成。")
    # 可以選擇在這裡讓ESP32休眠或無限循環，以免它自動重啟
    # while True:
    #     time.sleep(1)