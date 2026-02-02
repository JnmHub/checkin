import time
from typing import Dict, Optional, List


class SessionManager:
    def __init__(self):
        # 存储 Token -> {user_id, role, expire_at}
        self._sessions: Dict[str, dict] = {}
        # 存储 "role_id" -> [token1, token2...] (双向索引，用于精准踢人)
        self._user_to_tokens: Dict[str, List[str]] = {}

    def set_session(self, token: str, user_id: int, role: str, expire_in_seconds: int):
        """保存凭证，role 传入 'admin' 或 'employee'"""
        expire_at = time.time() + expire_in_seconds
        self._sessions[token] = {
            "user_id": user_id,
            "role": role,
            "expire_at": expire_at
        }

        user_key = f"{role}_{user_id}"
        if user_key not in self._user_to_tokens:
            self._user_to_tokens[user_key] = []
        self._user_to_tokens[user_key].append(token)

    def get_session(self, token: str) -> Optional[dict]:
        """验证凭证，返回包含 user_id 和 role 的字典"""
        session = self._sessions.get(token)
        # 如果不存在或已过期
        if not session or time.time() > session["expire_at"]:
            if session:
                self.delete_session(token)  # 顺手清理掉过期数据
            return None
        return session

    def delete_session(self, token: str):
        """
        主动销毁单个凭证 (用户退出登录时调用)
        """
        session = self._sessions.get(token)
        if session:
            user_key = f"{session['role']}_{session['user_id']}"
            # 1. 从反向索引列表中移除该 token
            if user_key in self._user_to_tokens:
                if token in self._user_to_tokens[user_key]:
                    self._user_to_tokens[user_key].remove(token)
                # 如果该用户没有任何 token 了，直接删掉 key
                if not self._user_to_tokens[user_key]:
                    del self._user_to_tokens[user_key]

            # 2. 从主 session 字典中移除
            del self._sessions[token]

    def clear_user_sessions(self, user_id: int, role: str):
        """
        强制踢出该角色的所有登录 (禁用账号、修改密码时调用)
        """
        user_key = f"{role}_{user_id}"
        tokens = self._user_to_tokens.get(user_key, [])
        # 循环删除该用户下的所有 token 记录
        for token in tokens:
            if token in self._sessions:
                del self._sessions[token]

        # 清空索引
        if user_key in self._user_to_tokens:
            del self._user_to_tokens[user_key]


# 全局单例
session_manager = SessionManager()