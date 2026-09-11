FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl --no-install-recommends && rm -rf /var/lib/apt/lists/*
# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 复制代码
COPY app/ ./app/
# 初始化数据库
RUN mkdir -p /data
RUN python -c "import sqlite3; c=sqlite3.connect('/data/demo.db'); c.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL)'); c.commit(); c.close()"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
