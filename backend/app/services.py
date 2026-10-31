import json
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .config import settings
from .db import AiRecord, SessionLocal, Usage

PROMPTS = ['这个网站可以怎么玩？', '框景和借景有什么区别？', '第一次去拙政园应该观察什么？', '如何用创作页做一幅园林作品？']
SYSTEM = '''你是“梅梅”，拙政观景的园林研学向导。语气亲切、清楚，优先解答网站使用和拙政园造景问题。
本站功能：游园页提供地图观察；手法页介绍框景、借景、对景、漏景、障景；创作页可上传照片、选窗框、拖动缩放、保存与导出；我的页包含本地及云端作品和关于/图片来源；本地作品需用户主动导入云端。登录后才能AI提问，每日20问。
框景是用门窗等边界组织画面；借景是将园外景物纳入园内构图；对景让空间两端景物相互回应；漏景通过花墙漏窗透出局部；障景先遮挡后展开。具体一景可以同时使用多种手法。
拙政园位于苏州，是苏州古典园林世界遗产的组成部分。根据已有内容提供观察建议，不编造史料、游客经历、来源或实时票务信息；日期、门票和开放安排请引导核对园方官方信息。
资料可参考 UNESCO https://whc.unesco.org/en/list/813/ 、计成《园冶》和本站关于页。不要虚构引文。对于缺乏把握的事实明确说明需核验；回答与园林无关的问题时简短引导回园林与本站功能。'''


def today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()


def charge(user_id):
    day = today()
    with SessionLocal() as db:
        if not db.scalar(select(Usage).where(Usage.user_id == user_id, Usage.day == day)):
            db.add(Usage(user_id=user_id, day=day, used=0))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        result = db.execute(update(Usage).where(Usage.user_id == user_id, Usage.day == day, Usage.used < settings.daily_limit).values(used=Usage.used + 1))
        db.commit()
        if result.rowcount != 1:
            raise HTTPException(429, f'今日 {settings.daily_limit} 次提问额度已用完，请明天再来')
    return day


def refund(user_id, day):
    with SessionLocal() as db:
        db.execute(update(Usage).where(Usage.user_id == user_id, Usage.day == day, Usage.used > 0).values(used=Usage.used - 1))
        db.commit()


def save_record(user_id, question, answer, status='complete'):
    with SessionLocal() as db:
        db.add(AiRecord(user_id=user_id, question=question, answer=answer, status=status))
        db.commit()


def messages(payload):
    history = [{'role': item.role, 'content': item.content} for item in payload.history]
    return [{'role': 'system', 'content': SYSTEM}, *history, {'role': 'user', 'content': payload.question}]


def stream_ai(payload):
    if not settings.ai_api_key:
        raise HTTPException(503, '梅梅问答尚未配置 AI 服务，请联系站点维护者')
    with httpx.Client(timeout=httpx.Timeout(settings.ai_timeout, connect=15)) as client:
        with client.stream('POST', settings.ai_api_base_url.rstrip('/') + '/chat/completions', headers={'Authorization': f'Bearer {settings.ai_api_key}'}, json={'model': settings.ai_model, 'messages': messages(payload), 'stream': True, 'max_tokens': 2400}) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith('data:'):
                    continue
                data = line[5:].strip()
                if data == '[DONE]':
                    return
                if not data:
                    continue
                chunk = json.loads(data)
                if chunk.get('error'):
                    raise RuntimeError('AI upstream error')
                text = (chunk.get('choices') or [{}])[0].get('delta', {}).get('content')
                if text:
                    yield text
            # A clean HTTP close without the upstream terminator is still an
            # incomplete answer. Propagate the disconnect to the fetch reader.
            raise RuntimeError('AI stream ended before completion')


def sms_client():
    if settings.sms_provider != 'aliyun' or not all((settings.sms_access_key_id, settings.sms_access_key_secret, settings.sms_sign_name)):
        raise HTTPException(503, '短信服务未配置，请联系站点维护者')
    from alibabacloud_dypnsapi20170525.client import Client
    from alibabacloud_tea_openapi.models import Config
    return Client(Config(access_key_id=settings.sms_access_key_id, access_key_secret=settings.sms_access_key_secret, endpoint=settings.sms_endpoint, connect_timeout=10000, read_timeout=15000))


def local_sms():
    if settings.sms_provider != 'local':
        return False
    if settings.environment not in {'development', 'test'}:
        raise HTTPException(503, '开发短信模式不可用于生产环境')
    return True


def send_sms(phone, scene):
    templates = {'register': '100001', 'reset_password': '100003'}
    if scene not in templates:
        raise HTTPException(400, '短信验证码场景不正确')
    if local_sms():
        return
    try:
        from alibabacloud_dypnsapi20170525.models import SendSmsVerifyCodeRequest
        # The provider generates and verifies a random code; never return it to the caller.
        response = sms_client().send_sms_verify_code(SendSmsVerifyCodeRequest(country_code='86', phone_number=phone, sign_name=settings.sms_sign_name, template_code=templates[scene], template_param='{"code":"##code##","min":"5"}', code_length=6, code_type=1, valid_time=300, interval=60))
        if not response.body.success or response.body.code != 'OK':
            raise RuntimeError('provider rejected request')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, '短信发送失败，请稍后重试') from None


def check_sms(phone, code):
    if local_sms():
        import hmac
        return hmac.compare_digest(code, settings.sms_dev_code)
    try:
        from alibabacloud_dypnsapi20170525.models import CheckSmsVerifyCodeRequest
        response = sms_client().check_sms_verify_code(CheckSmsVerifyCodeRequest(country_code='86', phone_number=phone, verify_code=code))
        if response.body.code != 'OK':
            raise RuntimeError('provider rejected verification')
        return response.body.code == 'OK' and response.body.model.verify_result == 'PASS'
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, '短信验证失败，请稍后重试') from None

