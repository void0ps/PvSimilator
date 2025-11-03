from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# 用户相关模式

class UserBase(BaseModel):
    username: str = Field(..., description="用户名", min_length=3, max_length=50)
    email: EmailStr = Field(..., description="邮箱")
    full_name: Optional[str] = Field(None, description="全名", max_length=100)
    company: Optional[str] = Field(None, description="公司名称", max_length=200)
    phone: Optional[str] = Field(None, description="电话号码", max_length=20)
    user_type: str = Field("user", description="用户类型: admin, user, guest")
    is_active: bool = Field(True, description="是否激活")

class UserCreate(UserBase):
    password: str = Field(..., description="密码", min_length=6)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    user_type: Optional[str] = Field(None, description="用户类型: admin, user, guest")
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

# 认证相关模式

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None

class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., description="新密码", min_length=6)

# 用户统计模式

class UserStats(BaseModel):
    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    admin_users: int = Field(..., description="管理员用户数")
    total_systems: int = Field(..., description="总系统数")
    total_simulations: int = Field(..., description="总模拟数")
    
    class Config:
        from_attributes = True