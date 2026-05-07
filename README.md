# 小红书主页分析器

这是一个基于 `MediaCrawler-main` 重新包装的分析应用，用于采集并分析小红书指定用户主页数据，并与自己的主页数据进行对比。

## 已实现能力

- 输入自己的主页链接和目标用户主页链接
- 调用 `MediaCrawler-main` 的小红书 creator 模式采集主页笔记、评论和创作者信息
- 分析目标用户的优势、内容特点、高频主题、高表现笔记
- 对比双方在平均互动、收藏率、评论率、分享率、爆款稳定度、正文长度上的差异
- 给出自己可以借鉴的内容方向和表达方式
- 以更直观的左右画像、条形差异和标签方式展示对比结果
- 可选接入 OpenAI 兼容接口的大模型增强分析
- 自动保存每次分析结果，并在页面中回看历史记录
- 提供简洁的前端页面和后端 API

## 目录结构

```text
xhs-analyzer/
  app/                  后端应用与分析逻辑
  web/                  前端页面
  data/runs/            每次用户主页采集后的本地数据
  data/history/         历史分析结果
  MediaCrawler-main/    原始采集能力
  start.bat             Windows 一键启动脚本
```

## 启动方式

项目已按你的环境配置为：

```text
E:\anaconda\envs\xhs-analyzer\python.exe
```

双击或运行：

```bat
start.bat
```

然后打开：

```text
http://127.0.0.1:8088
```

## 使用建议

1. 先确认本机 Chrome/Edge 已登录小红书，或者能在采集过程中扫码登录。
2. 主页链接优先使用完整链接，例如：

```text
https://www.xiaohongshu.com/user/profile/用户ID?xsec_token=...&xsec_source=...
```

也支持纯用户 ID，但完整链接通常更稳定。

3. 首次采集建议笔记数设置为 20 到 30，每篇评论数设置为 10 到 20。
4. 如果已经采集过同一个主页，页面默认会复用本地数据，速度会很快；需要重新采集时取消“优先复用本地数据”。

## API

- `GET /api/health`：服务状态
- `POST /api/analyze`：提交分析任务
- `GET /api/tasks/{task_id}`：查询任务进度和分析结果
- `GET /api/history`：历史记录列表
- `GET /api/history/{record_id}`：历史记录详情

## 大模型增强分析

大模型增强是可选能力。未配置 Key 时，系统会自动使用本地规则分析，不影响采集、对比和历史记录。

现在页面里已经有“大模型设置”，可以直接填写：

- 接口地址，例如 `https://api.openai.com/v1`
- 模型名称，例如 `gpt-4o-mini`
- API Key

保存后会写入：

```text
data/settings.json
```

打包给别人使用时，对方只需要在页面里填一次，不需要安装 Python，也不需要修改环境变量。

仍然保留环境变量作为默认值。如需在启动前预置默认配置，可以设置：

```bat
set XHS_LLM_API_KEY=你的_API_Key
set XHS_LLM_BASE_URL=https://api.openai.com/v1
set XHS_LLM_MODEL=gpt-4o-mini
start.bat
```

也可以使用其他兼容 `/chat/completions` 的服务，只要替换 `XHS_LLM_BASE_URL` 和 `XHS_LLM_MODEL` 即可。

## 打包迁移时的配置处理

如果做成免 Python 的压缩包或 exe，建议把以下目录作为可写数据目录保留在程序旁边：

```text
data/
  settings.json   大模型配置
  history/        分析历史
  runs/           采集原始数据
```

不要把 `data/settings.json` 写进只读安装目录。正式安装包可以把 `data/` 放在用户目录，便于保存 API Key 和历史记录。

## 合规提醒

请只采集你有合理使用理由的公开数据，控制频率和规模，不要用于骚扰、绕过限制、商业化抓取或任何违反平台规则与法律法规的用途。
