FROM python:3.10-slim-bookworm AS builder

WORKDIR /app

# 安装系统依赖（ffmpeg + 编译工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装 Python 包
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 最终镜像
FROM python:3.10-slim-bookworm

# 从 builder 复制 ffmpeg 和已安装的 Python 包
COPY --from=builder /usr/bin/ffmpeg /usr/bin/
COPY --from=builder /usr/bin/ffprobe /usr/bin/
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# 复制项目文件
COPY . .

# 创建数据及输出目录
RUN mkdir -p /app/data /app/output

# 赋予入口脚本执行权限
RUN chmod +x entrypoint.sh

EXPOSE 8000

# 健康检查（每 30 秒检查 HTTP 服务）
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/tv.m3u || exit 1

ENTRYPOINT ["./entrypoint.sh"]
