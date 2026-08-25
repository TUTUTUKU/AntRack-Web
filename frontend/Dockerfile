# 前端 Dockerfile：多阶段构建（Node 构建 + Nginx 部署）

# ===== 阶段1：构建 =====
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --registry https://registry.npmmirror.com
COPY . .
RUN npm run build

# ===== 阶段2：部署 =====
FROM nginx:alpine
# 安装 curl：用于容器健康检查（alpine 默认没有 wget/curl）
RUN apk add --no-cache curl \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
