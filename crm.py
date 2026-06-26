import sqlite3
import json
import os
from datetime import datetime
from openai import OpenAI
from config import config

class CRMManager:
    """CRM 用户信息管理器"""
    
    def __init__(self, db_path="crm.db"):
        self.db_path = db_path
        self._init_db()
        
        # LLM 客户端，用于提取用户信息
        self.llm_client = OpenAI(
            api_key=config["llm"]["api_key"],
            base_url=config["llm"]["base_url"]
        )
        self.llm_model = config["llm"]["model"]
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 用户信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                name TEXT,
                age INTEGER,
                gender TEXT,
                phone TEXT,
                email TEXT,
                location TEXT,
                interests TEXT,
                requirements TEXT,
                notes TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_profile(self, session_id):
        """获取用户信息"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def create_profile(self, session_id):
        """创建新用户档案"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO user_profiles (session_id, created_at, updated_at)
                VALUES (?, ?, ?)
            ''', (session_id, now, now))
            conn.commit()
        except sqlite3.IntegrityError:
            # 已存在就不创建
            pass
        
        conn.close()
        return self.get_profile(session_id)
    
    def update_profile(self, session_id, **kwargs):
        """更新用户信息"""
        # 先确保用户存在
        profile = self.get_profile(session_id)
        if not profile:
            self.create_profile(session_id)
        
        now = datetime.now().isoformat()
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 只更新传入的字段
        update_fields = []
        values = []
        for key, value in kwargs.items():
            if value is not None and key != "id" and key != "session_id":
                update_fields.append(f"{key} = ?")
                # 列表类型转成 JSON 字符串存储
                if isinstance(value, list):
                    values.append(json.dumps(value, ensure_ascii=False))
                else:
                    values.append(value)
        
        if update_fields:
            update_fields.append("updated_at = ?")
            values.append(now)
            values.append(session_id)
            
            sql = f"UPDATE user_profiles SET {', '.join(update_fields)} WHERE session_id = ?"
            cursor.execute(sql, values)
            conn.commit()
        
        conn.close()
        return self.get_profile(session_id)
    
    def extract_user_info(self, session_id, dialogue_history):
        """
        从对话历史中提取用户信息
        :param dialogue_history: 对话历史列表
        :return: 提取到的用户信息字典
        """
        # 先获取已有的用户信息
        existing = self.get_profile(session_id) or {}
        
        # 构造对话历史文本
        dialogue_text = ""
        for msg in dialogue_history[-10:]:  # 只看最近10轮
            role = "用户" if msg["role"] == "user" else "助手"
            dialogue_text += f"{role}: {msg['content']}\n"
        
        # 构造 Prompt
        system_prompt = """
你是一个用户信息提取专家。请从对话中提取用户的关键信息，以 JSON 格式返回。

需要提取的字段：
- name: 用户姓名（不知道就返回 null）
- age: 用户年龄（数字，不知道就返回 null）
- gender: 性别（男/女/未知）
- phone: 电话号码（不知道就返回 null）
- email: 邮箱（不知道就返回 null）
- location: 所在地区/城市（不知道就返回 null）
- interests: 兴趣爱好列表（数组形式，不知道就返回空数组）
- requirements: 用户的需求/问题（数组形式，不知道就返回空数组）
- notes: 其他备注信息（字符串）

注意：
1. 只提取对话中明确提到的信息，不要猜测
2. 如果信息之前已经知道，这次对话没有新内容，就返回空的 JSON {}
3. 只返回新增或更新的信息，已有的不变的不用返回
4. 严格返回 JSON 格式，不要有其他文字
"""
        
        user_prompt = f"""
已有用户信息：
{json.dumps(existing, ensure_ascii=False, indent=2)}

最近对话：
{dialogue_text}

请提取对话中的新用户信息，只返回 JSON。
"""
        
        # 调用 LLM 提取
        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3  # 低温度，保证输出稳定
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 尝试解析 JSON
            try:
                # 有时候 LLM 会在 JSON 外面加 ```json 标记，处理一下
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                extracted = json.loads(result_text)
                
                # 更新用户信息
                if extracted:
                    self.update_profile(session_id, **extracted)
                
                return extracted
                
            except json.JSONDecodeError:
                print(f"⚠️ 用户信息提取失败，无法解析 JSON: {result_text}")
                return {}
                
        except Exception as e:
            print(f"❌ 用户信息提取出错: {e}")
            return {}
    
    def list_all_profiles(self, limit=50):
        """列出所有用户档案"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles ORDER BY updated_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_profile(self, session_id):
        """删除用户档案"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_profiles WHERE session_id = ?", (session_id,))
        conn.commit()
        affected = cursor.rowcount
        conn.close()
        return affected > 0


# 全局 CRM 管理器实例
crm_manager = CRMManager()