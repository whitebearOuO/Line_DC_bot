import os
import re
import sys
import tempfile
import time
from dotenv import load_dotenv
from flask import Flask, request, abort

# Line Bot SDK v2
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, VideoMessage, AudioMessage, FileMessage, StickerMessage, TextSendMessage

import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import threading
import logging
import uuid
from pathlib import Path
import json

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 載入環境變數
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Discord 設定
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', 0))

# Line 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# 初始化 Line API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 初始化 Flask
app = Flask(__name__)

# 初始化 Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 存儲Discord頻道的引用
discord_channel = None

# 存儲Line機器人自己的ID
line_bot_id = None

# 存儲群組資訊的字典
group_info_cache = {}

# 創建臨時目錄用於存儲圖片
TEMP_DIR = Path("temp_images")
TEMP_DIR.mkdir(exist_ok=True)

# 暫存未發送的訊息
unsent_messages = []

# 當Discord機器人準備好時的事件
@bot.event
async def on_ready():
    global discord_channel, line_bot_id, unsent_messages
    logger.info(f'Discord Bot {bot.user} 已連接！')
    
    # 獲取指定的Discord頻道
    discord_channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if discord_channel is None:
        logger.error(f"無法找到指定的Discord頻道 ID: {DISCORD_CHANNEL_ID}")
        return
    
    logger.info(f"已連接到Discord頻道: {discord_channel.name}")
    
    # 註冊斜線指令
    try:
        # 同步指令到Discord伺服器
        await bot.tree.sync()
        logger.info("已同步斜線指令")
    except Exception as e:
        logger.error(f"同步斜線指令時發生錯誤: {e}")
    
    # 獲取Line機器人的個人資料
    try:
        bot_profile = line_bot_api.get_bot_info()
        line_bot_id = bot_profile.user_id
        logger.info(f"Line機器人ID: {line_bot_id}")
    except Exception as e:
        logger.warning(f"獲取Line機器人資訊時發生錯誤: {e}")
        line_bot_id = None
        logger.info("將繼續運行，但無法過濾機器人自己的訊息")
    
    # 重新發送暫存的訊息
    if unsent_messages:
        logger.info(f"重新發送 {len(unsent_messages)} 則暫存訊息")
        for msg in unsent_messages:
            try:
                await discord_channel.send(msg)
                logger.info(f"成功重新發送訊息: {msg}")
            except Exception as e:
                logger.error(f"重新發送訊息時發生錯誤: {e}")
        # 清空暫存訊息
        unsent_messages.clear()

# 獲取用戶顯示名稱的函數
def get_user_display_name(event):
    """
    嘗試獲取用戶的顯示名稱，失敗時返回默認名稱
    """
    user_id = event.source.user_id
    
    # 檢查事件來源類型
    if hasattr(event.source, 'type'):
        source_type = event.source.type
        if source_type == 'group':
            group_id = event.source.group_id
            
            # 嘗試從群組資訊獲取用戶名稱
            try:
                # 先嘗試獲取群組成員資料
                member_profile = line_bot_api.get_group_member_profile(group_id, user_id)
                user_name = member_profile.display_name
                logger.info(f"從群組獲取用戶名稱: {user_name}")
                return user_name
            except Exception as e:
                logger.warning(f"無法從群組獲取用戶資料: {e}")
                
            # 如果群組方法失敗，嘗試直接獲取用戶資料
            try:
                user_profile = line_bot_api.get_profile(user_id)
                user_name = user_profile.display_name
                logger.info(f"從個人資料獲取用戶名稱: {user_name}")
                return user_name
            except Exception as e:
                logger.warning(f"無法獲取用戶個人資料: {e}")
                
        elif source_type == 'user':
            # 一對一聊天
            try:
                user_profile = line_bot_api.get_profile(user_id)
                return user_profile.display_name
            except Exception as e:
                logger.warning(f"無法獲取一對一聊天用戶資料: {e}")
    
    # 如果所有方法都失敗，返回用戶ID的後6位作為顯示名稱
    return f"Line用戶({user_id[-6:]})"

# 定義一個斜線指令來發送訊息到Line
@bot.tree.command(name="say_line", description="發送訊息到Line群組")
@app_commands.describe(message="要發送到Line的訊息")
async def say_line(interaction: discord.Interaction, message: str):
    try:
        # 向Line發送訊息
        line_group_id = os.getenv('LINE_GROUP_ID', '')
        if not line_group_id:
            await interaction.response.send_message("錯誤：未設定LINE_GROUP_ID環境變數", ephemeral=True)
            return
        
        # 發送訊息到Line群組
        line_bot_api.push_message(line_group_id, TextSendMessage(text=f"[Discord] {interaction.user.display_name}: {message}"))
        
        # 回應用戶
        await interaction.response.send_message(f"已成功發送訊息到Line: {message}", ephemeral=False)
        logger.info(f"Discord用戶 {interaction.user.display_name} 發送訊息到Line: {message}")
    except Exception as e:
        logger.error(f"發送訊息到Line時發生錯誤: {e}")
        await interaction.response.send_message(f"發送訊息到Line時發生錯誤: {str(e)}", ephemeral=True)

# Line Webhook路由
@app.route("/callback", methods=['POST'])
def callback():
    # 取得X-Line-Signature頭部值
    signature = request.headers['X-Line-Signature']

    # 取得請求內容
    body = request.get_data(as_text=True)
    logger.info("收到Line訊息: %s", body)

    try:
        # 驗證簽名
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("無效的簽名")
        abort(400)

    return 'OK'

