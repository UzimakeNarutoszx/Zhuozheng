import base64
import io
import math
from typing import Literal
from PIL import Image
from pydantic import BaseModel, Field, field_validator


class Phone(BaseModel):
    phone: str = Field(pattern=r'^1[3-9]\d{9}$')


class SmsRequest(Phone):
    scene: Literal['register', 'reset_password'] = 'register'


class LoginRequest(Phone):
    password: str = Field(min_length=6, max_length=72)


class RegisterRequest(LoginRequest):
    nickname: str = Field(min_length=1, max_length=40)
    sms_code: str = Field(pattern=r'^\d{6}$')


class ResetRequest(Phone):
    new_password: str = Field(min_length=6, max_length=72)
    sms_code: str = Field(pattern=r'^\d{6}$')


class WorkRequest(BaseModel):
    id: str = Field(min_length=1, max_length=100, pattern=r'^[\w-]+$')
    title: str = Field(default='未命名取景', max_length=120)
    note: str = Field(default='', max_length=2000)
    methodId: Literal['frame', 'borrow', 'opposition', 'leak', 'screen'] = 'frame'
    frameId: Literal['round', 'square', 'fan', 'moon', 'open'] = 'round'
    keepCanvasBorder: bool = True
    scale: float = Field(default=1, ge=0.1, le=10, allow_inf_nan=False)
    offset: dict[str, float] = Field(default_factory=lambda: {'x': 0, 'y': 0})
    createdAt: int = Field(default=0, ge=0)
    imageDataUrl: str = Field(min_length=1, max_length=4_000_000)
    sourceImageDataUrl: str = Field(default='', max_length=4_000_000)

    @field_validator('offset')
    @classmethod
    def valid_offset(cls, value):
        if set(value) != {'x', 'y'} or any(not math.isfinite(v) or abs(v) > 1_000_000 for v in value.values()):
            raise ValueError('invalid offset')
        return value

    @field_validator('imageDataUrl', 'sourceImageDataUrl')
    @classmethod
    def valid_image(cls, value):
        if not value:
            return value
        header, sep, data = value.partition(',')
        if header not in {'data:image/jpeg;base64', 'data:image/png;base64', 'data:image/webp;base64'} or not sep:
            raise ValueError('only JPEG, PNG and WebP data URLs are supported')
        try:
            raw = base64.b64decode(data, validate=True)
            with Image.open(io.BytesIO(raw)) as image:
                if image.width * image.height > 20_000_000:
                    raise ValueError('image too large')
                image.verify()
        except Exception:
            raise ValueError('invalid image data') from None
        return value


class ImportRequest(BaseModel):
    works: list[WorkRequest] = Field(max_length=24)


class HistoryMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=4000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)
    method_id: Literal['frame', 'borrow', 'opposition', 'leak', 'screen'] | None = None

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('问题不能为空')
        return value.strip()

