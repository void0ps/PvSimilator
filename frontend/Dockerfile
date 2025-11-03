# 使用官方Node镜像（腾讯云镜像加速）
FROM node:18.17.1-bullseye

# 配置NPM镜像源（多重镜像源策略）
RUN npm config set registry https://registry.npmmirror.com/ || \
    npm config set registry https://registry.npm.taobao.org/ || \
    npm config set registry https://registry.npmjs.org/

# 1. 设置内存限制和工作目录
ENV NODE_OPTIONS="--max-old-space-size=4096"
WORKDIR /app

# 2. 复制package文件
COPY package*.json ./

# 3. 安装依赖（带内存限制）
RUN npm install --unsafe-perm --legacy-peer-deps && \
    npm rebuild --update-binary && \
    find node_modules/.bin -type f -exec chmod 755 {} \; && \
    npm cache clean --force

# 4. 复制源代码
COPY . .

# 5. 构建应用（带内存限制）
USER root
RUN npm run build && \
    chown -R 1000:1000 dist

# 6. 运行配置
USER 1000
EXPOSE 3000
ENV VITE_API_BASE_URL=/api/v1
CMD ["npx", "serve", "-s", "dist", "-l", "3000"]