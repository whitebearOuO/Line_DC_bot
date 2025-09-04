# Line-Discord 訊息轉發機器人

這個機器人可以在 Line 群組和 Discord 頻道之間雙向轉發訊息。當有人在 Line 群組發送訊息時，機器人會自動將訊息轉發到 Discord；同樣地，Discord 用戶也可以使用斜線指令將訊息發送到 Line 群組。

## 功能特色

- **雙向訊息轉發**：Line ↔ Discord 雙向溝通
- **多種訊息類型支援**：
  - 文字訊息完整轉發
  - 圖片自動下載並轉發（從 Line 到 Discord）
  - 貼圖、影片、語音、檔案等類型通知
- **使用者識別**：顯示發送者名稱
- **避免訊息循環**：智能識別機器人自己的訊息，防止訊息循環轉發
- **Discord 斜線指令**：使用 `/say_line` 將訊息發送到 Line 群組

## 安裝與設定

### 前置需求

- Python 3.6+
- Pipenv
- Discord 開發者帳號和機器人
- Line Messaging API 帳號
- 公開可訪問的 Webhook URL（可使用 ngrok）

### 安裝步驟

1. 複製專案：
   ```
   git clone https://github.com/您的用戶名/Line_DC_bot.git
   cd Line_DC_bot
   ```

2. 安裝依賴套件：
   ```
   pipenv install
   ```

3. 設定環境變數：
   ```
   cp .env.example .env
   ```
   
4. 編輯 `.env` 檔案，填入您的 API 密鑰和 ID：
   ```
   # Discord設定
   DISCORD_TOKEN=your_discord_bot_token
   DISCORD_CHANNEL_ID=your_discord_channel_id

   # Line設定
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
   LINE_CHANNEL_SECRET=your_line_channel_secret
   LINE_GROUP_ID=your_line_group_id

   # 伺服器設定
   PORT=8000
   ```

5. 啟動機器人：
   ```
   pipenv run python main.py
   ```

## Docker 部署

除了常規的 Python 安裝方式外，您也可以使用 Docker 來部署此機器人。

### 使用 Docker Compose 部署

1. 確保您已安裝 [Docker](https://www.docker.com/get-started) 和 [Docker Compose](https://docs.docker.com/compose/install/)

2. 複製專案並進入專案目錄：

## Discord 機器人設定

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 創建一個新的應用程式
3. 前往 "Bot" 分頁並創建一個機器人
4. 開啟 "Message Content Intent" 和 "Server Members Intent"
5. 複製機器人的 Token 並填入 `.env` 檔案
6. 使用 OAuth2 URL 生成器邀請機器人到您的伺服器
   - 所需權限：Send Messages, Read Messages/View Channels, Use Slash Commands
7. 右鍵點擊您想要連接的頻道 → Copy ID，填入 `.env` 檔案的 `DISCORD_CHANNEL_ID`

## Line 機器人設定

1. 前往 [Line Developers Console](https://developers.line.biz/console/)
2. 創建一個提供者和頻道（Messaging API 類型）
3. 在 "Messaging API" 分頁中獲取 Channel Secret 和 Channel Access Token
4. 填入 `.env` 檔案
5. 設定 Webhook URL 為 `https://your-server-url/callback`
   - 使用 ngrok：`ngrok http 8000`，然後使用生成的 URL + `/callback`
6. 將機器人加入您想要連接的 Line 群組
7. 在群組中發送測試訊息，從應用程式日誌中獲取 Group ID，填入 `.env` 檔案

## 使用指南

### 從 Line 發送訊息到 Discord

直接在已加入機器人的 Line 群組中發送訊息，機器人會自動將訊息轉發到 Discord 頻道。

### 從 Discord 發送訊息到 Line

在 Discord 中使用斜線指令：
```
/say_line 您的訊息內容
```

訊息將被發送到 Line 群組，並顯示為：`[Discord] 您的Discord名稱: 您的訊息內容`

## 本地開發與測試

由於 Line Messaging API 需要公開可訪問的 Webhook URL，本地開發時請使用 ngrok 等工具：

1. 啟動 ngrok：
   ```
   ngrok http 8000
   ```

2. 複製生成的 URL（例如 `https://a1b2c3d4.ngrok.io`）

3. 在 Line Developers Console 中將 Webhook URL 設定為 `https://a1b2c3d4.ngrok.io/callback`

4. 啟動機器人：
   ```
   pipenv run python main.py
   ```

## 注意事項

- 一個機器人實例目前只支援連接一個 Line 群組和一個 Discord 頻道
- 如要支援多個群組，需要修改程式碼或運行多個機器人實例
- Line 的圖片、貼圖等非文字內容在轉發到 Discord 時可能會有特定的顯示方式
- 請妥善保管您的 API 密鑰，不要將 `.env` 檔案上傳到公開的版本控制系統

## 環境設定

1. 複製 `.env.example` 檔案並重命名為 `.env`
2. 使用您自己的 API 金鑰和設定填寫 `.env` 檔案

注意：**永遠不要**將您的 `.env` 檔案提交到版本控制系統中，它包含敏感資訊！

## 故障排除

- **找不到 Discord 頻道**：確認 `DISCORD_CHANNEL_ID` 填寫正確，且機器人已加入該頻道
- **Line Webhook 驗證失敗**：確認 `LINE_CHANNEL_SECRET` 填寫正確
- **Discord 斜線指令無法使用**：重啟機器人，等待斜線指令同步完成
- **找不到 Line 群組 ID**：在群組中發送測試訊息，查看應用程式日誌獲取 Group ID

