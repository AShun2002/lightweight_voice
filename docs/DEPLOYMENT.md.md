# 轻量级语音问答服务部署指南

## 1. 系统架构

```mermaid
graph LR
    Client[客户端/Postman/网页] --> FastAPI[FastAPI服务层]
    FastAPI --> Route[/api/ask 统一接口]
    Route --> VoiceChat[语音问答核心调度层]
    
    VoiceChat --> ASR[ASR语音识别模块]
    VoiceChat --> LLM[LLM问答推理模块]
    VoiceChat --> TTS[TTS语音合成模块]
    
    subgraph Providers能力层
        ASR --> QwenASR(通义千问语音识别)
        LLM --> QwenLLM(通义大模型问答)
        TTS --> EdgeTTS(Edge语音合成)
    end
    
    VoiceChat --> Session[会话管理]
    VoiceChat --> CRM[用户信息提取存储SQLite]
    Session --> SQLite[(会话数据库)]
    CRM --> SQLite
```

---

## 2. 环境要求

| 项目 | 要求 |
|------|------|
| Python 版本 | 3.10 ~ 3.12 |
| 操作系统 | Windows / Linux / macOS 全平台兼容 |
| 网络 | 可正常访问 ASR / LLM / TTS 厂商接口 |
| 可选硬件 | NVIDIA 显卡 + CUDA 环境，可加速推理 |

---

## 3. 部署方式一：本地源码部署

适合开发调试场景。

### 3.1 克隆项目

```bash
git clone <你的仓库地址>
cd lightweight_voice
```

### 3.2 创建虚拟环境（推荐）

```bash
# 使用 venv
python -m venv venv

# Windows 激活
venv\Scripts\activate

# Linux/macOS 激活
source venv/bin/activate
```

### 3.3 安装依赖

```bash
pip install -r requirements.txt
```

### 3.4 配置服务

复制配置示例文件并填入你的密钥：

```bash
# Windows
copy config.yaml.example config.yaml

# Linux/macOS
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，填入 API 密钥等配置：

```yaml
llm:
  api_key: "你的通义千问 API Key"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  model: "qwen-turbo"

asr:
  api_key: "你的通义千问 API Key"
  model: "qwen3-asr-flash"

tts:
  voice: "zh-CN-XiaoxiaoNeural"

system_prompt: "你是一个友好的语音助手，回答要简洁明了，适合语音播报，不要太长。"

server:
  host: "0.0.0.0"
  port: 8000
  temp_dir: "temp_audio"
```

> **注意**：`config.yaml` 包含敏感信息，已加入 `.gitignore`，不会提交到代码库。

### 3.5 启动服务

```bash
# 方式一：直接运行
python api.py

# 方式二：使用 uvicorn（推荐，支持热重载）
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 3.6 验证服务

服务启动后，访问以下地址验证：

| 地址 | 用途 |
|------|------|
| http://127.0.0.1:8000/api/health | 健康检查，返回服务状态 |
| http://127.0.0.1:8000/docs | Swagger 交互式文档，可在线调试 |
| http://127.0.0.1:8000/ | 网页演示前端 |
| http://127.0.0.1:8000/api/ask | 核心问答接口（POST） |

---

## 4. 部署方式二：Docker 部署

适合生产环境或快速部署场景。

### 4.1 准备配置文件

在项目根目录创建 `config.yaml`，参考 3.4 节配置。

### 4.2 构建镜像

```bash
docker build -t lightweight-voice .
```

### 4.3 运行容器

```bash
docker run -d \
  --name voice-qa-service \
  -p 8000:8000 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/temp_audio:/app/temp_audio \
  -v $(pwd)/crm.db:/app/crm.db \
  --restart always \
  lightweight-voice
```

参数说明：
- `-p 8000:8000`：映射端口
- `-v config.yaml`：挂载配置文件
- `-v temp_audio`：挂载临时音频目录
- `-v crm.db`：挂载数据库文件，持久化用户数据
- `--restart always`：容器异常退出时自动重启

### 4.4 查看日志

```bash
docker logs -f voice-qa-service
```

---

## 5. 部署方式三：Docker Compose 部署

适合需要编排管理的场景。

### 5.1 启动服务

```bash
docker-compose up -d
```

### 5.2 查看状态

```bash
docker-compose ps
```

### 5.3 停止服务

```bash
docker-compose down
```

---

## 6. 配置文件详解

`config.yaml` 包含以下配置项：

### 6.1 LLM 配置（大语言模型）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| api_key | 通义千问 API 密钥 | 必填 |
| base_url | API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| model | 使用的模型 | `qwen-turbo` |

可选模型：
- `qwen-turbo`：快速响应，适合日常对话
- `qwen-plus`：能力更强，响应稍慢
- `qwen-max`：最强能力，适合复杂任务

### 6.2 ASR 配置（语音识别）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| api_key | 通义千问 API 密钥 | 必填 |
| model | 使用的模型 | `qwen3-asr-flash` |

