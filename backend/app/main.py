import json
import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import AiRecord, Base, SessionLocal, SmsCode, Usage, User, Work, engine, get_db
from .schemas import AskRequest, ImportRequest, LoginRequest, RegisterRequest, ResetRequest, SmsRequest, WorkRequest
from .security import create_token, decode_token, hash_password, limiter, verify_password
from . import services


@asynccontextmanager
async def lifespan(_):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title='拙政观景 API', lifespan=lifespan)
# Development normally uses Vite's same-origin proxy; explicit origins also allow a local preview.
app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5174', 'http://localhost:5174', 'http://127.0.0.1:5173', 'http://localhost:5173'], allow_methods=['*'], allow_headers=['*'])
bearer = HTTPBearer(auto_error=False)


@app.middleware('http')
async def private_responses(request, call_next):
    size = request.headers.get('content-length', '')
    if size.isdigit() and int(size) > 100_000_000:
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': '上传内容过大'}, status_code=413)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    payload = decode_token(credentials.credentials) if credentials else None
    user = db.get(User, payload['sub']) if payload else None
    if not user or user.token_version != payload.get('tv', 0):
        raise HTTPException(401, '登录已过期，请重新登录')
    return user


def user_json(user):
    return {'id': user.id, 'phone': user.phone, 'nickname': user.nickname, 'created_at': user.created_at.isoformat()}


def auth_json(user):
    return {'access_token': create_token(user), 'token_type': 'bearer', 'expires_in': settings.token_seconds, 'user': user_json(user)}


@app.get('/health')
def health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'service': 'garden', 'ai_configured': bool(settings.ai_api_key), 'sms_provider': settings.sms_provider}


@app.post('/api/v1/auth/send-sms')
def send_sms(payload: SmsRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if payload.scene == 'register' and user:
        raise HTTPException(409, '手机号已注册')
    if payload.scene == 'reset_password' and not user:
        raise HTTPException(404, '手机号未注册')
    limiter.consume('sms-ip:' + (request.client.host if request.client else 'unknown'), 30, 3600)
    limiter.consume('sms-minute:' + payload.phone, 1, 60)
    limiter.consume('sms-day:' + payload.phone, 10, 86400)
    services.send_sms(payload.phone, payload.scene)
    db.merge(SmsCode(phone=payload.phone, scene=payload.scene, issued_at=int(time.time()), attempts=0))
    db.commit()
    return {'message': f'开发验证码：{settings.sms_dev_code}' if settings.sms_provider == 'local' else '验证码已发送', 'retry_after': 60, 'development': settings.sms_provider == 'local'}


def verify_sms(db, phone, code, scene):
    issue = db.get(SmsCode, phone)
    if not issue or issue.scene != scene or issue.issued_at < time.time() - 300:
        raise HTTPException(400, '验证码已失效或与当前操作不匹配，请重新获取')
    if issue.attempts >= 5:
        raise HTTPException(429, '验证码错误次数过多，请重新获取')
    if not services.check_sms(phone, code):
        db.execute(update(SmsCode).where(SmsCode.phone == phone).values(attempts=SmsCode.attempts + 1))
        db.commit()
        raise HTTPException(400, '验证码输入错误')
    # Consume the exact issue atomically, before accepting a registration/reset.
    deleted = db.execute(delete(SmsCode).where(SmsCode.phone == phone, SmsCode.scene == scene, SmsCode.issued_at == issue.issued_at))
    if deleted.rowcount != 1:
        db.rollback()
        raise HTTPException(400, '验证码已使用，请重新获取')


@app.post('/api/v1/auth/register', status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.phone == payload.phone)):
        raise HTTPException(409, '手机号已注册')
    verify_sms(db, payload.phone, payload.sms_code, 'register')
    user = User(phone=payload.phone, nickname=payload.nickname.strip() or '园林访客', password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '手机号已注册') from None
    return auth_json(user)


@app.post('/api/v1/auth/login')
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    limiter.consume('login-ip:' + (request.client.host if request.client else 'unknown'), 60, 900)
    key = 'login:' + payload.phone
    limiter.consume(key, 5, 900)
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, '手机号或密码错误')
    limiter.clear(key)
    return auth_json(user)


@app.post('/api/v1/auth/forgot-password')
def forgot_password(payload: ResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.phone == payload.phone))
    if not user:
        raise HTTPException(404, '手机号未注册')
    verify_sms(db, payload.phone, payload.sms_code, 'reset_password')
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    db.commit()
    return {'message': '密码已重置，请重新登录'}


@app.get('/api/v1/profile/me')
def profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    day = services.today()
    usage = db.scalar(select(Usage).where(Usage.user_id == user.id, Usage.day == day))
    used = usage.used if usage else 0
    return {**user_json(user), 'ai_daily_limit': settings.daily_limit, 'ai_used_today': used, 'ai_remaining': max(0, settings.daily_limit - used), 'ai_usage_day': day}


