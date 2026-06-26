# lightweight_voice 语音问答独立服务
## 项目概述
本项目完成问答模块解耦，独立部署语音问答核心逻辑，完全移除ESP32硬件相关代码；基于FastAPI提供REST接口，同时支持文本、语音两种输入，可返回文本+合成语音音频。

## 系统架构图
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