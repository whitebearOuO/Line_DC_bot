FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 安裝 pipenv
RUN pip install pipenv

# 複製 Pipfile 和 Pipfile.lock (如果有)
COPY Pipfile* ./

# 安裝依賴 (不建立虛擬環境)
RUN pipenv install --system --deploy

# 複製應用程式代碼
COPY main.py ./
COPY .env.example ./.env.example

# 建立臨時圖片資料夾
RUN mkdir -p temp_images

# 運行應用程式
CMD ["python", "main.py"]