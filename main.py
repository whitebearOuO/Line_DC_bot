import os
import threading
import asyncio
import discord
from discord.ext import commands
from collections import deque
import time

# 匯入配置
from config import DISCORD_TOKEN, DISCORD_CHANNEL_ID, PORT
from utils.logging_utils import setup_logging
from utils.file_utils import cleanup_temp_files

class LineDiscordBot(commands.Bot):
    """整合 Line 與 Discord 的主要機器人類別"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, command_prefix="!")
        
        # 初始化日誌
        self.logger = setup_logging()
        
        # 初始化變數
        self.unsent_messages = []
        self.discord_channel = None
    
    async def load_extensions(self):
        """載入所有 Cog"""
        # 使用 load_extension 而不是 await self.load_extension
        self.load_extension("cogs.discord_cog")
        self.load_extension("cogs.line_cog")
        self.logger.info("已載入所有 Cog")
    
    def send_to_discord(self, message):
        """發送文字訊息到 Discord 頻道"""
        discord_cog = self.get_cog('DiscordCog')
        if discord_cog and discord_cog.discord_channel:
            try:
                asyncio.run_coroutine_threadsafe(discord_cog.discord_channel.send(message), self.loop)
                self.logger.info(f"成功發送訊息到 Discord: {message}")
            except Exception as e:
                self.logger.error(f"發送訊息到 Discord 時發生錯誤: {e}")
                self.unsent_messages.append(message)
        else:
            self.logger.error("Discord 頻道未初始化")
            self.unsent_messages.append(message)
    
    def send_to_discord_with_attachment(self, user_name, file_path, message_type="圖片"):
        """發送附件到 Discord 頻道"""
        discord_cog = self.get_cog('DiscordCog')
        
        async def send_attachment():
            try:
                # 確保檔案路徑是字串格式
                path_str = str(file_path)
                await discord_cog.discord_channel.send(
                    f"**{user_name}**:\n發送了{message_type}", 
                    file=discord.File(path_str)
                )
                # 發送成功後刪除暫存檔
                os.remove(path_str)
                self.logger.info(f"已成功發送{message_type}到Discord並刪除臨時文件: {path_str}")
            except discord.errors.DiscordException as e:
                self.logger.error(f"Discord API 錯誤: {e}")
                try:
                    os.remove(str(file_path))
                except:
                    pass
            except Exception as e:
                self.logger.error(f"發送{message_type}到Discord時發生錯誤: {e}")
                try:
                    os.remove(str(file_path))
                except:
                    pass
                
        if discord_cog and discord_cog.discord_channel:
            # 在 Discord 事件循環中執行發送操作
            asyncio.run_coroutine_threadsafe(send_attachment(), self.loop)
        else:
            self.logger.error("Discord 頻道未初始化")
            # 頻道未初始化時也要清理檔案
            try:
                os.remove(str(file_path))
            except:
                pass
            # 記錄一條訊息，表示有媒體未發送
            self.unsent_messages.append(f"**{user_name}**:\n發送了{message_type}，但Discord頻道未初始化")

def schedule_cleanup():
    """定期清理暫存檔案的排程任務"""
    while True:
        time.sleep(3600)  # 每小時執行一次
        cleanup_temp_files()

async def main():
    # 初始化機器人
    bot = LineDiscordBot()
    
    # 載入擴展
    await bot.load_extensions()
    
    # 啟動清理任務
    cleanup_thread = threading.Thread(target=schedule_cleanup)
    cleanup_thread.daemon = True
    cleanup_thread.start()
    
    # 獲取 Line Cog 實例
    line_cog = bot.get_cog('LineCog')
    
    # 在另一個執行緒中啟動 Flask 應用
    def run_flask():
        line_cog.app.run(host="0.0.0.0", port=PORT)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # 啟動 Discord Bot
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    # 啟動主程式
    asyncio.run(main())