### 6.3 TTS 配置（语音合成）

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| voice | 发音人音色 | `zh-CN-XiaoxiaoNeural` |

常用中文音色：
- `zh-CN-XiaoxiaoNeural`：晓晓（女声，亲切自然）
- `zh-CN-YunxiNeural`：云希（男声，沉稳）
- `zh-CN-YunyangNeural`：云扬（男声，新闻播报）
- `zh-CN-XiaoyiNeural`：晓伊（女声，活泼）

### 6.4 系统提示词

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| system_prompt | AI 助手的系统提示词 | 友好的语音助手 |

可根据业务场景自定义，例如：
```yaml
system_prompt: "你是一个专业的客服助手，回答用户问题要准确、简洁，控制在3句话以内。"
```

### 6.5 服务配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| host | 监听地址 | `0.0.0.0` |
| port | 监听端口 | `8000` |
| temp_dir | 临时音频文件目录 | `temp_audio` |

---

## 7. 接口调用示例

### 7.1 纯文本提问

```bash
curl -X POST "http://127.0.0.1:8000/api/ask" \
  -F "text=你好，介绍一下这个服务" \
  -F "return_audio=false"
```

### 7.2 语音提问并返回语音

```bash
curl -X POST "http://127.0.0.1:8000/api/ask" \
  -F "audio=@question.mp3" \
  -F "return_audio=true"
```

### 7.3 使用 Postman

导入 `examples/postman_collection.json` 到 Postman 中，即可使用预置的接口测试用例。

---

## 8. 常见问题排查

### 8.1 服务启动失败

**问题**：提示 `配置文件不存在：config.yaml`

**解决**：确保项目根目录下有 `config.yaml` 文件，可从 `config.yaml.example` 复制。

---

**问题**：提示 `ModuleNotFoundError: No module named 'xxx'`

**解决**：依赖未安装，执行 `pip install -r requirements.txt`。

---

### 8.2 API 调用失败

**问题**：返回错误码 2001/2002/2003（ASR/LLM/TTS 失败）

**解决**：
1. 检查 `config.yaml` 中的 API Key 是否正确
2. 检查网络是否能访问对应服务
3. 确认账户余额是否充足

---

**问题**：返回错误码 1001（参数错误）

**解决**：
1. 确保 `text` 和 `audio` 至少传一个
2. 检查请求格式是否为 `multipart/form-data`

---

### 8.3 语音识别效果不好

**建议**：
1. 使用清晰的音频，采样率建议 16kHz 以上
2. 避免背景噪音
3. 语速适中，不要太快

---

### 8.4 Docker 部署问题

**问题**：容器启动后立即退出

**解决**：查看日志 `docker logs voice-qa-service`，通常是配置文件问题。

---

**问题**：容器内无法访问外部网络

**解决**：检查 Docker 网络设置，确保容器可以访问外网。

---

## 9. 生产环境部署建议

### 9.1 使用反向代理

建议使用 Nginx 作为反向代理，配置 HTTPS 和限流：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 9.2 日志管理

建议配置日志轮转，避免日志文件过大。

### 9.3 监控告警

- 监控服务健康状态
- 监控 API 调用量和响应时间
- 设置异常告警

### 9.4 数据备份

定期备份 `crm.db` 数据库文件，防止数据丢失。

### 9.5 安全建议

1. 不要将 `config.yaml` 提交到代码库（已加入 .gitignore）
2. 生产环境使用强密钥
3. 配置 API 访问限流
4. 定期更新依赖包，修复安全漏洞

---

## 10. 目录结构说明

```
lightweight_voice/
├── api.py                  # FastAPI 服务入口
├── voice_chat.py           # 语音问答核心逻辑
├── config.py               # 配置加载
├── config.yaml             # 配置文件（不提交）
├── config.yaml.example     # 配置示例
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像构建
├── docker-compose.yml      # Docker Compose 配置
├── .gitignore              # Git 忽略文件
├── README.md               # 项目说明
├── crm.py                  # CRM 用户信息管理
├── providers/              # 能力提供层
│   ├── asr/                # 语音识别
│   │   ├── base.py         # 抽象基类
│   │   └── qwen_asr.py     # 通义千问实现
│   ├── llm/                # 大语言模型
│   │   ├── base.py         # 抽象基类
│   │   └── qwen_llm.py     # 通义千问实现
│   └── tts/                # 语音合成
│       ├── base.py         # 抽象基类
│       └── edge_tts.py     # Edge TTS 实现
├── docs/                   # 文档
│   ├── API.md              # API 接口文档
│   └── DEPLOYMENT.md       # 部署指南（本文档）
├── examples/               # 示例
│   └── postman_collection.json  # Postman 集合
├── static/                 # 静态文件
│   └── index.html          # 网页演示
└── temp_audio/             # 临时音频文件（不提交）
```
