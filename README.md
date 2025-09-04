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

## 快速開始 (使用 Docker)

### 前置需求

- [Docker](https://www.docker.com/get-started) 和 [Docker Compose](https://docs.docker.com/compose/install/)
- Discord 開發者帳號和機器人
- Line Messaging API 帳號
- 公開可訪問的 Webhook URL（可使用 ngrok）

### Docker 部署步驟

1. **複製專案**：
   ```bash
   git clone https://github.com/whitebearOuO/Line_DC_bot.git
   cd Line_DC_bot
   ```

2. **設定環境變數**：
   ```bash
   cp .env.example .env
   ```
   
3. **編輯 `.env` 檔案**，填入您的 API 金鑰和 ID：
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

4. **構建並啟動 Docker 容器**：
   ```bash
   docker-compose up -d
   ```

5. **查看日誌**：
   ```bash
   docker-compose logs -f
   ```

### 使用 Ngrok 設定公開 URL

Docker 容器啟動後，您需要設定一個公開的 URL 讓 Line 平台能夠發送 Webhook 事件：

1. **安裝並啟動 Ngrok**：
   ```bash
   # 安裝 Ngrok (如果尚未安裝)
   # 在 https://ngrok.com/ 註冊並獲取 authtoken

   # 啟動 Ngrok
   ngrok http 8000
   ```

2. **複製生成的 URL**（例如 `https://a1b2c3d4.ngrok.io`）

3. **在 Line Developers Console 中設定 Webhook URL**：
   `https://a1b2c3d4.ngrok.io/callback`

## 更新機器人

當機器人有新功能或修復時，您可以按照以下步驟更新：

### 使用 Docker 更新

1. **獲取最新代碼**：
   ```bash
   cd Line_DC_bot
   git pull origin main
   ```

2. **重建並重啟容器**：
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

3. **查看更新後的日誌**：
   ```bash
   docker-compose logs -f
   ```

### 疑難排解更新問題

如果更新後出現問題：

1. **檢查 `.env` 文件**：
   - 新版本可能需要額外的環境變數
   - 對比 `.env.example` 和您的 `.env` 文件

2. **清理 Docker 緩存**：
   ```bash
   docker system prune -a
   ```

3. **查看詳細錯誤日誌**：
   ```bash
   docker-compose logs -f
   ```

## 詳細配置指南

### Discord 機器人設定

1. 前往 [Discord Developer Portal](https://discord.com/developers/applications)
2. 創建一個新的應用程式
3. 前往 "Bot" 分頁並創建一個機器人
4. 開啟 "Message Content Intent" 和 "Server Members Intent"
5. 複製機器人的 Token 並填入 `.env` 檔案
6. 使用 OAuth2 URL 生成器邀請機器人到您的伺服器
   - 所需權限：Send Messages, Read Messages/View Channels, Use Slash Commands
7. 右鍵點擊您想要連接的頻道 → Copy ID，填入 `.env` 檔案的 `DISCORD_CHANNEL_ID`

### Line 機器人設定

1. 前往 [Line Developers Console](https://developers.line.biz/console/)
2. 創建一個提供者和頻道（Messaging API 類型）
3. 在 "Messaging API" 分頁中獲取 Channel Secret 和 Channel Access Token
4. 填入 `.env` 檔案
5. 設定 Webhook URL 為您的 Ngrok URL + `/callback`
6. 將機器人加入您想要連接的 Line 群組
7. 在群組中發送測試訊息，從應用程式日誌中獲取 Group ID，填入 `.env` 檔案的 `LINE_GROUP_ID`

## 使用方法

### 從 Line 發送訊息到 Discord

直接在已加入機器人的 Line 群組中發送訊息，機器人會自動將訊息轉發到 Discord 頻道。

### 從 Discord 發送訊息到 Line

在 Discord 中使用斜線指令：
```
/say_line 您的訊息內容
```

訊息將被發送到 Line 群組，並顯示為：`[Discord] 您的Discord名稱: 您的訊息內容`

## Docker 相關命令

### 啟動容器
```bash
docker-compose up -d
```

### 停止容器
```bash
docker-compose down
```

### 查看日誌
```bash
docker-compose logs -f
```

### 重建容器
```bash
docker-compose build --no-cache
```

### 查看容器狀態
```bash
docker-compose ps
```

## 在 Linux 伺服器上部署

在 Linux 伺服器上部署與在本地機器上相同，但您可能需要考慮以下額外步驟：

1. **安裝 Docker 和 Docker Compose**：
   ```bash
   # 在 Ubuntu/Debian 上
   sudo apt update
   sudo apt install docker.io docker-compose
   
   # 設定權限
   sudo usermod -aG docker $USER
   newgrp docker
   ```

2. **設定防火牆**：
   ```bash
   sudo ufw allow 8000/tcp
   ```

3. **設定持久的公開 URL**：
   - 使用 Nginx + Let's Encrypt 設定 HTTPS 反向代理
   - 或使用 [serveo.net](https://serveo.net/) 等服務

4. **設定為系統服務**：
   ```bash
   # 創建 systemd 服務文件
   sudo nano /etc/systemd/system/line-discord-bot.service
   ```
   
   服務文件內容：
   ```
   [Unit]
   Description=Line Discord Bot Docker Compose
   Requires=docker.service
   After=docker.service

   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/path/to/Line_DC_bot
   ExecStart=/usr/bin/docker-compose up -d
   ExecStop=/usr/bin/docker-compose down
   TimeoutStartSec=0

   [Install]
   WantedBy=multi-user.target
   ```
   
   啟用服務：
   ```bash
   sudo systemctl enable line-discord-bot
   sudo systemctl start line-discord-bot
   ```

## 注意事項

- 一個機器人實例目前只支援連接一個 Line 群組和一個 Discord 頻道
- 如要支援多個群組，需要修改程式碼或運行多個機器人實例
- Line 的圖片、貼圖等非文字內容在轉發到 Discord 時會自動處理
- 請妥善保管您的 API 密鑰，不要將 `.env` 檔案上傳到公開的版本控制系統
- Docker 容器會自動重啟，除非明確停止

## 故障排除

- **找不到 Discord 頻道**：確認 `DISCORD_CHANNEL_ID` 填寫正確，且機器人已加入該頻道
- **Line Webhook 驗證失敗**：確認 `LINE_CHANNEL_SECRET` 填寫正確，且 Webhook URL 正確
- **Discord 斜線指令無法使用**：重啟機器人，等待斜線指令同步完成
- **找不到 Line 群組 ID**：在群組中發送測試訊息，查看應用程式日誌獲取 Group ID
- **Docker 權限問題**：使用 `sudo usermod -aG docker $USER` 將用戶添加到 docker 群組
- **依賴項問題**：如果更新後出現缺少依賴項錯誤，使用 `docker-compose build --no-cache` 重新構建容器

## 高級使用

### 自定義 Docker 配置

如果您需要自定義 Docker 設定，可以編輯 `docker-compose.yml` 文件：
```yaml
version: '3'

services:
  line-discord-bot:
    build: .
    container_name: line-discord-bot
    volumes:
      - ./.env:/app/.env
      - ./temp_images:/app/temp_images
    ports:
      - "8000:8000"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
```

### 備份設定

定期備份您的 `.env` 文件和其他重要數據：
```bash
cp .env .env.backup
```

## 貢獻與支援

歡迎提交 Issues 和 Pull Requests 來改進這個機器人。如有任何問題，請在 GitHub 上開 Issue。

## 授權

MIT