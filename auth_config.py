import os
import secrets
from datetime import datetime, timedelta

# 1. Render 설정에서 비밀번호 가져오기
def get_password():
    # Render의 'MY_REAL_PASSWORD'를 가져오고, 없으면 기본값 'noma' 사용
    return os.environ.get("MY_REAL_PASSWORD", "noma")

ACCESS_PASSWORD = get_password()

# 2. 로그인 버튼 눌렀을 때 확인하는 함수
def verify_password(password):
    return password == ACCESS_PASSWORD

# 3. 토큰 설정 (로그인 유지용)
TOKEN_VALIDITY_DAYS = 7

def generate_token():
    return secrets.token_urlsafe(32)

def create_token_data(token):
    return {
        "token": token,
        "expiry": (datetime.now() + timedelta(days=TOKEN_VALIDITY_DAYS)).isoformat(),
        "created": datetime.now().isoformat()
    }

def is_token_valid(token_data):
    if not token_data or "expiry" not in token_data:
        return False
    try:
        expiry = datetime.fromisoformat(token_data["expiry"])
        return datetime.now() < expiry
    except:
        return False