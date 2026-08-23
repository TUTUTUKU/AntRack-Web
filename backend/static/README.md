# backend/static/
此目录用于存放物料图片等用户上传的静态资源。
- 通过 API /static/<文件名> 访问（由 FastAPI StaticFiles 托管）。
- Docker 部署时此目录作为 volume 挂载，容器重建不丢失图片。
