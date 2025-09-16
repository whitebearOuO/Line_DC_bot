import logging
import pytz
from datetime import datetime
from config import TIMEZONE_NAME

class TimezoneFormatter(logging.Formatter):
    """
    自訂日誌格式器，以指定時區顯示時間戳
    
    時間格式化範例: 2025-09-15 23:22:45 +08:00(asia/taipei)
    使用 pytz 時區庫，讓日誌記錄使用可識別的當地時間
    """
    def __init__(self, fmt=None, datefmt=None, timezone=None):
        super().__init__(fmt, datefmt)
        self.timezone = timezone or pytz.utc

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, self.timezone)
        tz_offset = dt.strftime('%z')
        tz_offset_fmt = f"{tz_offset[:3]}:{tz_offset[3:]}" if tz_offset else ''
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        return f"{time_str} {tz_offset_fmt}({self.timezone.zone.lower()})"

def setup_logging():
    """設置日誌系統"""
    # 使用全域設定的時區
    custom_timezone = pytz.timezone(TIMEZONE_NAME)
    
    # 創建格式器
    formatter = TimezoneFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        timezone=custom_timezone
    )
    
    # 配置日誌
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('line_discord_bridge')
    
    # 設置所有處理器的格式
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)
    
    # 記錄目前使用的時區設定
    logger.info(f"日誌系統已設定使用時區: {TIMEZONE_NAME}")
    
    return logger