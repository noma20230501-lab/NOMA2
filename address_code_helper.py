"""
주소 코드 검색 도우미
시군구코드와 법정동코드를 찾는 데 도움을 줍니다.
"""
import re

# 시군구코드 매핑 (서울특별시, 대구광역시 등)
SIGUNGU_CODES = {
    # 서울특별시
    '종로구': '11110',
    '중구': '11140',
    '용산구': '11170',
    '성동구': '11200',
    '광진구': '11215',
    '동대문구': '11230',
    '중랑구': '11260',
    '성북구': '11290',
    '강북구': '11305',
    '도봉구': '11320',
    '노원구': '11350',
    '은평구': '11380',
    '서대문구': '11410',
    '마포구': '11440',
    '양천구': '11470',
    '강서구': '11500',
    '구로구': '11530',
    '금천구': '11545',
    '영등포구': '11560',
    '동작구': '11590',
    '관악구': '11620',
    '서초구': '11650',
    '강남구': '11680',
    '송파구': '11710',
    '강동구': '11740',
    # 대구광역시
    '대구 중구': '27110',
    '대구 동구': '27140',
    '대구 서구': '27170',
    '대구 남구': '27200',
    '대구 북구': '27230',
    '대구 수성구': '27260',
    '대구 달서구': '27290',
    '대구 달성군': '27710',
}

