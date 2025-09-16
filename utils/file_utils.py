import os
import time
import uuid
import logging
from config import TEMP_DIR

logger = logging.getLogger('line_discord_bridge')

def cleanup_temp_files():
    """清理超過1小時的暫存圖片檔案"""
    try:
        for file in TEMP_DIR.glob("*"):
            if (time.time() - file.stat().st_mtime) > 3600:
                file.unlink()
                logger.info(f"已刪除過期臨時文件: {file}")
    except Exception as e:
        logger.error(f"清理臨時文件時發生錯誤: {e}")

def generate_temp_file_path(extension):
    """生成臨時檔案路徑"""
    return TEMP_DIR / f"{uuid.uuid4()}{extension}"