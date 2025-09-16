import os
import uuid
import json
import asyncio
import discord
import mimetypes
from pathlib import Path
from collections import deque
from discord.ext import commands

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, VideoMessage, AudioMessage, 
    FileMessage, StickerMessage, TextSendMessage
)

from flask import Flask, request, abort

from config import (
    LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, 
    LINE_GROUP_ID, TEMP_DIR
)

class LineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
        self.handler = WebhookHandler(LINE_CHANNEL_SECRET)
        self.line_group_id = LINE_GROUP_ID
        self.processed_message_ids = deque(maxlen=100)
        self.line_bot_id = None
        
        # 設定 Flask 應用
        self.app = Flask(__name__)
        self.setup_routes()
        self.setup_line_handlers()
    
    def setup_routes(self):
        """設置 Flask 路由"""
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
    
    def handle_line_text_message(self, event):
        """處理 Line 文字訊息"""
        user_id = event.source.user_id
        
        # 忽略機器人自己的訊息
        if self.line_bot_id and user_id == self.line_bot_id:
            self.logger.info("忽略Line機器人自己發送的訊息")
            return
        
        user_name = self.get_user_display_name(event)
        message = event.message.text
        self.bot.send_to_discord(f"**{user_name}**:\n{message}")
    
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
            file_path = TEMP_DIR / f"{uuid.uuid4()}.jpg"
            
            with open(file_path, 'wb') as fd:
                for chunk in message_content.iter_content():
                    fd.write(chunk)
            
            self.bot.send_to_discord_with_attachment(user_name, str(file_path), "圖片")
        except Exception as e:
            self.logger.error(f"處理圖片時發生錯誤: {e}")
            self.bot.send_to_discord(f"**{user_name}**:\n發送了一張圖片，但處理失敗: {str(e)}")
    
    # 其餘方法保持相同，只是將 self.send_to_discord 改為 self.bot.send_to_discord
    # ...

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

    async def fetch_line_bot_info(self):
        """獲取 Line Bot 資訊"""
        try:
            bot_profile = self.line_bot_api.get_bot_info()
            self.line_bot_id = bot_profile.user_id
            self.logger.info(f"Line機器人ID: {self.line_bot_id}")
        except Exception as e:
            self.logger.warning(f"獲取Line機器人資訊時發生錯誤: {e}")
            self.line_bot_id = None
            self.logger.info("將繼續運行，但無法過濾機器人自己的訊息")

def setup(bot):
    bot.add_cog(LineCog(bot))