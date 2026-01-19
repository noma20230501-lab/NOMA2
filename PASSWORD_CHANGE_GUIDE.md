# 비밀번호 변경 가이드

## 현재 기본 비밀번호
```
admin123
```

## 비밀번호 변경 방법

### 1단계: auth_config.py 파일 열기

### 2단계: 새 비밀번호의 해시값 생성

Python을 실행하고 다음 코드를 입력하세요:

```python
import hashlib

# 새로운 비밀번호 입력 (예: "mypassword123")
new_password = "mypassword123"

# SHA256 해시 생성
password_hash = hashlib.sha256(new_password.encode()).hexdigest()
print(password_hash)
```

### 3단계: auth_config.py 파일 수정

`ACCESS_PASSWORD_HASH` 값을 생성된 해시값으로 변경:

```python
# 변경 전
ACCESS_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# 변경 후 (예시)
ACCESS_PASSWORD_HASH = "새로_생성한_해시값_여기에_붙여넣기"
```

### 4단계: 저장 후 재시작

파일을 저장하고 Streamlit 앱을 재시작하세요.

---

## 토큰 유효기간 변경

`auth_config.py` 파일에서 다음 값을 수정:

```python
# 7일 → 원하는 일수로 변경
TOKEN_VALIDITY_DAYS = 7
```
