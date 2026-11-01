import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)


class Settings:
    environment = os.getenv('ENVIRONMENT', 'development')
    database_url = os.getenv('DATABASE_URL', f'sqlite:///{DATA / "garden.db"}')
    secret_key = os.getenv('SECRET_KEY', '')
    token_seconds = 7 * 24 * 3600
    sms_provider = os.getenv('SMS_PROVIDER', 'aliyun')
    sms_dev_code = os.getenv('SMS_DEV_CODE', '123456')
    sms_access_key_id = os.getenv('ALIYUN_DYPNS_ACCESS_KEY_ID', '')
    sms_access_key_secret = os.getenv('ALIYUN_DYPNS_ACCESS_KEY_SECRET', '')
    sms_endpoint = os.getenv('ALIYUN_DYPNS_ENDPOINT', 'dypnsapi.aliyuncs.com')
    sms_sign_name = os.getenv('ALIYUN_DYPNS_SIGN_NAME', '')
    ai_api_key = os.getenv('AI_API_KEY', '')
    ai_api_base_url = os.getenv('AI_API_BASE_URL', 'https://api.aicodewith.com/v1')
    ai_model = os.getenv('AI_MODEL', 'deepseek-flash')
    ai_timeout = float(os.getenv('AI_TIMEOUT_SECONDS', '180'))
    daily_limit = int(os.getenv('AI_DAILY_QUESTION_LIMIT', '20'))
    admin_phones = {item.strip() for item in os.getenv('ADMIN_PHONES', '').split(',') if item.strip()}
    media_dir = Path(os.getenv('MEDIA_DIR') or DATA / 'media')
    # Comments containing these words wait for review; extend locally via SENSITIVE_WORDS.
    sensitive_words = {'赌博', '色情', '代开发票', '加微信', '刷单', '博彩', *(item.strip() for item in os.getenv('SENSITIVE_WORDS', '').split(',') if item.strip())}


settings = Settings()
if not settings.secret_key:
    if settings.environment not in {'development', 'test'}:
        raise RuntimeError('SECRET_KEY must be configured')
    # Private local secret survives restarts; it is never a shared source default.
    secret_path = DATA / '.secret'
    if not secret_path.exists():
        secret_path.write_text(secrets.token_urlsafe(48))
        secret_path.chmod(0o600)
    settings.secret_key = secret_path.read_text().strip()
if settings.environment not in {'development', 'test'} and settings.sms_provider == 'local':
    raise RuntimeError('Local SMS is only available in development or test')