# 법정동코드 매핑
BJDONG_CODES = {
    # 강남구
    '강남구': {
        '역삼동': '11680',
        '개포동': '10300',
        '청담동': '10600',
        '삼성동': '10700',
        '대치동': '10800',
        '논현동': '10100',
        '압구정동': '10500',
        '신사동': '10200',
        '세곡동': '10900',
        '도곡동': '10400',
    },
    # 대구 중구
    '대구 중구': {
        '동인동1가': '10100',
        '동인동2가': '10200',
        '동인동3가': '10300',
        '동인동4가': '10400',
        '삼덕동1가': '10500',
        '삼덕동2가': '10600',
        '삼덕동3가': '10700',
        '삼덕동': '10700',  # 기본값으로 삼덕동3가 사용
        '삼덕': '10700',  # 부분 매칭용
        '봉산동': '10800',
        '장관동': '10900',
        '상서동': '11000',
        '수동': '11100',
        '덕산동': '11200',
        '종로1가': '11300',
        '종로2가': '11400',
        '사일동': '11500',
        '동일동': '11600',
        '남일동': '11700',
        '전동': '11800',
        '동성로3가': '11900',
        '동문동': '12000',
        '문화동': '12100',
        '공평동': '12200',
        '동성로2가': '12300',
        '태평로1가': '12400',
        '교동': '12500',
        '용덕동': '12600',
        '상덕동': '12700',
        '완전동': '12800',
        '도원동': '12900',
        '수창동': '13000',
        '태평로3가': '13100',
        '인교동': '13200',
        '서야동': '13300',
        '서성로1가': '13400',
        '시장북로': '13500',
        '하서동': '13600',
        '남성로': '13700',
        '계산동1가': '13800',
        '계산동2가': '13900',
        '동산동': '14000',
        '서문로2가': '14100',
        '서성로2가': '14200',
        '포정동': '14300',
        '서문로1가': '14400',
        '서내동': '14500',
        '북성로2가': '14600',
        '대안동': '14700',
        '동성로1가': '14800',
        '태평로2가': '14900',
        '북성로1가': '15000',
        '화전동': '15100',
        '향촌동': '15200',
        '북내동': '15300',
        '대신동': '15400',
        '달성동': '15500',
        '남산동': '15600',
        '대봉동': '15700',
    },
    # 대구 동구
    '대구 동구': {
        '신암동': '10100',
        '신천동': '10200',
        '효목동': '10300',
        '평광동': '10400',
        '봉무동': '10500',
        '불로동': '10600',
        '도동': '10700',
        '지저동': '10800',
        '입석동': '10900',
        '검사동': '11000',
        '방촌동': '11100',
        '둔산동': '11200',
        '부동': '11300',
        '신평동': '11400',
        '서호동': '11500',
        '동호동': '11600',
        '신기동': '11700',
        '율하동': '11800',
        '용계동': '11900',
        '율암동': '12000',
        '상매동': '12100',
        '매여동': '12200',
        '각산동': '12300',
        '신서동': '12400',
        '동내동': '12500',
        '괴전동': '12600',
        '금강동': '12700',
        '대림동': '12800',
        '사복동': '12900',
        '숙천동': '13000',
        '내곡동': '13100',
        '능성동': '13200',
        '진인동': '13300',
        '도학동': '13400',
        '백안동': '13500',
        '미곡동': '13600',
        '용수동': '13700',
        '신무동': '13800',
        '미대동': '13900',
        '내동': '14000',
        '신용동': '14100',
        '중대동': '14200',
        '송정동': '14300',
        '덕곡동': '14400',
        '지묘동': '14500',
    },
    # 대구 서구
    '대구 서구': {
        '내당동': '10100',
        '비산동': '10200',
        '평리동': '10300',
        '상리동': '10400',
        '중리동': '10500',
        '이현동': '10600',
        '원대동1가': '10700',
        '원대동2가': '10800',
        '원대동3가': '10900',
    },
    # 대구 남구
    '대구 남구': {
        '이천동': '10100',
        '봉덕동': '10200',
        '대명동': '10300',
    },
    # 대구 북구
    '대구 북구': {
        '칠성동1가': '10100',
        '칠성동2가': '10200',
        '고성동1가': '10300',
        '고성동2가': '10400',
        '고성동3가': '10500',
        '침산동': '10600',
        '노원동1가': '10700',
        '노원동2가': '10800',
        '노원동3가': '10900',
        '대현동': '11000',
        '산격동': '11100',
        '복현동': '11200',
        '검단동': '11300',
        '동변동': '11400',
        '서변동': '11500',
        '조야동': '11600',
        '노곡동': '11700',
        '읍내동': '11800',
        '동호동': '11900',
        '학정동': '12000',
        '도남동': '12100',
        '국우동': '12200',
        '구암동': '12300',
        '동천동': '12400',
        '관음동': '12500',
        '태전동': '12600',
        '매천동': '12700',
        '팔달동': '12800',
        '금호동': '12900',
        '사수동': '13000',
        '연경동': '13100',
    },
    # 대구 수성구
    '대구 수성구': {
        '범어동': '10100',
        '만촌동': '10200',
        '수성동1가': '10300',
        '수성동2가': '10400',
        '수성동3가': '10500',
        '수성동4가': '10600',
        '수성동': '10400',  # 기본값으로 수성동2가 사용
        '수성': '10400',  # 부분 매칭용
        '황금동': '10700',
        '중동': '10800',
        '상동': '10900',
        '파동': '11000',
        '두산동': '11100',
        '지산동': '11200',
        '범물동': '11300',
        '시지동': '11400',
        '매호동': '11500',
        '성동': '11600',
        '사월동': '11700',
        '신매동': '11800',
        '욱수동': '11900',
        '노변동': '12000',
        '삼덕동': '12200',
        '연호동': '12300',
        '이천동': '12400',
        '고모동': '12500',
        '가천동': '12600',
        '대흥동': '12700',
    },
    # 대구 달서구
    '대구 달서구': {
        '성당동': '10100',
        '두류동': '10200',
        '파호동': '10400',
        '호림동': '10500',
        '갈산동': '10600',
        '신당동': '10700',
        '이곡동': '10800',
        '장동': '10900',
        '장기동': '11000',
        '용산동': '11100',
        '죽전동': '11200',
        '감삼동': '11300',
        '본리동': '11400',
        '상인동': '11500',
        '도원동': '11600',
        '진천동': '11700',
        '유천동': '11800',
        '대천동': '11900',
        '월성동': '12000',
        '월암동': '12100',
        '송현동': '12200',
        '대곡동': '12300',
        '본동': '12400',
        '호산동': '12500',
    },
}


def find_sigungu_by_dong(dong_name):
    """동 이름으로 시군구 찾기 (역검색)"""
    """동 이름이 어떤 시군구에 속하는지 찾기"""
    for sigungu_name, dong_dict in BJDONG_CODES.items():
        # 더 구체적인 매칭부터 시도 (길이순 정렬)
        for dong_key, code in sorted(
            dong_dict.items(), key=lambda x: len(
                x[0]), reverse=True):
            if dong_key in dong_name or dong_name in dong_key:
                return SIGUNGU_CODES.get(sigungu_name), sigungu_name
    return None, None


