# 智能法律问答系统（面试演示版）

这是一个基于 Flask 的法律问答系统，支持多轮对话上下文，并通过通义千问 API 生成法律咨询参考答案。

## 功能特性

- 法律问题智能问答（中文场景）
- 支持多轮会话记忆（Session）
- 支持法律类别辅助提问
- 回答包含风险提示，适合作品集演示

## 技术栈

- 后端：Flask
- 模型调用：OpenAI Python SDK（DashScope 兼容模式）
- 提示词：LangChain PromptTemplate
- 前端：Jinja2 + Bootstrap
- 部署：Gunicorn + Docker

## 本地启动

### 1) 安装依赖

```bash
pip install -r requirements.txt
```

### 2) 配置环境变量

复制 `.env.example` 为 `.env`，并填写你的密钥：

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

关键变量：

- `DASHSCOPE_API_KEY`: 通义 API Key（必填）
- `FLASK_SECRET_KEY`: 会话密钥（建议随机字符串）

### 3) 运行项目

```bash
python app.py
```

打开浏览器访问：`http://127.0.0.1:5000`

## 生产部署（Docker）

### 1) 构建镜像

```bash
docker build -t legal-qa-app .
```

### 2) 启动容器

```bash
docker run -d --name legal-qa \
  -p 5000:5000 \
  --env-file .env \
  legal-qa-app
```

访问：`http://<你的服务器IP>:5000`

## 生产部署（推荐：Nginx 反向代理）

使用项目内置的 `docker-compose.prod.yml`，可同时启动 Flask + Nginx。

### 1) 启动服务

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 2) 检查运行状态

```bash
docker compose -f docker-compose.prod.yml ps
```

### 3) 访问系统

访问：`http://<你的服务器IP>`

健康检查：`http://<你的服务器IP>/health`

说明：

- Nginx 已内置基础限流（每 IP 每分钟约 20 次请求）。
- 应用层也有 Session 级限流（每 60 秒最多 8 次提问），防止演示环境被刷。
- 如需 HTTPS，可在服务器 Nginx 上继续配置证书（Let's Encrypt）。

## 云服务器上线建议（给面试官访问）

1. 购买轻量云服务器（2C2G 起步即可）
2. 安装 Docker 并部署本项目
3. 开放安全组端口 `5000`（或通过 Nginx 转发到 `80/443`）
4. 配置 HTTPS（推荐使用 Nginx + Let's Encrypt）
5. 把访问地址发给面试官（如 `https://law-demo.xxx.com`）

## 注意事项

- 本系统回答仅供法律科普，不构成正式法律意见。
- 生产环境务必设置强随机 `FLASK_SECRET_KEY`。
- `.env` 文件不要提交到公开仓库。
- 公开演示建议绑定域名并开启 HTTPS，提升可信度与可访问性。
