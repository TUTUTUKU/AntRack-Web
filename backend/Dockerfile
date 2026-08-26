# AntRack 蚁仓后端 Dockerfile
# Python 3.10 (FastAPI 0.110 + SQLAlchemy 2 + pandas) · 单 SQLite 持久化
# 构建: docker build -t antrack/backend:latest .
# 单容器: docker run -d --name antrack-backend -p 8000:8000 -v ./data:/app/data -v ./static:/app/static antrack/backend:latest
# 推荐:   用同目录下 docker-compose up -d (带卷 + 健康检查 + 重启)
FROM python:3.10-slim


# 时区固定为 Asia/Shanghai（日志 / JWT 过期时间都按北京时间走）
ENV TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 系统依赖：
#   gcc/libffi-dev/pkg-config/libssl-dev → 编译 bcrypt / cryptography / cffi (python-jose)
#   tzdata → 让 TZ 生效
#   curl   → 容器内健康检查用 (HEALTHCHECK 调 /)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    pkg-config \
    tzdata \
    curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# ---------- 依赖层缓存 ----------
# 先只 copy requirements.txt，改代码再构建时直接复用缓存的 pip install 层
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt

# ---------- 源码 ----------
COPY . .

# 确保 data / static 目录存在（Docker 卷挂载到空目录也没事）
RUN mkdir -p /app/data /app/static \
 && chmod -R 755 /app/data /app/static

EXPOSE 8000

# ---------- 健康检查 ----------
# 10s 起开始探，每 30s 探一次，3 次失败标记 unhealthy（docker ps 能看到状态）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/ || exit 1

# uvicorn 常驻启动（startup 里会 Base.metadata.create_all + init_db 建表 + 写默认 admin）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
