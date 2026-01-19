@echo off
python -c "import hashlib; pw='noma123'; print('='*60); print(f'비밀번호: {pw}'); print(f'해시값: {hashlib.sha256(pw.encode()).hexdigest()}'); print('='*60)"
pause
