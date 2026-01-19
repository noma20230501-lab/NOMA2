import hashlib

# 여기에 원하는 비밀번호 입력
password = "noma123"

# SHA256 해시 생성
hash_value = hashlib.sha256(password.encode()).hexdigest()

print("=" * 60)
print(f"비밀번호: {password}")
print(f"해시값: {hash_value}")
print("=" * 60)

input("엔터를 누르면 종료됩니다...")
