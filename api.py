import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from voice_chat import VoiceChat
from config import config

# ========== 创建 FastAPI 应用 ==========
app = FastAPI(
    title="轻量级语音交互服务",
    version="1.0.0",
    description="基于 ASR + LLM + TTS 的轻量级语音交互服务，支持文本和语音问答"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 临时文件目录
TEMP_DIR = config["server"]["temp_dir"]
os.makedirs(TEMP_DIR, exist_ok=True)


# ========== 统一响应格式工具 ==========

def success_response(data=None, message="success"):
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error_response(code: int, message: str, data=None):
    """错误响应"""
    return JSONResponse(
        status_code=200,  # HTTP 状态码还是 200，业务错误码在 body 里
        content={
            "code": code,
            "message": message,
            "data": data
        }
    )


# ========== 错误码定义 ==========
ERROR_CODES = {
    0: "success",
    1001: "参数错误",
    1002: "会话不存在",
    2001: "语音识别失败",
    2002: "AI 对话失败",
    2003: "语音合成失败",
    3001: "用户档案不存在",
    5000: "服务器内部错误"
}


# ========== 会话管理器 ==========

class SessionManager:
    """会话管理器：管理多个用户的对话"""
    
    def __init__(self):
        self.sessions = {}  # session_id -> VoiceChat 对象
    
    def get_session(self, session_id):
        """获取或创建会话"""
        if session_id not in self.sessions:
            self.sessions[session_id] = VoiceChat(config)
            self.sessions[session_id].set_session_id(session_id)
        return self.sessions[session_id]
    
    def create_session(self):
        """创建新会话，返回 session_id"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = VoiceChat(config)
        self.sessions[session_id].set_session_id(session_id)
        return session_id
    
    def clear_session(self, session_id):
        """清空会话历史"""
        if session_id in self.sessions:
            self.sessions[session_id].clear_history()
            return True
        return False
    
    def delete_session(self, session_id):
        """删除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

# 全局会话管理器
session_manager = SessionManager()


# ========== 请求/响应模型 ==========

class TextChatRequest(BaseModel):
    """文字对话请求"""
    message: str
    session_id: str = None


class AskRequest(BaseModel):
    """统一问答请求（文本方式）"""
    text: str
    session_id: str = None
    return_audio: bool = True  # 是否返回语音


class ProfileUpdateRequest(BaseModel):
    """用户信息更新请求"""
    name: str = None
    age: int = None
    gender: str = None
    phone: str = None
    email: str = None
    location: str = None
    interests: list = None
    requirements: list = None
    notes: str = None


# ========== 首页 ==========

@app.get("/", response_class=HTMLResponse, summary="首页 - 语音助手网页")
async def root():
    """首页：语音助手网页界面"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "static", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health", summary="服务状态检查")
async def health_check():
    """检查服务是否正常运行"""
    return success_response({
        "status": "ok",
        "version": "1.0.0",
        "message": "语音交互服务运行中"
    })


# ========== 会话管理接口 ==========

@app.post("/api/session/create", summary="创建新会话")
async def create_session():
    """创建一个新的对话会话，返回 session_id"""
    session_id = session_manager.create_session()
    return success_response({"session_id": session_id})


@app.post("/api/session/clear", summary="清空会话历史")
async def clear_session(session_id: str):
    """清空指定会话的对话历史"""
    success = session_manager.clear_session(session_id)
    if success:
        return success_response(message="对话历史已清空")
    else:
        return error_response(1002, "会话不存在")


@app.delete("/api/session/delete", summary="删除会话")
async def delete_session(session_id: str):
    """删除指定的会话"""
    success = session_manager.delete_session(session_id)
    if success:
        return success_response(message="会话已删除")
    else:
        return error_response(1002, "会话不存在")


# ========== 核心问答接口（统一入口）⭐ ==========

@app.post("/api/ask", summary="统一问答接口（支持文本/语音）")
async def ask(
    request: Request,
    text: str = Form(None),
    audio: UploadFile = File(None),
    session_id: str = Form(None),
    return_audio: bool = Form(True)
):
    """
    统一问答接口，支持文本和语音输入
    
    - 文本输入：传 text 参数
    - 语音输入：传 audio 文件
    - 两者都传的话，优先使用语音
    """
    try:
        # 获取或创建会话
        session_id = session_id or session_manager.create_session()
        vc = session_manager.get_session(session_id)
        
        user_text = ""
        
        # 1. 处理输入
        if audio:
            # 语音输入
            input_filename = f"{TEMP_DIR}/input_{uuid.uuid4()}.mp3"
            with open(input_filename, "wb") as f:
                content = await audio.read()
                f.write(content)
            
            # ASR 识别
            user_text = vc.asr.transcribe(input_filename)
            
        elif text:
            # 文本输入
            user_text = text
            
        else:
            return error_response(1001, "请提供 text 或 audio 参数")
        
        # 2. LLM 对话
        reply_text = vc.chat_text(user_text)
        
        # 3. TTS 语音合成（如果需要）
        audio_url = None
        if return_audio:
            output_filename = f"{TEMP_DIR}/output_{uuid.uuid4()}.mp3"
            await vc.tts.synthesize(reply_text, output_filename)
            audio_url = f"/api/audio/{os.path.basename(output_filename)}"
        
        # 4. 返回结果
        return success_response({
            "session_id": session_id,
            "user_text": user_text,
            "reply_text": reply_text,
            "audio_url": audio_url
        })
        
    except Exception as e:
        return error_response(5000, f"服务器错误：{str(e)}")


# ========== 兼容旧接口（保留） ==========

@app.post("/api/chat/text", summary="文字对话（兼容）")
async def chat_text(request: TextChatRequest):
    """文字对话接口（兼容旧版）"""
    try:
        session_id = request.session_id or session_manager.create_session()
        vc = session_manager.get_session(session_id)
        reply = vc.chat_text(request.message)
        
        return success_response({
            "reply": reply,
            "session_id": session_id
        })
    except Exception as e:
        return error_response(5000, str(e))


@app.post("/api/chat/voice", summary="语音对话（兼容）")
async def chat_voice(audio: UploadFile = File(...), session_id: str = Form(None)):
    """语音对话接口（兼容旧版）"""
    try:
        session_id = session_id or session_manager.create_session()
        vc = session_manager.get_session(session_id)
        
        input_filename = f"{TEMP_DIR}/input_{uuid.uuid4()}.mp3"
        with open(input_filename, "wb") as f:
            content = await audio.read()
            f.write(content)
        
        output_filename = f"{TEMP_DIR}/output_{uuid.uuid4()}.mp3"
        
        user_text, reply_text, output_file = await vc.chat(
            input_filename, output_filename
        )
        
        return success_response({
            "user_text": user_text,
            "reply_text": reply_text,
            "audio_url": f"/api/audio/{os.path.basename(output_file)}",
            "session_id": session_id
        })
    
    except Exception as e:
        return error_response(5000, str(e))


@app.get("/api/audio/{filename}", summary="获取音频文件")
async def get_audio(filename: str):
    """获取生成的音频文件"""
    file_path = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="音频文件不存在")
    return FileResponse(file_path, media_type="audio/mpeg")


# ========== CRM 相关接口 ==========

from crm import crm_manager

@app.get("/api/crm/profile", summary="获取用户信息")
async def get_crm_profile(session_id: str):
    """获取指定会话的用户信息"""
    profile = crm_manager.get_profile(session_id)
    if profile:
        return success_response(profile)
    else:
        return error_response(3001, "用户档案不存在")


@app.put("/api/crm/profile", summary="更新用户信息")
async def update_crm_profile(session_id: str, data: ProfileUpdateRequest):
    """手动更新用户信息"""
    profile = crm_manager.update_profile(session_id, **data.dict(exclude_none=True))
    return success_response(profile)


@app.get("/api/crm/profiles", summary="获取所有用户列表")
async def list_crm_profiles(limit: int = 50):
    """获取所有用户档案列表"""
    profiles = crm_manager.list_all_profiles(limit)
    return success_response({
        "total": len(profiles),
        "profiles": profiles
    })


@app.delete("/api/crm/profile", summary="删除用户档案")
async def delete_crm_profile(session_id: str):
    """删除指定用户的档案"""
    success = crm_manager.delete_profile(session_id)
    if success:
        return success_response(message="用户档案已删除")
    else:
        return error_response(3001, "用户档案不存在")


@app.post("/api/crm/extract", summary="手动触发用户信息提取")
async def extract_user_info(session_id: str):
    """手动从对话历史中提取用户信息"""
    vc = session_manager.get_session(session_id)
    if vc:
        extracted = crm_manager.extract_user_info(session_id, vc.history)
        return success_response({
            "extracted": extracted,
            "profile": crm_manager.get_profile(session_id)
        })
    else:
        return error_response(1002, "会话不存在")


# ========== 全局异常处理 ==========

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，统一返回格式"""
    return error_response(5000, f"服务器内部错误：{str(exc)}")


# ========== 启动服务 ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=config["server"]["host"], 
        port=config["server"]["port"]
    )