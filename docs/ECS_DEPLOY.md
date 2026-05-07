# ECS 部署与更新

本项目支持直接在 ECS 上通过 Git 拉取代码并用 Docker Compose 部署。

## 推荐配置

- Ubuntu 22.04 LTS
- 2 核 4GB 起步，推荐 2 核 8GB
- 磁盘 40GB 以上
- 安全组开放 `8088`，或用 Nginx 反向代理到 `80/443`

## 首次部署

```bash
apt update
apt install -y git ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

拉取代码并启动：

```bash
cd /opt
git clone https://github.com/cheakerwu/xhs-analyzer.git
cd xhs-analyzer
cp .env.example .env
chmod +x scripts/*.sh
./scripts/deploy.sh
```

访问：

```text
http://你的ECS公网IP:8088
```

## 更新代码

```bash
cd /opt/xhs-analyzer
git pull
./scripts/deploy.sh
```

## 大模型配置

推荐在页面里的“大模型设置”中填写接口地址、模型名和 API Key。配置会保存到：

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

## 注意

小红书采集涉及登录态和浏览器自动化。首次在 ECS 使用时可能需要扫码登录。建议控制采集频率和数量，并遵守平台规则与法律法规。