def find_sigungu_code(address):
    """주소에서 시군구코드 찾기"""
    # 대구는 특별 처리 (대구 중구 형식)
    if '대구' in address:
        if '중구' in address:
            return '27110', '대구 중구'
        elif '동구' in address:
            return '27140', '대구 동구'
        elif '서구' in address:
            return '27170', '대구 서구'
        elif '남구' in address:
            return '27200', '대구 남구'
        elif '북구' in address:
            return '27230', '대구 북구'
        elif '수성구' in address:
            return '27260', '대구 수성구'
        elif '달서구' in address:
            return '27290', '대구 달서구'
        elif '달성군' in address:
            return '27710', '대구 달성군'

    # "대구"가 없지만 구 이름만 있는 경우 (예: "중구 봉산동")
    # 대구의 구 이름들
    daegu_gu_names = {
        '중구': ('27110', '대구 중구'),
        '동구': ('27140', '대구 동구'),
        '서구': ('27170', '대구 서구'),
        '남구': ('27200', '대구 남구'),
        '북구': ('27230', '대구 북구'),
        '수성구': ('27260', '대구 수성구'),
        '달서구': ('27290', '대구 달서구'),
        '달성군': ('27710', '대구 달성군'),
    }

    # 구 이름만 있는 경우 (서울 중구와 구분하기 위해 동 이름으로 검증)
    # 대구만 작업하므로, "서울"이 없으면 대구로 인식
    for gu_name, (code, full_name) in daegu_gu_names.items():
        if gu_name in address and '서울' not in address:
            # 동 이름으로 역검색하여 실제로 대구에 속하는지 확인
            # 주소에서 동 이름 추출 시도 (동으로 끝나거나, 숫자+가로 끝나는 패턴 포함)
            # 예: "삼덕동3가", "삼덕동", "종로2가", "종로1가" 등
            dong_match = re.search(
                r'([가-힣]+동[0-9가]*|[가-힣]+동|[가-힣]+\d+가)', address)
            if dong_match:
                dong_name = dong_match.group(1)
                # 해당 구에 동이 있는지 확인
                if full_name in BJDONG_CODES:
                    for dong_key in BJDONG_CODES[full_name].keys():
                        if dong_name in dong_key or dong_key in dong_name:
                            return code, full_name
            # 동 이름을 찾지 못했거나 검증에 실패했지만 "서울"이 없고 대구의 구 이름이면 대구로 인식
            # (대구만 작업하므로)
            if '서울' not in address:
                return code, full_name

    # 서울 등 다른 지역
    for name, code in SIGUNGU_CODES.items():
        if name in address:
            return code, name
    return None, None


def find_bjdong_code(address, sigungu_name):
    """주소에서 법정동코드 찾기"""
    if sigungu_name in BJDONG_CODES:
        bjdong_dict = BJDONG_CODES[sigungu_name]

        # 1. 먼저 더 구체적인 매칭 시도 (예: 삼덕동3가, 종로2가)
        # 길이순으로 정렬하여 더 긴 매칭이 먼저 시도되도록
        for name, code in sorted(
            bjdong_dict.items(), key=lambda x: len(
                x[0]), reverse=True):
            # 정확히 일치하거나 포함 관계 확인
            # "수성구"에 "수성"이 포함되는 것을 방지하기 위해 단어 경계 확인
            if name in address:
                # "수성"이 "수성구"에 포함되는 경우 제외
                if name == '수성' and '수성구' in address:
                    continue
                # "수성동"이 "수성구"에 포함되는 경우도 확인 필요
                if name == '수성동' and '수성구' in address and '수성동' not in address:
                    continue
                return code, name
            # 공백 제거 후 비교 (예: "종로2가"와 " 종로2가 "를 매칭)
            if name.replace(' ', '') in address.replace(' ', ''):
                # "수성"이 "수성구"에 포함되는 경우 제외
                if name == '수성' and '수성구' in address:
                    continue
                if name == '수성동' and '수성구' in address and '수성동' not in address:
                    continue
                return code, name

        # 2. 부분 매칭 시도 (예: "삼덕"으로 "삼덕동" 찾기)
        # 하지만 "수성" 같은 단일 문자 매칭은 나중에 (더 긴 것부터)
        for name, code in sorted(
            bjdong_dict.items(), key=lambda x: len(
                x[0]), reverse=True):
            # "수성"은 "수성구"에 포함되므로 제외
            if name == '수성' and '수성구' in address:
                continue
            if name == '수성동' and '수성구' in address and '수성동' not in address:
                continue

            if name in address or any(
                    part in address for part in name.split('동')):
                return code, name
            # 공백 제거 후 부분 매칭
            name_clean = name.replace(' ', '')
            address_clean = address.replace(' ', '')
            if name_clean in address_clean:
                return code, name
    return None, None