@app.get('/api/v1/profile/works')
def list_works(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [json.loads(row.payload) for row in db.scalars(select(Work).where(Work.user_id == user.id).order_by(Work.updated_at.desc()))]


def upsert_work(db, user_id, payload, *, only_new=False):
    row = db.scalar(select(Work).where(Work.user_id == user_id, Work.work_id == payload.id))
    if row and only_new:
        return False
    serialized = json.dumps(payload.model_dump(), ensure_ascii=False)
    if row:
        row.payload, row.updated_at = serialized, datetime.utcnow()
    else:
        db.add(Work(user_id=user_id, work_id=payload.id, payload=serialized))
    return True


@app.post('/api/v1/profile/works/import')
def import_works(payload: ImportRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    # Repeated imports preserve the cloud copy and keep the browser original untouched.
    imported = 0
    for item in payload.works:
        imported += int(upsert_work(db, user.id, item, only_new=True))
        db.flush()
    db.commit()
    return {'imported': imported, 'skipped': len(payload.works) - imported, 'works': list_works(user, db)}


@app.post('/api/v1/profile/works')
def save_work(payload: WorkRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    upsert_work(db, user.id, payload)
    db.commit()
    return payload.model_dump()


@app.put('/api/v1/profile/works/{work_id}')
def update_work(work_id: str, payload: WorkRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if work_id != payload.id:
        raise HTTPException(400, '作品编号不一致')
    return save_work(payload, user, db)


@app.get('/api/v1/profile/works/{work_id}')
def get_work(work_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Work).where(Work.user_id == user.id, Work.work_id == work_id))
    if not row:
        raise HTTPException(404, '作品不存在')
    return json.loads(row.payload)


@app.delete('/api/v1/profile/works/{work_id}')
def remove_work(work_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    result = db.execute(delete(Work).where(Work.user_id == user.id, Work.work_id == work_id))
    db.commit()
    if not result.rowcount:
        raise HTTPException(404, '作品不存在')
    return {'message': '作品已删除'}


@app.get('/api/v1/content/ask/bootstrap')
def bootstrap():
    return {'prompts': services.PROMPTS, 'followups': ['给我一个现场观察的小练习', '带我去相关页面'], 'welcome_message': '我是梅梅。你可以问我如何使用拙政观景，也可以一起聊聊拙政园与五种造景手法。'}


@app.post('/api/v1/content/ask')
def ask(payload: AskRequest, user: User = Depends(current_user)):
    day = services.charge(user.id)
    try:
        answer = ''.join(services.stream_ai(payload))
        if not answer.strip():
            raise ValueError('empty response')
    except Exception as error:
        services.refund(user.id, day)
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(502, '梅梅暂时没有收到回答，请稍后重试；本次未扣额度') from None
    services.save_record(user.id, payload.question, answer)
    return {'answer': answer, 'sources': 'AI 回答基于本站园林资料整理，重要事实请核对官方来源。'}


@app.post('/api/v1/content/ask/stream')
def ask_stream(payload: AskRequest, user: User = Depends(current_user)):
    day = services.charge(user.id)
    stream = None
    try:
        stream = iter(services.stream_ai(payload))
        first = next(stream)
    except Exception as error:
        services.refund(user.id, day)
        getattr(stream, 'close', lambda: None)()
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(502, '梅梅暂时没有收到回答，请稍后重试；本次未扣额度') from None
    user_id = user.id

    def generate():
        chunks = []
        status = 'interrupted'
        try:
            chunks.append(first)
            yield first
            for chunk in stream:
                chunks.append(chunk)
                yield chunk
            status = 'complete'
        finally:
            getattr(stream, 'close', lambda: None)()
            if chunks:
                services.save_record(user_id, payload.question, ''.join(chunks), status)
            else:
                services.refund(user_id, day)
    return StreamingResponse(generate(), media_type='text/plain; charset=utf-8', headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-store'})


@app.get('/api/v1/profile/ai-records')
def records(user: User = Depends(current_user), db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=100), before: int | None = Query(None, ge=1)):
    query = select(AiRecord).where(AiRecord.user_id == user.id)
    if before is not None:
        query = query.where(AiRecord.id < before)
    rows = db.scalars(query.order_by(AiRecord.id.desc()).limit(limit))
    return [{'id': row.id, 'question': row.question, 'answer': row.answer, 'status': row.status, 'created_at': row.created_at.isoformat()} for row in rows]


@app.delete('/api/v1/profile/ai-records')
def clear_records(user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(AiRecord).where(AiRecord.user_id == user.id))
    db.commit()
    return {'message': '问答记录已清空；每日额度不变'}

