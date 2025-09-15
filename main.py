# =====================
# 主程式依賴與初始化
# =====================
import os
import time
import uuid
import logging
import pytz
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, abort
from pathlib import Path
import mimetypes
from collections import deque
import threading
import asyncio
import json

# Line Bot SDK v2
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, VideoMessage, AudioMessage, 
    FileMessage, StickerMessage, TextSendMessage
)

# Discord Bot 相關
import discord
from discord.commands import Option
from discord.ext import commands

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
# TIMEZONE_NAME = 'America/New_York'  # 美國東岸（UTC-5/UTC-4）
# TIMEZONE_NAME = 'America/Los_Angeles'  # 美國西岸（UTC-8/UTC-7）


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


class LineDiscordBridge:
    """
    Line 與 Discord 訊息橋接器
    
    負責:
    1. 初始化 Line 和 Discord 連接
    2. 處理來自 Line 的訊息並轉發到 Discord
    3. 處理來自 Discord 的訊息並轉發到 Line
    4. 管理暫存檔案與緩存
    """
    
    def __init__(self):
        """初始化橋接器"""
        # 設定基本變數
        self.logger = None
        self.temp_dir = Path("temp_images")
        self.temp_dir.mkdir(exist_ok=True)
        
        # 初始化緩存和狀態
        self.processed_message_ids = deque(maxlen=100)
        self.unsent_messages = []
        self.discord_channel = None
        self.line_bot_id = None
        self.group_info_cache = {}
        
        # 設定日誌系統
        self.setup_logging()
        
        # 載入環境變數
        load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
        
        # 初始化 Line 和 Discord Bot
        self.init_line_bot()
        self.init_discord_bot()
        
        # 設定 Flask 應用
        self.setup_flask()
    
    def setup_logging(self):
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
        self.logger = logging.getLogger(__name__)
        
        # 設置所有處理器的格式
        for handler in logging.getLogger().handlers:
            handler.setFormatter(formatter)
        
        # 記錄目前使用的時區設定
        self.logger.info(f"日誌系統已設定使用時區: {TIMEZONE_NAME}")
    
    def init_line_bot(self):
        """初始化 Line Bot"""
        self.line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        self.line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')
        self.line_group_id = os.getenv('LINE_GROUP_ID', '')
        
        # 初始化 Line Bot API
        self.line_bot_api = LineBotApi(self.line_channel_access_token)
        self.handler = WebhookHandler(self.line_channel_secret)
        
        # 設定 Line 訊息處理
        self.setup_line_handlers()
    
    def init_discord_bot(self):
        """初始化 Discord Bot"""
        self.discord_token = os.getenv('DISCORD_TOKEN')
        self.discord_channel_id = int(os.getenv('DISCORD_CHANNEL_ID', 0))
        
        # 初始化 Discord Bot
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = discord.Bot(intents=intents)
        
        # 設定 Discord 事件處理
        self.setup_discord_handlers()
    
    def setup_flask(self):
        """設置 Flask 應用"""
        self.app = Flask(__name__)
        
        # 註冊路由
        @self.app.route("/callback", methods=['POST'])
        def callback():
            """處理來自 Line 平台的 Webhook 事件"""
            signature = request.headers['X-Line-Signature']
            body = request.get_data(as_text=True)
            self.logger.info("收到Line訊息: %s", body)
            
            # 檢查是否為重複訊息
            try:
                webhook_data = json.loads(body)
                if 'events' in webhook_data and webhook_data['events']:
                    for event in webhook_data['events']:
                        # 檢查訊息ID是否已處理過
                        if 'message' in event and 'id' in event['message']:
                            message_id = event['message']['id']
                            if message_id in self.processed_message_ids:
                                self.logger.info(f"跳過重複訊息 ID: {message_id}")
                                return 'OK'  # 已處理過，直接返回成功
                        
                        # 添加新訊息ID到已處理集合
                        self.processed_message_ids.append(message_id)
            except Exception as e:
                self.logger.error(f"解析訊息ID時發生錯誤: {e}")
            
            # 處理訊息
            try:
                self.handler.handle(body, signature)
            except InvalidSignatureError:
                self.logger.error("無效的簽名")
                abort(400)
            
            return 'OK'
        
        @self.app.route("/", methods=['GET', 'POST'])
        def index():
            """首頁路由，顯示服務狀態"""
            return 'Line-Discord Bot運行中！請將Webhook設置為/callback路徑。'
    
    def setup_line_handlers(self):
        """設置 Line 訊息處理器"""
        # 文字訊息處理
        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_text_message(event):
            self.handle_line_text_message(event)
        
        # 圖片訊息處理
        @self.handler.add(MessageEvent, message=ImageMessage)
        def handle_image_message(event):
            self.handle_line_image_message(event)
        
        # 貼圖訊息處理
        @self.handler.add(MessageEvent, message=StickerMessage)
        def handle_sticker_message(event):
            self.handle_line_sticker_message(event)
        
        # 媒體訊息處理
        @self.handler.add(MessageEvent, message=(VideoMessage, AudioMessage, FileMessage))
        def handle_media_message(event):
            self.handle_line_media_message(event)
    
    def setup_discord_handlers(self):
        """設置 Discord 事件處理器"""
        # 機器人就緒事件
        @self.bot.event
        async def on_ready():
            await self.on_discord_ready()
        
        # 斜線指令
        @self.bot.slash_command(name="say_line", description="發送訊息到Line群組")
        async def say_line(ctx, message: Option(str, "要發送到Line的訊息")):
            await self.handle_discord_say_line(ctx, message)
    
    async def on_discord_ready(self):
        """Discord Bot 啟動完成時執行"""
        self.logger.info(f'Discord Bot {self.bot.user} 已連接！')
        
        # 初始化頻道
        self.discord_channel = self.bot.get_channel(self.discord_channel_id)
        if self.discord_channel is None:
            self.logger.error(f"無法找到指定的Discord頻道 ID: {self.discord_channel_id}")
            return
        self.logger.info(f"已連接到Discord頻道: {self.discord_channel.name}")
        
        # 獲取 Line Bot ID
        try:
            bot_profile = self.line_bot_api.get_bot_info()
            self.line_bot_id = bot_profile.user_id
            self.logger.info(f"Line機器人ID: {self.line_bot_id}")
        except Exception as e:
            self.logger.warning(f"獲取Line機器人資訊時發生錯誤: {e}")
            self.line_bot_id = None
            self.logger.info("將繼續運行，但無法過濾機器人自己的訊息")
        
        # 重發未發送的訊息
        if self.unsent_messages:
            self.logger.info(f"重新發送 {len(self.unsent_messages)} 則暫存訊息")
            for msg in self.unsent_messages:
                try:
                    await self.discord_channel.send(msg)
                    self.logger.info(f"成功重新發送訊息: {msg}")
                except Exception as e:
                    self.logger.error(f"重新發送訊息時發生錯誤: {e}")
            self.unsent_messages.clear()
    
    async def handle_discord_say_line(self, ctx, message):
        """處理 Discord 斜線指令：發送訊息到 Line 群組"""
        try:
            if not self.line_group_id:
                await ctx.respond("錯誤：未設定LINE_GROUP_ID環境變數", ephemeral=True)
                return
            
            self.line_bot_api.push_message(
                self.line_group_id, 
                TextSendMessage(text=f"[Discord] {ctx.author.display_name}: {message}")
            )
            
            await ctx.respond(f"已成功發送訊息到Line: {message}", ephemeral=False)
            self.logger.info(f"Discord用戶 {ctx.author.display_name} 發送訊息到Line: {message}")
        except Exception as e:
            self.logger.error(f"發送訊息到Line時發生錯誤: {e}")
            await ctx.respond(f"發送訊息到Line時發生錯誤: {str(e)}", ephemeral=True)
    
    def handle_line_text_message(self, event):
        """處理 Line 文字訊息"""
        user_id = event.source.user_id
        
        # 忽略機器人自己的訊息
        if self.line_bot_id and user_id == self.line_bot_id:
            self.logger.info("忽略Line機器人自己發送的訊息")
            return
        
        user_name = self.get_user_display_name(event)
        message = event.message.text
        self.send_to_discord(f"**{user_name}**:\n{message}")
    
    def handle_line_image_message(self, event):
        """處理 Line 圖片訊息"""
        user_id = event.source.user_id
        
        # 忽略機器人自己的訊息
        if self.line_bot_id and user_id == self.line_bot_id:
            self.logger.info("忽略Line機器人自己發送的圖片")
            return
        
        user_name = self.get_user_display_name(event)
        message_id = event.message.id
        
        try:
            message_content = self.line_bot_api.get_message_content(message_id)
            file_path = self.temp_dir / f"{uuid.uuid4()}.jpg"
            
            with open(file_path, 'wb') as fd:
                for chunk in message_content.iter_content():
                    fd.write(chunk)
            
            self.send_to_discord_with_attachment(user_name, str(file_path), "圖片")
        except Exception as e:
            self.logger.error(f"處理圖片時發生錯誤: {e}")
            self.send_to_discord(f"**{user_name}**:\n發送了一張圖片，但處理失敗: {str(e)}")
    
    def handle_line_sticker_message(self, event):
        """處理 Line 貼圖訊息"""
        user_id = event.source.user_id
        
        # 忽略機器人自己的訊息
        if self.line_bot_id and user_id == self.line_bot_id:
            self.logger.info("忽略Line機器人自己發送的貼圖")
            return
        
        user_name = self.get_user_display_name(event)
        sticker_id = event.message.sticker_id
        package_id = event.message.package_id
        
        self.send_to_discord(f"**{user_name}**:\n發送了一個貼圖 (貼圖ID: {sticker_id}, 包ID: {package_id})")
    
    def handle_line_media_message(self, event):
        """處理 Line 媒體訊息（影片、語音、檔案）"""
        user_id = event.source.user_id
        
        # 忽略機器人自己的訊息
        if self.line_bot_id and user_id == self.line_bot_id:
            self.logger.info("忽略Line機器人自己發送的媒體")
            return
        
        user_name = self.get_user_display_name(event)
        
        # 判斷訊息類型
        if isinstance(event.message, VideoMessage):
            message_type = "影片"
        elif isinstance(event.message, AudioMessage):
            message_type = "語音"
        elif isinstance(event.message, FileMessage):
            message_type = "檔案"
        else:
            message_type = "媒體"
        
        # 在下載前先判斷是否為影片訊息，如果是且 isRedelivery=true 可能直接跳過
        if isinstance(event.message, VideoMessage) and hasattr(event, 'delivery_context') and \
           getattr(event.delivery_context, 'is_redelivery', False):
            # 僅發送一次通知，避免重複處理大檔案
            self.send_to_discord(f"**{user_name}**:\n發送了一個{message_type}（大檔案，可能重複）")
            return
        
        # 嘗試下載檔案並判斷大小
        message_id = event.message.id
        try:
            message_content = self.line_bot_api.get_message_content(message_id)
            
            # FileMessage 用原始檔名，其餘類型用 MIME type 推斷副檔名
            if isinstance(event.message, FileMessage) and hasattr(event.message, 'file_name'):
                orig_name = event.message.file_name
                file_path = self.temp_dir / f"{uuid.uuid4()}_{orig_name}"
            else:
                # 嘗試從 message_content.headers 取得 Content-Type
                mime_type = None
                if hasattr(message_content, 'headers') and 'Content-Type' in message_content.headers:
                    mime_type = message_content.headers['Content-Type']
                
                # 若無法取得，則 fallback 用 message_type
                if not mime_type:
                    mime_type = {
                        '影片': 'video/mp4',
                        '語音': 'audio/m4a',
                        '檔案': 'application/octet-stream',
                        '媒體': 'application/octet-stream'
                    }.get(message_type, 'application/octet-stream')
                
                ext = mimetypes.guess_extension(mime_type) or '.bin'
                file_path = self.temp_dir / f"{uuid.uuid4()}{ext}"
            
            with open(file_path, 'wb') as fd:
                for chunk in message_content.iter_content():
                    fd.write(chunk)
            
            file_size = file_path.stat().st_size
            max_size = 25 * 1024 * 1024  # 25MB
            
            if file_size <= max_size:
                self.send_to_discord_with_attachment(user_name, str(file_path), message_type)
            else:
                self.send_to_discord(f"**{user_name}**:\n發送了一個{message_type}（超過25MB，未轉傳）")
                os.remove(file_path)
        except Exception as e:
            self.logger.error(f"處理{message_type}時發生錯誤: {e}")
            self.send_to_discord(f"**{user_name}**:\n發送了一個{message_type}，但處理失敗: {str(e)}")
    
    def get_user_display_name(self, event):
        """獲取 Line 用戶的顯示名稱"""
        user_id = event.source.user_id
        source_type = getattr(event.source, 'type', None)
        
        if source_type == 'group':
            group_id = event.source.group_id
            try:
                member_profile = self.line_bot_api.get_group_member_profile(group_id, user_id)
                return member_profile.display_name
            except Exception:
                pass
            try:
                user_profile = self.line_bot_api.get_profile(user_id)
                return user_profile.display_name
            except Exception:
                pass
        elif source_type == 'user':
            try:
                user_profile = self.line_bot_api.get_profile(user_id)
                return user_profile.display_name
            except Exception:
                pass
        
        return f"Line用戶({user_id[-6:]})"
    
    def send_to_discord(self, message):
        """發送文字訊息到 Discord 頻道"""
        if self.discord_channel:
            try:
                asyncio.run_coroutine_threadsafe(self.discord_channel.send(message), self.bot.loop)
                self.logger.info(f"成功發送訊息到 Discord: {message}")
            except Exception as e:
                self.logger.error(f"發送訊息到 Discord 時發生錯誤: {e}")
                self.unsent_messages.append(message)
        else:
            self.logger.error("Discord 頻道未初始化")
            self.unsent_messages.append(message)
    
    def send_to_discord_with_attachment(self, user_name, file_path, message_type="圖片"):
        """發送附件到 Discord 頻道"""
        async def send_attachment():
            try:
                # 確保檔案路徑是字串格式
                path_str = str(file_path)
                await self.discord_channel.send(
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
                
        if self.discord_channel:
            # 在 Discord 事件循環中執行發送操作
            asyncio.run_coroutine_threadsafe(send_attachment(), self.bot.loop)
        else:
            self.logger.error("Discord 頻道未初始化")
            # 頻道未初始化時也要清理檔案
            try:
                os.remove(str(file_path))
            except:
                pass
            # 記錄一條訊息，表示有媒體未發送
            self.unsent_messages.append(f"**{user_name}**:\n發送了{message_type}，但Discord頻道未初始化")
    
    def cleanup_temp_files(self):
        """清理超過1小時的暫存圖片檔案"""
        try:
            for file in self.temp_dir.glob("*"):
                if (time.time() - file.stat().st_mtime) > 3600:
                    file.unlink()
                    self.logger.info(f"已刪除過期臨時文件: {file}")
        except Exception as e:
            self.logger.error(f"清理臨時文件時發生錯誤: {e}")
    
    def run_discord_bot(self):
        """啟動 Discord Bot"""
        self.bot.run(self.discord_token)
    
    def schedule_cleanup(self):
        """定期清理暫存檔案的排程任務"""
        while True:
            time.sleep(3600)  # 每小時執行一次
            self.cleanup_temp_files()
    
    def start(self):
        """啟動橋接器"""
        # 在單獨的線程中啟動Discord機器人
        discord_thread = threading.Thread(target=self.run_discord_bot)
        discord_thread.daemon = True
        discord_thread.start()
        
        # 啟動清理任務
        cleanup_thread = threading.Thread(target=self.schedule_cleanup)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        # 啟動Flask應用 (Line Webhook)
        port = int(os.environ.get("PORT", 8000))
        self.app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    # 初始化並啟動橋接器
    bridge = LineDiscordBridge()
    bridge.start()
