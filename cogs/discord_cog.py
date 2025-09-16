import asyncio
import discord
from discord.commands import Option
from discord.ext import commands
from config import DISCORD_CHANNEL_ID, LINE_GROUP_ID
from linebot.models import TextSendMessage

class DiscordCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.discord_channel = None
        self.discord_channel_id = DISCORD_CHANNEL_ID
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Discord Bot 啟動完成時執行"""
        self.logger.info(f'Discord Bot {self.bot.user} 已連接！')
        
        # 初始化頻道
        self.discord_channel = self.bot.get_channel(self.discord_channel_id)
        if self.discord_channel is None:
            self.logger.error(f"無法找到指定的Discord頻道 ID: {self.discord_channel_id}")
            return
        self.logger.info(f"已連接到Discord頻道: {self.discord_channel.name}")
        
        # 獲取 Line Bot ID
        line_cog = self.bot.get_cog('LineCog')
        if line_cog:
            await line_cog.fetch_line_bot_info()
        
        # 重發未發送的訊息
        if self.bot.unsent_messages:
            self.logger.info(f"重新發送 {len(self.bot.unsent_messages)} 則暫存訊息")
            for msg in self.bot.unsent_messages:
                try:
                    await self.discord_channel.send(msg)
                    self.logger.info(f"成功重新發送訊息: {msg}")
                except Exception as e:
                    self.logger.error(f"重新發送訊息時發生錯誤: {e}")
            self.bot.unsent_messages.clear()
    
    @commands.slash_command(name="say_line", description="發送訊息到Line群組")
    async def say_line(self, ctx, message: Option(str, "要發送到Line的訊息")):
        """處理 Discord 斜線指令：發送訊息到 Line 群組"""
        try:
            line_cog = self.bot.get_cog('LineCog')
            if not line_cog:
                await ctx.respond("錯誤：Line 功能尚未初始化", ephemeral=True)
                return
                
            if not LINE_GROUP_ID:
                await ctx.respond("錯誤：未設定LINE_GROUP_ID環境變數", ephemeral=True)
                return
            
            line_cog.line_bot_api.push_message(
                LINE_GROUP_ID, 
                TextSendMessage(text=f"[Discord] {ctx.author.display_name}: {message}")
            )
            
            await ctx.respond(f"已成功發送訊息到Line: {message}", ephemeral=False)
            self.logger.info(f"Discord用戶 {ctx.author.display_name} 發送訊息到Line: {message}")
        except Exception as e:
            self.logger.error(f"發送訊息到Line時發生錯誤: {e}")
            await ctx.respond(f"發送訊息到Line時發生錯誤: {str(e)}", ephemeral=True)

def setup(bot):
    bot.add_cog(DiscordCog(bot))