# 首頁路由
@app.route("/", methods=['GET', 'POST'])
def index():
    return 'Line-Discord Bot運行中！請將Webhook設置為/callback路徑。'

# Line文字訊息處理
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    
    # 檢查是否為機器人自己發送的訊息
    if line_bot_id and user_id == line_bot_id:
        logger.info("忽略Line機器人自己發送的訊息")
        return
    
    # 獲取用戶顯示名稱
    user_name = get_user_display_name(event)
    message = event.message.text
    
    # 轉發訊息到Discord (使用換行格式)
    send_to_discord(f"**{user_name}**:\n{message}")

# Line圖片訊息處理
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    
    # 檢查是否為機器人自己發送的訊息
    if line_bot_id and user_id == line_bot_id:
        logger.info("忽略Line機器人自己發送的圖片")
        return
    
    # 獲取用戶顯示名稱
    user_name = get_user_display_name(event)
    message_id = event.message.id
    
    try:
        # 下載圖片
        message_content = line_bot_api.get_message_content(message_id)
        
        # 生成唯一檔名
        file_path = TEMP_DIR / f"{uuid.uuid4()}.jpg"
        
        # 保存圖片
        with open(file_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)
        
        # 轉發圖片到Discord
        send_image_to_discord(user_name, str(file_path))
        
    except Exception as e:
        logger.error(f"處理圖片時發生錯誤: {e}")
        # 發送錯誤訊息到Discord
        send_to_discord(f"**{user_name}**:\n發送了一張圖片，但處理失敗: {str(e)}")

# Line貼圖訊息處理
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    user_id = event.source.user_id
    
    # 檢查是否為機器人自己發送的訊息
    if line_bot_id and user_id == line_bot_id:
        logger.info("忽略Line機器人自己發送的貼圖")
        return
    
    # 獲取用戶顯示名稱
    user_name = get_user_display_name(event)
    
    # 通知Discord有貼圖訊息
    sticker_id = event.message.sticker_id
    package_id = event.message.package_id
    send_to_discord(f"**{user_name}**:\n發送了一個貼圖 (貼圖ID: {sticker_id}, 包ID: {package_id})")

# 其他Line訊息類型處理（視頻、音訊、檔案等）
@handler.add(MessageEvent, message=(VideoMessage, AudioMessage, FileMessage))
def handle_media_message(event):
    user_id = event.source.user_id
    
    # 檢查是否為機器人自己發送的訊息
    if line_bot_id and user_id == line_bot_id:
        logger.info("忽略Line機器人自己發送的媒體")
        return
    
    # 獲取用戶顯示名稱
    user_name = get_user_display_name(event)
    
    # 判斷訊息類型
    if isinstance(event.message, VideoMessage):
        message_type = "影片"
    elif isinstance(event.message, AudioMessage):
        message_type = "語音"
    elif isinstance(event.message, FileMessage):
        message_type = "檔案"
    else:
        message_type = "媒體"
    
    # 通知Discord有媒體訊息
    send_to_discord(f"**{user_name}**:\n發送了一個{message_type}")

# 傳送訊息到Discord的函數
def send_to_discord(message):
    global unsent_messages
    if discord_channel:
        try:
            # 使用 asyncio 的 run_coroutine_threadsafe 發送訊息
            asyncio.run_coroutine_threadsafe(discord_channel.send(message), bot.loop)
            logger.info(f"成功發送訊息到 Discord: {message}")
        except Exception as e:
            logger.error(f"發送訊息到 Discord 時發生錯誤: {e}")
            # 將未發送的訊息暫存
            unsent_messages.append(message)
            logger.info(f"訊息已暫存，等待重新發送: {message}")
    else:
        logger.error("Discord 頻道未初始化")
        # 將未發送的訊息暫存
        unsent_messages.append(message)

# 傳送圖片到Discord的函數
def send_image_to_discord(user_name, file_path):
    if discord_channel:
        # 創建一個異步任務來發送圖片
        async def send_image():
            try:
                # 發送圖片和用戶名稱 (使用換行格式)
                await discord_channel.send(f"**{user_name}**:\n發送了圖片", file=discord.File(file_path))
                # 發送後刪除臨時文件
                os.remove(file_path)
                logger.info(f"已成功發送圖片到Discord並刪除臨時文件: {file_path}")
            except Exception as e:
                logger.error(f"發送圖片到Discord時發生錯誤: {e}")
        
        # 在Discord機器人的事件循環中運行任務
        asyncio.run_coroutine_threadsafe(send_image(), bot.loop)
    else:
        logger.error("Discord頻道未初始化")
        # 刪除臨時文件
        try:
            os.remove(file_path)
        except:
            pass

# 啟動Discord機器人的函數
def run_discord_bot():
    bot.run(DISCORD_TOKEN)

# 定期清理臨時文件夾的任務
def cleanup_temp_files():
    try:
        for file in TEMP_DIR.glob("*"):
            # 如果文件超過1小時，則刪除
            if (time.time() - file.stat().st_mtime) > 3600:
                file.unlink()
                logger.info(f"已刪除過期臨時文件: {file}")
    except Exception as e:
        logger.error(f"清理臨時文件時發生錯誤: {e}")

if __name__ == "__main__":
    # 在單獨的線程中啟動Discord機器人
    discord_thread = threading.Thread(target=run_discord_bot)
    discord_thread.daemon = True
    discord_thread.start()
    
    # 啟動Flask應用
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
