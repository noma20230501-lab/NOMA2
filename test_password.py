import hashlib

password = "noma"
password_hash = hashlib.sha256(password.encode()).hexdigest()

print(f"비밀번호: {password}")
print(f"해시값: {password_hash}")
print()

# auth_config.py의 해시값과 비교
stored_hash = "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"
print(f"저장된 해시: {stored_hash}")
print(f"일치 여부: {password_hash == stored_hash}")
