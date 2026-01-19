"""
인증 설정 파일
"""
import hashlib
import secrets
import os
from datetime import datetime, timedelta

# 접속 비밀번호 설정 (SHA256 해시값으로 저장)
# Streamlit Cloud에서는 Secrets에서, 로컬에서는 환경변수에서 가져옴
import os

# 1. Render 설정(Environment)에서 비밀번호 가져오기
def get_password():
    # Render에 설정한 'MY_REAL_PASSWORD'를 가져오고, 없으면 'noma'를 사용
    return os.environ.get("MY_REAL_PASSWORD", "noma")

# 2. 실제 인증에 사용할 변수
ACCESS_PASSWORD = get_password()

# 3. 로그인 버튼을 누를 때 실행되는 비밀번호 확인 함수
def verify_password(password):
    # 입력한 비번과 서버 설정 비번이 일치하는지 확인
    return password == ACCESS_PASSWORD

# 토큰 유효기간 (일)
TOKEN_VALIDITY_DAYS = 7


def generate_token():
    """무작위 토큰 생성"""
    return secrets.token_urlsafe(32)


def verify_password(password: str) -> bool:
    """비밀번호 검증"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return password_hash == ACCESS_PASSWORD_HASH


def is_token_valid(token_data: dict) -> bool:
    """토큰 유효성 검사"""
    if not token_data:
        return False

    token = token_data.get('token')
    expiry = token_data.get('expiry')

    if not token or not expiry:
        return False

    # 만료 시간 확인
    try:
        expiry_date = datetime.fromisoformat(expiry)
        return datetime.now() < expiry_date
    except BaseException:
        return False


def create_token_data(token: str) -> dict:
    """토큰 데이터 생성"""
    expiry = datetime.now() + timedelta(days=TOKEN_VALIDITY_DAYS)
    return {
        'token': token,
        'expiry': expiry.isoformat(),
        'created': datetime.now().isoformat()
    }
