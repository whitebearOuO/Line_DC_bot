FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製 requirements.txt
COPY requirements.txt .

# 安裝所有依賴項
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式代碼
COPY . .

# 建立臨時圖片資料夾
RUN mkdir -p temp_images

# 運行應用程式
CMD ["python", "main.py"]