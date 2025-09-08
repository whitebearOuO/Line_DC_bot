import logging
from datetime import datetime
import pytz  # 確保已安裝 pytz 模組

class TimezoneFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, tz=None):
        super().__init__(fmt, datefmt)
        self.tz = tz

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.isoformat()

# 設定時區，例如 Asia/Taipei
taipei_tz = pytz.timezone("Asia/Taipei")

# 自定義日誌格式
formatter = TimezoneFormatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    tz=taipei_tz
)

# 設定日誌處理器
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 測試日誌
logger.info("這是一條測試日誌")