def parse_address(address):
    """주소를 파싱하여 코드와 번지 추출"""

    # 번지 추출 (다양한 형식 지원)
    # "12번지", "147-6", "147번지", "122,", "122.", "122 " 등
    bun = None
    ji = None

    # "147-6" 형식 처리 (번호-지번호)
    dash_match = re.search(r'(\d+)\s*-\s*(\d+)', address)
    if dash_match:
        bun = dash_match.group(1).zfill(4)
        ji = dash_match.group(2).zfill(4)
    else:
        # "12번지" 형식 처리
        bun_match = re.search(r'(\d+)\s*번지', address)
        if bun_match:
            bun = bun_match.group(1).zfill(4)
        else:
            # 단독 번호 추출 (쉼표, 마침표, 띄어쓰기 등 구분자 포함)
            # 예: "122,", "122.", "122 ", "122" 등
            bun_match = re.search(r'\s+(\d+)(?:\s*[,.\s]|$)', address)
            if bun_match:
                bun = bun_match.group(1).zfill(4)
            else:
                # 마지막 숫자 추출 시도 (구분자 없이)
                bun_match = re.search(r'\s+(\d+)(?:\s|$)', address)
                if bun_match:
                    bun = bun_match.group(1).zfill(4)

    # 시군구 코드 찾기
    sigungu_code, sigungu_name = find_sigungu_code(address)

    # 시군구를 찾지 못했지만 동 이름이 있는 경우, 동 이름으로 역검색
    if not sigungu_name:
        # 주소에서 동 이름 추출 시도 (동으로 끝나거나, 숫자+가로 끝나는 패턴 포함)
        dong_match = re.search(r'([가-힣]+동[0-9가]*|[가-힣]+동|[가-힣]+\d+가)', address)
        if dong_match:
            dong_name = dong_match.group(1)
            sigungu_code, sigungu_name = find_sigungu_by_dong(dong_name)

    # 법정동 코드 찾기
    bjdong_code, bjdong_name = None, None
    if sigungu_name:
        bjdong_code, bjdong_name = find_bjdong_code(address, sigungu_name)
    elif not sigungu_name:
        # 시군구를 찾지 못했지만 동 이름이 있는 경우, 모든 구에서 검색
        dong_match = re.search(r'([가-힣]+동[0-9가]*|[가-힣]+동|[가-힣]+\d+가)', address)
        if dong_match:
            dong_name = dong_match.group(1)
            # 모든 구에서 동 이름 검색
            for sigungu_name, dong_dict in BJDONG_CODES.items():
                for dong_key, code in sorted(
                    dong_dict.items(), key=lambda x: len(
                        x[0]), reverse=True):
                    if dong_key in dong_name or dong_name in dong_key:
                        sigungu_code = SIGUNGU_CODES.get(sigungu_name)
                        sigungu_name = sigungu_name
                        bjdong_code = code
                        bjdong_name = dong_key
                        break
                if bjdong_code:
                    break

    return {
        'sigungu_code': sigungu_code,
        'sigungu_name': sigungu_name,
        'bjdong_code': bjdong_code,
        'bjdong_name': bjdong_name,
        'bun': bun or '0000',
        'ji': ji or '0000'  # 지 번호가 없으면 0000
    }


if __name__ == "__main__":
    # 테스트
    test_addresses = [
        "서울특별시 강남구 개포동 12번지",
        "중구 종로2가 53-4",
        "대구 중구 종로2가 53-4",
        "중구 삼덕동2가 122"
    ]

    for test_address in test_addresses:
        result = parse_address(test_address)
        print(f"주소: {test_address}")
        print(f"결과: {result}")
        print("-" * 50)
