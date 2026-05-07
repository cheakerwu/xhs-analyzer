# ECS 部署与更新

本项目支持直接在 ECS 上通过 Git 拉取代码并用 Docker Compose 部署。

## 推荐配置

- Ubuntu 22.04 LTS
- 2 核 4GB 起步，推荐 2 核 8GB
- 磁盘 40GB 以上
- 安全组开放 `80`（Nginx）和 `8088`（直连调试用）
- 支持 Ubuntu / Debian / CentOS / Alibaba Cloud Linux

## 首次部署

### 1. 安装 Docker

```bash
apt update
apt install -y git ca-certificates curl gnupg nginx
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2. 拉取代码并启动

```bash
cd /opt
git clone https://github.com/cheakerwu/xhs-analyzer.git
cd xhs-analyzer
cp .env.example .env
chmod +x scripts/*.sh
./scripts/deploy.sh
```

部署脚本会自动：
- 配置 Docker 国内镜像加速（`/etc/docker/daemon.json`）
- 使用清华 pip 镜像源安装 Python 依赖
- 构建并启动 Docker 容器
- 如果检测到 Nginx 已安装，自动配置反向代理并重载

### 3. 配置子域名（Cloudflare）

1. 登录 [Cloudflare 控制台](https://dash.cloudflare.com)
2. 选择 `minamiovo.xyz` 域名
3. 进入 **DNS** → **记录**
4. 添加记录：
   - **类型**: A
   - **名称**: `xhs`
   - **内容**: `<ECS公网IP>`
   - **代理状态**: 已代理（橙色云朵，自动提供 HTTPS）
5. 保存后等待 DNS 生效（通常 1-2 分钟）

生效后访问：`https://xhs.minamiovo.xyz`

## 更新代码

```bash
cd /opt/xhs-analyzer
git pull
./scripts/deploy.sh
```

## 大模型配置

推荐在页面里的"大模型设置"中填写接口地址、模型名和 API Key。配置会保存到：

```text
data/settings.json
```

也可以在 `.env` 里预置默认值：

```bash
XHS_LLM_API_KEY=你的Key
XHS_LLM_BASE_URL=https://api.openai.com/v1
XHS_LLM_MODEL=gpt-4o-mini
```

## 数据持久化

`docker-compose.yml` 会挂载：

```text
./data:/app/data
./browser_data:/app/MediaCrawler-main/browser_data
```

容器重启或更新镜像不会丢失：

- 大模型设置
- 历史分析记录
- 采集原始数据
- 浏览器登录态

## 备份

```bash
./scripts/backup.sh
```

备份文件会生成到 `backups/`。

## Nginx 配置说明

`scripts/nginx-xhs.conf` 配置了：
- 监听 80 端口，域名为 `xhs.minamiovo.xyz`
- 反向代理到容器的 `127.0.0.1:8088`
- `proxy_read_timeout 300s`：采集任务可能耗时较长，需要较长的读取超时
- `client_max_body_size 50m`：允许较大的请求体

Cloudflare 开启代理后自动处理 HTTPS，ECS 端无需配置 SSL 证书。

## 注意

小红书采集涉及登录态和浏览器自动化。首次在 ECS 使用时可能需要扫码登录。建议控制采集频率和数量，并遵守平台规则与法律法规。
