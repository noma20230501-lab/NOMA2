# -*- coding: utf-8 -*-
"""
NOMA 시스템 설정 파일
API 키 등 공통 설정을 여기서 관리합니다.
키를 변경할 때는 이 파일 하나만 수정하면 됩니다.
"""
import os

# 국토교통부 건축HUB 건축물대장 API 키 (공공데이터포털에서 발급)
# Render 등 배포 환경에서는 환경변수 BUILDING_API_KEY를 설정하세요.
# 로컬 환경에서는 아래 기본값을 그대로 사용합니다.
BUILDING_API_KEY = os.environ.get(
    "BUILDING_API_KEY",
    "770b632a7abe47d5adad542d8b29350aceb52a0d82009f9acbef29101daa8a81"
)
