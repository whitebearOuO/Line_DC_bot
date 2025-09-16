import os
import pytz
from pathlib import Path
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# =====================
# 時區設定（可自訂）
# =====================
# 你可以根據需求更改下方的時區設定：
# 例如：
#   台北：Asia/Taipei
#   英國（倫敦）：Europe/London
#   日本（東京）：Asia/Tokyo
#   美國（紐約）：America/New_York
#   美國（洛杉磯）：America/Los_Angeles
#
# 只需修改 TIMEZONE_NAME 即可切換日誌時區。
TIMEZONE_NAME = 'Asia/Taipei'  # 預設台北時區
# TIMEZONE_NAME = 'Europe/London'  # 英國（UTC+0）
# TIMEZONE_NAME = 'Asia/Tokyo'    # 日本（UTC+9）

# Line Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_GROUP_ID = os.getenv('LINE_GROUP_ID', '')

# Discord Bot 設定
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))

# 檔案設定
TEMP_DIR = Path("temp_images")
TEMP_DIR.mkdir(exist_ok=True)

# Flask 設定
PORT = int(os.environ.get("PORT", 8000))