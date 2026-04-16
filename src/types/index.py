from typing import List, Dict, Any, Optional

# 定义事件类型
class Event:
    def __init__(self, id: int, name: str, description: str, date: str, location: str):
        self.id = id
        self.name = name
        self.description = description
        self.date = date
        self.location = location

# 定义用户类型
class User:
    def __init__(self, id: int, username: str, email: str, password: str):
        self.id = id
        self.username = username
        self.email = email
        self.password = password

# 定义响应类型
class Response:
    def __init__(self, success: bool, message: str, data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data if data is not None else {}

# 定义类型别名
EventList = List[Event]
UserList = List[User]