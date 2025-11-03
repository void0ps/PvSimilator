# 使用官方Python镜像（腾讯云镜像加速）
FROM python:3.10-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 使用多重镜像源策略（优先清华源，失败时使用阿里云源）
RUN set -e; \
    # 先尝试清华源
    sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list && \
    apt-get update || (echo "清华源失败，尝试阿里云源..." && \
    sed -i 's/mirrors.tuna.tsinghua.edu.cn/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update) && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/* && \
    # 设置PIP源（优先清华源，失败时使用阿里云源）
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/ || \
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

# 先单独安装依赖（利用缓存层）
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 非root用户运行
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
