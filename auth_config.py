"""
인증 설정 파일
"""
import hashlib
import secrets
import os
from datetime import datetime, timedelta

# 접속 비밀번호 설정 (SHA256 해시값으로 저장)
# Streamlit Cloud에서는 Secrets에서, 로컬에서는 환경변수에서 가져옴
try:
    import streamlit as st
    # Streamlit Cloud의 Secrets 사용
    ACCESS_PASSWORD_HASH = st.secrets.get(
        "ACCESS_PASSWORD_HASH",
        "248d7b40f79c4f8eee8a89d9b7e3d2d11d34217f2867cca567fa9c6e1609bf38")
except BaseException:
    # 로컬 환경: 기본값 사용 (noma123)
    ACCESS_PASSWORD_HASH = os.getenv(
        "ACCESS_PASSWORD_HASH",
        "248d7b40f79c4f8eee8a89d9b7e3d2d11d34217f2867cca567fa9c6e1609bf38")

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
