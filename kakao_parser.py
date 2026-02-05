"""
카카오톡 매물 정보 파싱 모듈
카톡 텍스트에서 매물 정보를 추출합니다.
"""
import re
from typing import Dict, Optional, Tuple


class KakaoPropertyParser:
    """카카오톡 매물 정보 파서"""

    def __init__(self):
        # 용도 약어 매핑
        self.usage_abbreviation = {
            '제2종근생': '제2종 근린생활시설',  # 제2종근생 우선 매칭
            '제1종근생': '제1종 근린생활시설',  # 제1종근생 우선 매칭
            '1종근생': '제1종 근린생활시설',
            '2종근생': '제2종 근린생활시설',
            '1종근린': '제1종 근린생활시설',
            '2종근린': '제2종 근린생활시설',
            '제1종': '제1종 근린생활시설',
            '제2종': '제2종 근린생활시설',
            '1종': '제1종 근린생활시설',
            '2종': '제2종 근린생활시설',
            '근생': '근린생활시설',
            '근린': '근린생활시설',
            '사무소': '사무소',
            '사무실': '사무실',
            '상가': '상가',
            '점포': '점포',
            '판매시설': '판매시설',  # ✅ 추가
            '교육연구시설': '교육연구시설',  # ✅ 추가
            '노유자시설': '노유자시설',  # ✅ 추가
            '수련시설': '수련시설',  # ✅ 추가
            '운동시설': '운동시설',  # ✅ 추가
            '업무시설': '업무시설',  # ✅ 추가
            '숙박시설': '숙박시설',  # ✅ 추가
            '위락시설': '위락시설',  # ✅ 추가
            '공장': '공장',  # ✅ 추가
            '창고시설': '창고시설',  # ✅ 추가
            '위험물저장및처리시설': '위험물 저장 및 처리 시설',  # ✅ 추가
            '자동차관련시설': '자동차 관련 시설',  # ✅ 추가
            '동물및식물관련시설': '동물 및 식물 관련 시설',  # ✅ 추가
            '분뇨및쓰레기처리시설': '분뇨 및 쓰레기 처리 시설',  # ✅ 추가
            '교정및군사시설': '교정 및 군사 시설',  # ✅ 추가
            '방송통신시설': '방송통신시설',  # ✅ 추가
            '발전시설': '발전시설',  # ✅ 추가
            '묘지관련시설': '묘지 관련 시설',  # ✅ 추가
            '관광휴게시설': '관광휴게시설',  # ✅ 추가
            '장례시설': '장례시설',  # ✅ 추가
            '단독주택': '단독주택',  # ✅ 추가
            '공동주택': '공동주택',  # ✅ 추가
            '다가구': '다가구주택',  # ✅ 추가
            '다세대': '다세대주택',  # ✅ 추가
            '연립': '연립주택',  # ✅ 추가
            '아파트': '아파트',  # ✅ 추가
        }

    def parse(self, text: str) -> Dict:
        """
        카톡 텍스트를 파싱하여 매물 정보 추출

        예시 입력:
        중구 대안동 70-1 4층
        1. 500/35 부가세없음
        2. 관리비 실비정산
        3. 무권리
        4. 제1종근생 사무소 / 24.36m2 / 약 7평
        5. 1층 주차장 있지만 협소 / 내부화장실1개
        6. 동향
        7. 등기 o 불법 x
        8. 임대인 010 3547 3814
        """
        result = {
            'address': None,
            'floor': None,  # 지하층은 음수로 저장 (예: 지하1층 -> -1)
            'is_basement': False,  # 지하층 여부 플래그
            'ho': None,  # 호수 추가
            'deposit': None,
            'monthly_rent': None,
            'vat_included': None,
            'maintenance_fee': None,
            'rights': None,
            'usage': None,
            'usage_detail': None,
            'area_m2': None,
            'area_pyeong': None,
            'actual_area_m2': None,  # 실면적(계약면적) 추가
            'actual_area_pyeong': None,  # 실면적 평수 추가
            'parking': None,
            'bathroom_count': None,
            'direction': None,
            'registration': None,
            'illegal': None,
            'landlord_phone': None,
            'raw_text': text,
            'input_usage_from_numbered_list': None  # 번호 리스트에서 추출한 용도 키워드 (원본)
        }

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # 첫 줄: 주소 및 층수, 호수 추출
        if lines:
            first_line = lines[0]
            result['address'], result['floor'], result['ho'], result['dong'], result['is_basement'] = self._parse_address_and_floor(
                first_line)

        # 번호 리스트 영역만 추출 (1., 2., 3. 등으로 시작하는 행들)
        # 번호 리스트가 끝나는 지점 찾기 (번호로 시작하지 않는 행이 나오면 그 이후는 모두 무시)
        # 단, 번호 리스트 중간에 번호가 없는 줄(예: "또는...")이 있어도 다음 번호 줄이 나오면 계속 추가
        numbered_lines = []
        in_numbered_list = False  # 번호 리스트 영역에 진입했는지 여부
        consecutive_non_numbered = 0  # 연속된 번호 없는 줄 개수

        for line in lines[1:]:  # 첫 줄(주소) 제외
            # 숫자 번호로 시작하는 행인지 확인 (예: "1. ", "2.", "10. " 등)
            if re.match(r'^\d+\.\s*', line):
                numbered_lines.append(line)
                in_numbered_list = True  # 번호 리스트 영역 진입
                consecutive_non_numbered = 0  # 번호 줄이 나오면 리셋
            else:
                # 번호로 시작하지 않는 행이 나오면
                if in_numbered_list:
                    # 이미 번호 리스트 영역에 진입했다면
                    consecutive_non_numbered += 1
                    # 연속으로 2줄 이상 번호가 없으면 종료 (하단 설명란 무시)
                    if consecutive_non_numbered >= 2:
                        break
                    # 1줄만 번호가 없으면 계속 (예: "또는..." 같은 줄)
                # 아직 번호 리스트 영역에 진입하지 않았다면 계속 (주소 다음 줄이 번호가 아닐 수 있음)

        # ✅ 번호 리스트가 없으면 모든 줄(주소 제외)을 파싱 대상으로 포함
        if not numbered_lines:
            numbered_lines = lines[1:]  # 첫 줄(주소) 제외한 모든 줄

        # 번호 리스트 영역에서만 화장실 수와 방향 추출
        # 화장실 수: 번호 리스트 중 '화장실', '욕실', 'W.C' 키워드가 포함된 행에서 추출
        for line in numbered_lines:
            # 화장실 관련 키워드 확인
            if any(
                keyword in line for keyword in [
                    '화장실',
                    '욕실',
                    'W.C',
                    'wc',
                    'WC']):
                bathroom_result = self._parse_bathroom_count_from_numbered_line(
                    line)
                if bathroom_result is not None:
                    result['bathroom_count'] = bathroom_result
                    break  # 첫 번째 매칭된 행만 사용

        # 방향: 번호 리스트 중 '방향', '향' 키워드가 포함된 행에서만 추출
        for line in numbered_lines:
            # "향"으로 끝나는 단어가 포함되어 있거나 "방향" 키워드가 있으면 방향으로 간주
            if '방향' in line or any(
                keyword in line for keyword in [
                    '남동향',
                    '남서향',
                    '북동향',
                    '북서향',
                    '동향',
                    '서향',
                    '남향',
                    '북향']):
                direction = self._parse_direction_from_numbered_line(line)
                if direction:
                    result['direction'] = direction
                    break  # 첫 번째 매칭된 행만 사용

        # 나머지 줄 파싱 (번호 리스트 영역만)
        for line in numbered_lines:
            # 보증금/월세 추출 (예: 500/35)
            deposit_rent = self._parse_deposit_rent(line)
            if deposit_rent:
                result['deposit'] = deposit_rent[0]
                result['monthly_rent'] = deposit_rent[1]
                if '부가세없음' in line or '부가세 없음' in line or 'vat' in line.lower():
                    result['vat_included'] = False
                elif '부가세포함' in line or '부가세 포함' in line:
                    result['vat_included'] = True

            # 관리비
            if '관리비' in line:
                result['maintenance_fee'] = self._parse_maintenance_fee(line)

            # 권리금
            if '권리' in line:
                result['rights'] = self._parse_rights(line)

            # 용도 및 면적
            # 면적이 있는 줄 (m2, ㎡, 평 등이 있거나 계약/전용/실면적 키워드가 있으면 면적 정보로 간주)
            # 용도와 면적을 함께 입력하므로, 면적이 있는 줄에서만 용도를 추출
            has_area = 'm2' in line.lower(
            ) or '㎡' in line or '평' in line or '계약' in line or '전용' in line or '실면적' in line
            if has_area or '근생' in line or '근린' in line:
                # 번호 리스트에서 용도 키워드 추출 (원본 텍스트에서)
                if not result['input_usage_from_numbered_list']:
                    input_usage_keyword = self._extract_usage_keyword_from_line(
                        line)
                    if input_usage_keyword:
                        result['input_usage_from_numbered_list'] = input_usage_keyword

                usage_info = self._parse_usage_and_area(line)
                if usage_info:
                    if usage_info.get('usage'):
                        result['usage'] = usage_info.get('usage')
                    if usage_info.get('usage_detail'):
                        result['usage_detail'] = usage_info.get('usage_detail')
                    if usage_info.get('area_m2'):
                        result['area_m2'] = usage_info.get('area_m2')
                    if usage_info.get('area_pyeong'):
                        result['area_pyeong'] = usage_info.get('area_pyeong')
                    # 실면적(계약면적) 추가
                    if usage_info.get('actual_area_m2'):
                        result['actual_area_m2'] = usage_info.get(
                            'actual_area_m2')
                    if usage_info.get('actual_area_pyeong'):
                        result['actual_area_pyeong'] = usage_info.get(
                            'actual_area_pyeong')

            # 주차장
            if '주차' in line:
                result['parking'] = self._parse_parking(line)

            # 화장실과 방향은 이미 번호 리스트 영역에서 추출했으므로 여기서는 제외

            # 등기/불법/위반건축물
            if '등기' in line:
                result['registration'] = self._parse_registration(line)
            if '불법' in line or '위반' in line or '건축물' in line:
                result['illegal'] = self._parse_illegal(line)

            # 임대인 전화번호
            phone = self._parse_phone(line)
            if phone:
                result['landlord_phone'] = phone

        return result

    def _parse_address_and_floor(self,
                                 text: str) -> Tuple[Optional[str],
                                                     Optional[int],
                                                     Optional[str],
                                                     Optional[str],
                                                     bool]:
        """주소와 층수, 호수, 동 추출 (소재지 우선 분석)"""
        # 소재지에서 호수 정보 먼저 추출
        # 호수 패턴: "101호", "2층 201호", "상가 105호", "동 101호", "1동 101호" 등
        ho = None
        dong = None

        # 패턴 1: "동 호수" 형식 (예: "동 101호", "1동 101호", "A동 101호", "111동 B01호")
        dong_ho_pattern = re.search(
            r'(\d+|[가-힣a-zA-Z])\s*동\s*([A-Z]?\d+)\s*호',
            text,
            re.IGNORECASE)
        if dong_ho_pattern:
            dong = dong_ho_pattern.group(1)  # 동 번호 추출
            ho = dong_ho_pattern.group(2)  # 호수 추출 (B01, 101 등)
        else:
            # 패턴 2: "층 호수" 형식 (예: "3층 101호", "1층 B01호")
            floor_ho_pattern = re.search(
                r'(\d+)\s*층\s*([A-Z]?\d+)\s*호', text, re.IGNORECASE)
            if floor_ho_pattern:
                ho = floor_ho_pattern.group(2)  # 호수 추출 (B01, 101 등)
            else:
                # 패턴 3: "상가 호수" 형식 (예: "상가 105호", "상가1층 B01호", "상가1층101호")
                # "상가" + 층수(선택) + "층"(선택) + 공백(선택) + 호수 + "호"
                # 우선순위: "상가1층 101호" 형식 (층수와 호수 사이 공백 있음)
                sanga_ho_pattern = re.search(
                    r'상가\s*(\d+)\s*층\s+([A-Z]?\d+)\s*호', text, re.IGNORECASE)
                if sanga_ho_pattern:
                    ho = sanga_ho_pattern.group(2)  # 호수 (두 번째 그룹, B01, 101 등)
                else:
                    # 패턴 3-2: "상가1층101호" 형식 (층수와 호수 사이 공백 없음)
                    sanga_ho_pattern2 = re.search(
                        r'상가\s*(\d+)\s*층\s*([A-Z]?\d+)\s*호', text, re.IGNORECASE)
                    if sanga_ho_pattern2:
                        ho = sanga_ho_pattern2.group(2)  # 호수 (B01, 101 등)
                    else:
                        # 패턴 3-3: "상가 105호" 형식 (층수 없음, "상가"와 호수 사이 공백)
                        sanga_ho_pattern3 = re.search(
                            r'상가\s+([A-Z]?\d+)\s*호', text, re.IGNORECASE)
                        if sanga_ho_pattern3:
                            ho = sanga_ho_pattern3.group(1)  # 호수 (B01, 105 등)
                        else:
                            # 패턴 4: 단순 "호수" 형식 (예: "101호", "B01호", "A동 105호")
                            # 영문+숫자 조합도 지원 (예: B01, A101)
                            ho_match = re.search(
                                r'([A-Z]?\d+)\s*호', text, re.IGNORECASE)
                            if ho_match:
                                ho_num = ho_match.group(1)
                                # 호수는 보통 1~4자리 숫자 또는 영문1자+숫자
                                # "B01", "101", "A동 105" 등
                                ho = ho_num

        # 동 정보만 있는 경우 (호수 없이 "111동", "A동" 등)
        if not dong:
            # 번지수를 먼저 찾기
            bunji_match = re.search(r'(\d+(?:-\d+)?)\s+', text)
            if bunji_match:
                # 번지수 이후 텍스트에서 동 찾기
                after_bunji_text = text[bunji_match.end():]

                # 우선순위 1: 숫자 동 (예: "111동", "109동")
                dong_numeric_pattern = re.search(
                    r'(\d+)\s*동', after_bunji_text, re.IGNORECASE)
                if dong_numeric_pattern:
                    dong = dong_numeric_pattern.group(1)
                else:
                    # 우선순위 2: 영문 동 (예: "A동", "B동") - 번지수 이후에만
                    dong_alpha_pattern = re.search(
                        r'([A-Z])\s*동', after_bunji_text, re.IGNORECASE)
                    if dong_alpha_pattern:
                        dong = dong_alpha_pattern.group(1)

        # 호수/동 정보가 추출되었다면 해당 부분을 제거
        if dong and ho:
            # 동과 호수가 함께 있는 경우 제거 (예: "111동 B01호")
            text = re.sub(
                r'(\d+|[가-힣a-zA-Z])\s*동\s*' +
                re.escape(
                    str(ho)) +
                r'\s*호',
                '',
                text,
                flags=re.IGNORECASE)
            text = text.strip()
        elif ho:
            # 호수만 있는 경우 제거 (예: "지하1층 B01호" -> "지하1층")
            text = re.sub(
                r'(\d+)\s*층\s*' +
                re.escape(
                    str(ho)) +
                r'\s*호',
                r'\1층',
                text,
                flags=re.IGNORECASE)
            text = re.sub(
                r'상가\s*\d*\s*층?\s*' +
                re.escape(
                    str(ho)) +
                r'\s*호',
                '',
                text,
                flags=re.IGNORECASE)
            text = re.sub(
                re.escape(
                    str(ho)) +
                r'\s*호',
                '',
                text,
                flags=re.IGNORECASE)
            text = text.strip()
        elif dong:
            # 동만 있는 경우 제거 (주소의 동/읍/면은 제거하지 않도록 주의)
            # 번지수 뒤에 오는 동만 제거 (예: "758 111동" -> "758")
            # 패턴: 숫자(번지수) + 공백(선택) + 동번호 + "동"
            text = re.sub(
                r'(\d+)\s+' +
                re.escape(
                    str(dong)) +
                r'\s*동',
                r'\1',
                text,
                flags=re.IGNORECASE)
            text = text.strip()

        # 층수 추출 (예: 4층, 3F, 3층) - 호수 추출 후
        # 지하층 판별: 숫자 바로 앞에 "지하", "지", "B", "b", "-" 키워드 확인
        floor_match = re.search(
            r'(지하|지|B|b|-)?\s*(\d+)\s*층',
            text,
            re.IGNORECASE)
        floor = None
        is_basement = False
        if floor_match:
            basement_keyword = floor_match.group(1)  # 지하층 키워드 (지하, 지, B, b, -)
            floor_num = int(floor_match.group(2))  # 층수 숫자

            # 지하층 판별: 키워드가 있고 None이 아니면 지하층
            if basement_keyword:
                is_basement = True
                # 지하층은 음수로 저장 (예: 지하1층 -> -1)
                floor = -floor_num
            else:
                # 지상층은 양수로 저장
                floor = floor_num

            # 층수 부분 제거 (나중에 주소 정제 시 사용)
            text_before_floor = text[:floor_match.start()].strip()
            text_after_floor = text[floor_match.end():].strip()
            # 층수 앞부분과 뒷부분을 합치되, 층수는 제거
            text = (text_before_floor + ' ' + text_after_floor).strip()

        # 주소 정제: 주소 뒤의 쉼표(,), 마침표(.), 띄어쓰기 이후의 건물명/설명 제거
        # 예: "중구 삼덕동2가 122, 1층" -> "중구 삼덕동2가 122"
        # 예: "중구 삼덕동2가 122. 1층" -> "중구 삼덕동2가 122"
        # 예: "중구 삼덕동2가 122 전 다이벌스카페" -> "중구 삼덕동2가 122"

        # 번지수 패턴 찾기 (예: 122, 122-3, 122번지 등)
        bunji_patterns = [
            r'(\d+-\d+)',  # 122-3 형식
            r'(\d+번지)',  # 122번지 형식
            r'(\d+)',      # 122 형식 (마지막 숫자)
        ]

        # 번지수 위치 찾기
        bunji_end_pos = len(text)
        for pattern in bunji_patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                # 마지막 번지수 패턴의 끝 위치
                last_match = matches[-1]
                bunji_end_pos = last_match.end()
                break

        # 번지수 이후의 쉼표, 마침표, 띄어쓰기 이후 내용 제거
        if bunji_end_pos < len(text):
            # 번지수 이후 부분
            after_bunji = text[bunji_end_pos:].strip()
            # 쉼표, 마침표, 띄어쓰기로 시작하는 경우 제거
            if after_bunji.startswith(',') or after_bunji.startswith(
                    '.') or after_bunji.startswith(' '):
                # 첫 번째 구분자 이후의 모든 내용 제거
                text = text[:bunji_end_pos].strip()
            # 한글/영문이 바로 이어지는 경우도 제거 (건물명 등)
            elif re.match(r'^[가-힣a-zA-Z]', after_bunji):
                # 번지수까지만 유지
                text = text[:bunji_end_pos].strip()

        address = text.strip() if text.strip() else None
        return address, floor, ho, dong, is_basement

    def _parse_deposit_rent(self, text: str) -> Optional[Tuple[int, int]]:
        """보증금/월세 추출 (예: 500/35, 3000-180, 2704만/270만, 2704만 1200원/270만 4120원)"""

        # ✅ 전화번호 패턴 제거 (010, 011, 016, 017, 018, 019 등)
        # 전화번호를 임시로 제거하여 보증금/월세 파싱에 방해되지 않도록 함
        text_without_phone = re.sub(
            r'01[016789][-\s]?\d{3,4}[-\s]?\d{4}', '', text)

        # ✅ 특수기호와 띄어쓰기 정규화 (/, -, ~, 공백 등 → /)
        # 숫자 사이의 특수문자를 / 로 통일
        normalized_text = re.sub(
            r'(\d+)\s*[-~]\s*(\d+)',
            r'\1/\2',
            text_without_phone)

        # 패턴 1: "XXXX만 XXXX원/XXX만 XXX원" 형식
        pattern1 = r'(\d+)만\s*(\d+)?원?\s*/\s*(\d+)만\s*(\d+)?원?'
        match1 = re.search(pattern1, normalized_text)
        if match1:
            # 보증금: XXXX만 XXXX -> XXXX.XXXX (예: 2704만 1200 -> 2704)
            deposit_main = int(match1.group(1))
            deposit_sub = int(match1.group(2)) if match1.group(2) else 0
            # 만 단위이므로 그대로 사용 (예: 2704만 -> 2704)
            deposit = deposit_main

            # 월세: XXX만 XXX
            rent_main = int(match1.group(3))
            rent_sub = int(match1.group(4)) if match1.group(4) else 0
            rent = rent_main

            return deposit, rent

        # 패턴 2: "XXXX만/XXX만" 형식
        pattern2 = r'(\d+)만\s*/\s*(\d+)만?'
        match2 = re.search(pattern2, normalized_text)
        if match2:
            deposit = int(match2.group(1))
            rent = int(match2.group(2))
            return deposit, rent

        # 패턴 3: 기존 "숫자/숫자" 패턴 (정규화된 텍스트 사용)
        # ✅ 3자리 이하 숫자는 전화번호 가능성이 있으므로 4자리 이상만 매칭
        pattern3 = r'(\d{2,4})\s*/\s*(\d{2,3})'
        match3 = re.search(pattern3, normalized_text)
        if match3:
            deposit = int(match3.group(1))
            rent = int(match3.group(2))
            # ✅ 보증금이 너무 작으면 (100 미만) 전화번호일 가능성 → 제외
            if deposit >= 100:
                return deposit, rent

        return None

    def _parse_maintenance_fee(self, text: str) -> str:
        """관리비 정보 추출"""
        if '실비정산' in text or '실비 정산' in text:
            return '실비정산'
        elif '포함' in text:
            return '포함'
        elif '없음' in text or '없' in text:
            return '없음'
        # 숫자 추출 시도
        match = re.search(r'(\d+)', text)
        if match:
            return match.group(1)
        return text

    def _parse_rights(self, text: str) -> str:
        """권리금 정보 추출"""
        if '무권리' in text or '권리없음' in text:
            return '무권리'
        elif '권리' in text:
            # 권리금 금액 추출 시도
            match = re.search(r'(\d+)', text)
            if match:
                return match.group(1)
            return '있음'
        return '정보없음'

    def _parse_usage_and_area(self, text: str) -> Optional[Dict]:
        """용도 및 면적 추출 (전용면적, 실면적, 계약면적 모두 추출)"""
        result = {}

        # 용도 추출
        usage = None
        usage_detail = None

        # 약어를 표준 명칭으로 변환 (긴 것부터 매칭하도록 정렬)
        # 예: "제2종근린생활시설"이 "제2종"보다 먼저 매칭되도록
        sorted_abbrevs = sorted(
            self.usage_abbreviation.items(),
            key=lambda x: len(
                x[0]),
            reverse=True)
        for abbrev, standard in sorted_abbrevs:
            if abbrev in text:
                usage = standard
                break

        # 사무소/사무실 상세 정보
        if '사무소' in text or '사무실' in text:
            usage_detail = '사무소' if '사무소' in text else '사무실'
            if not usage:
                usage = '사무소' if '사무소' in text else '사무실'

        # 면적 추출 - 실면적(계약면적) 우선 추출, 전용면적도 추출
        area_m2 = None  # 전용면적 또는 기본 면적
        actual_area_m2 = None  # 실면적(계약면적)

        # 1. "전용면적, 실면적, 실평수" 형식 검색 (예: "전용면적 100m2, 실면적 110m2")
        exclusive_actual_pattern = r'전용면적\s*(\d+\.?\d*)\s*m2[,\s]+실면적\s*(\d+\.?\d*)\s*m2'
        exclusive_actual_match = re.search(
            exclusive_actual_pattern, text, re.IGNORECASE)
        if not exclusive_actual_match:
            exclusive_actual_pattern = r'전용면적\s*(\d+\.?\d*)\s*㎡[,\s]+실면적\s*(\d+\.?\d*)\s*㎡'
            exclusive_actual_match = re.search(exclusive_actual_pattern, text)

        if exclusive_actual_match:
            # 첫 번째가 전용면적, 두 번째가 실면적
            area_m2 = float(exclusive_actual_match.group(1))
            actual_area_m2 = float(exclusive_actual_match.group(2))
        else:
            # 1-1. "실면적 XXXm2, 전용면적 XXXm2" 형식 (순서 반대)
            actual_exclusive_pattern = r'실면적\s*(\d+\.?\d*)\s*m2[,\s]+전용면적\s*(\d+\.?\d*)\s*m2'
            actual_exclusive_match = re.search(
                actual_exclusive_pattern, text, re.IGNORECASE)
            if not actual_exclusive_match:
                actual_exclusive_pattern = r'실면적\s*(\d+\.?\d*)\s*㎡[,\s]+전용면적\s*(\d+\.?\d*)\s*㎡'
                actual_exclusive_match = re.search(
                    actual_exclusive_pattern, text)

            if actual_exclusive_match:
                # 첫 번째가 실면적, 두 번째가 전용면적
                actual_area_m2 = float(actual_exclusive_match.group(1))
                area_m2 = float(actual_exclusive_match.group(2))
            else:
                # 2-0-1. "계약XX 전용XX" 형식 (m2 없이, 괄호와 평수 포함 지원)
                # ✅ "계약40 전용30(20평)" 같은 형식 지원
                contract_exclusive_no_unit_pattern = r'(계약|계약면적)\s*약?\s*(\d+\.?\d*)\s*(?:\([^)]*\))?\s*[,]?\s*(전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*(?:\([^)]*\))?'
                contract_exclusive_no_unit_match = re.search(
                    contract_exclusive_no_unit_pattern, text, re.IGNORECASE)

                # m2가 포함되어 있지 않은지 확인 (m2 있으면 다음 패턴에서 처리)
                if contract_exclusive_no_unit_match:
                    match_text = text[contract_exclusive_no_unit_match.start(
                    ):contract_exclusive_no_unit_match.end()]
                    if 'm2' not in match_text.lower() and '㎡' not in match_text:
                        # 첫 번째가 계약면적, 두 번째가 전용면적
                        actual_area_m2 = float(
                            contract_exclusive_no_unit_match.group(2))
                        area_m2 = float(
                            contract_exclusive_no_unit_match.group(4))
                        print(
                            f"🔍 [파싱] m2 없는 패턴 매칭: 계약={actual_area_m2}, 전용={area_m2}")
                        contract_exclusive_simple_match = True  # 다음 패턴 건너뛰기
                    else:
                        contract_exclusive_simple_match = None
                else:
                    contract_exclusive_simple_match = None

                # 2-0-2. "계약 XXXm2 (평수) 전용XXXm2" 형식 (괄호와 평수 포함 지원, 콤마 무시)
                # ✅ 중간에 (39평) 같은 괄호가 있어도 매칭되도록 수정
                if not contract_exclusive_simple_match:
                    contract_exclusive_simple_pattern = r'(계약|계약면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2\s*(?:\([^)]*\))?\s*[,]?\s*(전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2'
                    contract_exclusive_simple_match = re.search(
                        contract_exclusive_simple_pattern, text, re.IGNORECASE)
                    if not contract_exclusive_simple_match:
                        contract_exclusive_simple_pattern = r'(계약|계약면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡\s*(?:\([^)]*\))?\s*[,]?\s*(전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡'
                        contract_exclusive_simple_match = re.search(
                            contract_exclusive_simple_pattern, text)

                    if contract_exclusive_simple_match:
                        # 첫 번째가 계약면적, 두 번째가 전용면적
                        actual_area_m2 = float(
                            contract_exclusive_simple_match.group(2))
                        area_m2 = float(
                            contract_exclusive_simple_match.group(4))
                        print(
                            f"🔍 [파싱] 슬래시 없는 패턴 매칭 (괄호 지원): 계약={actual_area_m2}, 전용={area_m2}")
                else:
                    # 2-1. "전용 XXXm2 계약XXXm2" 형식 (순서 반대, 콤마 무시)
                    exclusive_contract_simple_pattern = r'(전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2\s+[,]?\s*(계약|계약면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2'
                    exclusive_contract_simple_match = re.search(
                        exclusive_contract_simple_pattern, text, re.IGNORECASE)
                    if not exclusive_contract_simple_match:
                        exclusive_contract_simple_pattern = r'(전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡\s+[,]?\s*(계약|계약면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡'
                        exclusive_contract_simple_match = re.search(
                            exclusive_contract_simple_pattern, text)

                    if exclusive_contract_simple_match:
                        # 첫 번째가 전용면적, 두 번째가 계약면적
                        area_m2 = float(
                            exclusive_contract_simple_match.group(2))
                        actual_area_m2 = float(
                            exclusive_contract_simple_match.group(4))

                if not actual_area_m2:
                    # 2. "계약 XXXm2 / 전용 XXXm2" 또는 "계약면적 XXXm2 / 전용면적 XXXm2" 형식
                    # (짧은 형태도 지원, 괄호 안의 평수 무시, 콤마 무시)
                    contract_exclusive_pattern = r'(계약|계약면적|전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2\s*(?:\([^)]*\))?\s*[/,]\s*(계약|계약면적|전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2\s*(?:\([^)]*\))?'
                    contract_exclusive_match = re.search(
                        contract_exclusive_pattern, text, re.IGNORECASE)
                    if not contract_exclusive_match:
                        contract_exclusive_pattern = r'(계약|계약면적|전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡\s*(?:\([^)]*\))?\s*[/,]\s*(계약|계약면적|전용|전용면적)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡\s*(?:\([^)]*\))?'
                        contract_exclusive_match = re.search(
                            contract_exclusive_pattern, text)

                    if contract_exclusive_match:
                        # 첫 번째와 두 번째 키워드 확인
                        first_keyword = contract_exclusive_match.group(1)
                        first_value = float(contract_exclusive_match.group(2))
                        second_keyword = contract_exclusive_match.group(3)
                        second_value = float(contract_exclusive_match.group(4))

                        # 계약 또는 계약면적 또는 실면적이면 첫 번째가 계약면적
                        if '계약' in first_keyword or '실면적' in first_keyword:
                            actual_area_m2 = first_value
                            area_m2 = second_value
                            print(
                                f"🔍 [파싱] 슬래시 있는 패턴 매칭 (괄호 무시): 계약={actual_area_m2}, 전용={area_m2}")
                        else:
                            area_m2 = first_value
                            actual_area_m2 = second_value
                            print(
                                f"🔍 [파싱] 슬래시 있는 패턴 매칭 (순서 반대, 괄호 무시): 전용={area_m2}, 계약={actual_area_m2}")

                if not actual_area_m2:
                    # 3. "공급 XXXm2/전용 XXXm2" 형식 우선 검색 (공급과 전용이 함께 있는 경우, "약"
                    # 포함, 콤마 무시)
                    supply_exclusive_pattern = r'공급\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2\s*[/,]\s*전용\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2'
                    supply_exclusive_match = re.search(
                        supply_exclusive_pattern, text, re.IGNORECASE)
                    if not supply_exclusive_match:
                        supply_exclusive_pattern = r'공급\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡\s*[/,]\s*전용\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡'
                        supply_exclusive_match = re.search(
                            supply_exclusive_pattern, text)

                    if supply_exclusive_match:
                        # 전용면적 사용 (두 번째 그룹), 공급면적은 실면적으로 간주할 수 있음
                        area_m2 = float(supply_exclusive_match.group(2))
                        actual_area_m2 = float(supply_exclusive_match.group(1))
                    else:
                        # 4-1. "실면적 XXX" 또는 "계약면적 XXX" 또는 "계약 XXX" 형식 검색 (m2 없이)
                        # 단, 뒤에 m2나 ㎡이 안 나오는 경우만
                        if not actual_area_m2:
                            actual_no_unit_match = re.search(
                                r'(실면적|계약면적|계약|실)\s*약?\s*(\d+\.?\d*)(?!\s*[m㎡])', text, re.IGNORECASE)
                            if actual_no_unit_match:
                                # 뒤에 "전용"이 나오는지 확인 (계약40 전용30 형식인 경우)
                                after_text = text[actual_no_unit_match.end(
                                ):actual_no_unit_match.end() + 20]
                                if '전용' in after_text:
                                    actual_area_m2 = float(
                                        actual_no_unit_match.group(2))
                                    print(
                                        f"🔍 [파싱] 계약면적 m2 없이 인식: {actual_area_m2}㎡")

                        # 4-2. "실면적 XXXm2" 또는 "계약면적 XXXm2" 또는 "계약 XXXm2" 형식 검색
                        # ("약" 포함, 콤마 무시)
                        if not actual_area_m2:
                            actual_match = re.search(
                                r'(실면적|계약면적|계약|실)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2', text, re.IGNORECASE)
                            if not actual_match:
                                actual_match = re.search(
                                    r'(실면적|계약면적|계약|실)\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡', text)

                            if actual_match:
                                actual_area_m2 = float(actual_match.group(2))

                        # 5-1. "전용 XXX" 형식 검색 (m2 없이)
                        # 단, 뒤에 m2나 ㎡이 안 나오고, 괄호 안의 평수가 있는 경우만
                        if not area_m2:
                            exclusive_no_unit_match = re.search(
                                r'전용\s*약?\s*(\d+\.?\d*)(?!\s*[m㎡])\s*\(', text, re.IGNORECASE)
                            if exclusive_no_unit_match:
                                area_m2 = float(
                                    exclusive_no_unit_match.group(1))
                                print(f"🔍 [파싱] 전용면적 m2 없이 인식: {area_m2}㎡")

                        # 5-2. "전용 XXXm2" 또는 "전용면적 XXXm2" 형식 검색 ("약" 포함, 콤마 무시)
                        if not area_m2:
                            exclusive_match = re.search(
                                r'전용면적\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2', text, re.IGNORECASE)
                            if not exclusive_match:
                                exclusive_match = re.search(
                                    r'전용면적\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡', text)
                            if not exclusive_match:
                                exclusive_match = re.search(
                                    r'전용\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2', text, re.IGNORECASE)
                            if not exclusive_match:
                                exclusive_match = re.search(
                                    r'전용\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡', text)

                            if exclusive_match:
                                area_m2 = float(exclusive_match.group(1))
                        else:
                            # 5-1. "전용면적 약 XXXm2" 형식 (전용면적과 약 사이에 공백이 있는 경우)
                            exclusive_approx_match = re.search(
                                r'전용면적\s+약\s*(\d+\.?\d*)\s*m2', text, re.IGNORECASE)
                            if not exclusive_approx_match:
                                exclusive_approx_match = re.search(
                                    r'전용면적\s+약\s*(\d+\.?\d*)\s*㎡', text)

                            if exclusive_approx_match:
                                area_m2 = float(
                                    exclusive_approx_match.group(1))
                            else:
                                # 6. "XXXm2/XXXm2" 또는 "XXXm2, XXXm2" 형식 (슬래시나 콤마로 구분, 두 번째가 전용면적, 첫 번째가 실면적, "약" 포함)
                                # 단, 평수(m2가 아닌 평)가 포함된 경우는 제외
                                slash_pattern = r'약?\s*(\d+\.?\d*)\s*[,]?\s*m2\s*[/,]\s*약?\s*(\d+\.?\d*)\s*[,]?\s*m2'
                                slash_match = re.search(
                                    slash_pattern, text, re.IGNORECASE)
                                if not slash_match:
                                    slash_pattern = r'약?\s*(\d+\.?\d*)\s*[,]?\s*㎡\s*[/,]\s*약?\s*(\d+\.?\d*)\s*[,]?\s*㎡'
                                    slash_match = re.search(
                                        slash_pattern, text)

                                if slash_match and '평' not in text[slash_match.start(
                                ):slash_match.end() + 5]:
                                    # 슬래시로 구분된 두 개의 m2 면적 (평수가 아닌 경우)
                                    # "적용" 키워드가 있으면 첫 번째가 실면적, 두 번째가 전용면적
                                    if '적용' in text:
                                        actual_area_m2 = float(
                                            slash_match.group(1))
                                        area_m2 = float(slash_match.group(2))
                                    else:
                                        # 두 번째 숫자가 전용면적, 첫 번째가 실면적로 간주
                                        actual_area_m2 = float(
                                            slash_match.group(1))
                                        area_m2 = float(slash_match.group(2))
                                else:
                                    # 7. 단순 면적만 있는 경우 (실면적으로 간주, 전용면적 없음) - "약 XXXm2" 형식 포함, 콤마 무시
                                    # "XXXm2 / XX평" 형식도 여기서 처리 (슬래시 뒤가 평수인 경우)
                                    area_m2_match = re.search(
                                        r'약\s*(\d+\.?\d*)\s*[,]?\s*m2', text, re.IGNORECASE)
                                    if not area_m2_match:
                                        area_m2_match = re.search(
                                            r'약\s*(\d+\.?\d*)\s*[,]?\s*㎡', text)
                                    if not area_m2_match:
                                        # "XXXm2 / XX평" 형식에서 m2 부분만 추출
                                        area_m2_match = re.search(
                                            r'(\d+\.?\d*)\s*[,]?\s*m2', text, re.IGNORECASE)
                                    if not area_m2_match:
                                        area_m2_match = re.search(
                                            r'(\d+\.?\d*)\s*[,]?\s*㎡', text)
                                    if not area_m2_match:
                                        area_m2_match = re.search(
                                            r'(\d+\.?\d*)\s*[,]?\s*제곱미터', text)

                                    if area_m2_match:
                                        # ✅ 면적이 하나만 있는 경우, 전용면적으로 간주 (계약면적은 None)
                                        if actual_area_m2 is None and area_m2 is None:
                                            area_m2 = float(
                                                area_m2_match.group(1))
                                            print(
                                                f"🔍 [파싱] 면적 1개 발견 → 전용면적으로 처리: {area_m2}㎡")
                                        elif actual_area_m2 is None:
                                            actual_area_m2 = float(
                                                area_m2_match.group(1))
                                        elif area_m2 is None:
                                            area_m2 = float(
                                                area_m2_match.group(1))

        # 평수 추출
        area_pyeong_match = re.search(r'약?\s*(\d+\.?\d*)\s*평', text)
        area_pyeong = None
        actual_area_pyeong = None
        if area_pyeong_match:
            # "실평수" 또는 "실평"이 있으면 실면적 평수, 없으면 전용면적 평수
            if '실평' in text:
                actual_area_pyeong = float(area_pyeong_match.group(1))
            else:
                area_pyeong = float(area_pyeong_match.group(1))

        # 면적이 있으면 평수 계산 (없는 경우만)
        if area_m2 and area_pyeong is None:
            # m²를 평으로 변환 (1평 = 3.3058 m²)
            area_pyeong = round(area_m2 / 3.3058, 1)
        if actual_area_m2 and actual_area_pyeong is None:
            actual_area_pyeong = round(actual_area_m2 / 3.3058, 1)

        if usage or area_m2 or actual_area_m2:
            result_dict = {
                'usage': usage,
                'usage_detail': usage_detail,
                'area_m2': area_m2,
                'area_pyeong': area_pyeong
            }
            # 실면적(계약면적) 추가
            if actual_area_m2:
                result_dict['actual_area_m2'] = actual_area_m2
            if actual_area_pyeong:
                result_dict['actual_area_pyeong'] = actual_area_pyeong
            return result_dict
        return None

    def _parse_parking(self, text: str) -> str:
        """주차장 정보 추출"""
        if '없음' in text or '없' in text:
            return '없음'
        elif '있음' in text or '있' in text:
            if '협소' in text:
                return '있음(협소)'
            return '있음'
        return '정보없음'

    def _parse_bathroom_count_from_numbered_line(
            self, line: str, total_floors: int = None):
        """
        번호 리스트 행에서 화장실 개수 추출
        "층마다 N개" 같은 표현이 있으면 총 층수 × N으로 계산
        """
        # "층마다 N개" 또는 "층 당 N개" 패턴 확인
        per_floor_match = re.search(
            r'층\s*(?:마다|당)\s*(\d+)\s*개', line, re.IGNORECASE)
        if per_floor_match and total_floors:
            per_floor_count = int(per_floor_match.group(1))
            return total_floors * per_floor_count

        # 일반 화장실 개수 추출
        return self._parse_bathroom_count(line)

    def _parse_direction_from_numbered_line(self, line: str) -> Optional[str]:
        """
        번호 리스트 행에서 방향 추출
        '방향', '향' 키워드가 포함된 행에서만 추출
        """
        # 방향 키워드 확인
        if '방향' in line:
            # "방향 : 남향" 같은 형식 처리
            direction_match = re.search(r'방향\s*[:=]\s*([남북동서]+향)', line)
            if direction_match:
                return direction_match.group(1)

        # "향"으로 끝나는 단어가 있으면 방향으로 간주 (예: "북향", "동향", "남동향" 등)
        direction = self._parse_direction(line)
        if direction:
            return direction

        return None

    def _extract_usage_keyword_from_line(self, line: str) -> Optional[str]:
        """
        번호 리스트 행에서 용도 키워드 추출 (원본 키워드 반환)
        면적 정보와 함께 기재된 번호 행에서 용도 키워드를 추출합니다.
        """
        # 용도 키워드 매핑 (긴 것부터 매칭)
        usage_keywords = {
            # 제1종 근린생활시설
            '1종근생': '1종근생',
            '제1종근생': '제1종근생',
            '1종근린': '1종근린',
            '제1종근린': '제1종근린',
            '제1종': '제1종',
            '1종': '1종',
            # 제2종 근린생활시설
            '2종근생': '2종근생',
            '제2종근생': '제2종근생',
            '2종근린': '2종근린',
            '제2종근린': '제2종근린',
            '제2종': '제2종',
            '2종': '2종',
            # 단독주택
            '단독': '단독',
            '다가구': '다가구',
            '원룸건물': '원룸건물',
            # 공동주택
            '아파트': '아파트',
            '빌라': '빌라',
            '다세대': '다세대',
            # 업무시설
            '오피스텔': '오피스텔',
            '사무실': '사무실',
        }

        # 긴 키워드부터 매칭 (우선순위)
        sorted_keywords = sorted(
            usage_keywords.items(),
            key=lambda x: len(
                x[0]),
            reverse=True)

        for keyword, value in sorted_keywords:
            if keyword in line:
                return value

        return None
        direction_keywords = [
            '남동향',
            '남서향',
            '북동향',
            '북서향',
            '동향',
            '서향',
            '남향',
            '북향']
        for keyword in direction_keywords:
            if keyword in line:
                return keyword

        return None

    def _parse_bathroom_count(self, text: str):
        """화장실 개수 추출 (숫자 또는 특수 형식) - 모든 특수기호 지원"""
        # 특수 형식 처리: "남녀 화장실 별도 각1개", "내부 화장실 남녀 각 1개" 등
        # 화장실 관련 특수 표현이 있으면 그대로 반환
        if '남녀' in text and '각' in text:
            # "남녀 화장실 별도 각1개", "내부 화장실 남녀 각 1개" 등
            # 화장실 관련 부분만 추출
            bathroom_part = text
            # 주차 관련 부분 제거 (예: "주차가능 / 내부 화장실 남녀 각 1개")
            if '/' in bathroom_part:
                parts = bathroom_part.split('/')
                for part in parts:
                    if '화장실' in part:
                        bathroom_part = part.strip()
                        break

            # "화장실" 키워드가 포함된 부분만 추출
            if '화장실' in bathroom_part:
                # "화장실" 앞뒤로 적절한 범위 추출
                idx = bathroom_part.find('화장실')

                # 화장실 앞부분: 문장 경계(마침표, 쉼표) 이후만 추출
                before_text = bathroom_part[:idx]
                # 마지막 마침표/쉼표 위치 찾기
                last_separator = max(
                    before_text.rfind('.'),
                    before_text.rfind(','),
                    before_text.rfind('。'))
                if last_separator >= 0:
                    start = last_separator + 1  # 구분자 다음부터
                else:
                    start = max(0, idx - 10)  # 화장실 앞 10자까지

                end = min(len(bathroom_part), idx + 30)  # 화장실 뒤 30자까지
                extracted = bathroom_part[start:end].strip()
                # 앞뒤 불필요한 부분 제거
                if '내부' in extracted or '외부' in extracted or '남녀' in extracted or '단독' in extracted:
                    return extracted
                return bathroom_part.strip()

        # 모든 특수기호 지원: :, -, =, _, 공백 등
        # "상가화장실 [특수기호] 숫자개" 형식
        # 예: "상가화장실 : 6개", "상가화장실 - 1개", "상가화장실 = 3개", "상가화장실_3개", "아파트 상가화장실 :
        # 6개"
        sanga_match = re.search(
            r'상가\s*화장실\s*[:=,\-–_\s]+\s*(\d+)\s*개',
            text,
            re.IGNORECASE)
        if sanga_match:
            return int(sanga_match.group(1))

        # "상가화장실 [특수기호] 숫자" 형식 (개수 없음)
        sanga_match2 = re.search(
            r'상가\s*화장실\s*[:=,\-–_\s]+\s*(\d+)',
            text,
            re.IGNORECASE)
        if sanga_match2:
            return int(sanga_match2.group(1))

        # "내부화장실 [특수기호] 숫자" 형식
        internal_match = re.search(r'내부\s*화장실\s*[:=,\-–_\s]*\s*(\d+)', text)
        if internal_match:
            return int(internal_match.group(1))

        # "욕실 [특수기호] 숫자개" 형식
        yoksil_match = re.search(
            r'욕실\s*[:=,\-–_\s]+\s*(\d+)\s*개',
            text,
            re.IGNORECASE)
        if yoksil_match:
            return int(yoksil_match.group(1))

        # "W.C [특수기호] 숫자개" 형식
        wc_match = re.search(
            r'W\.?C\.?\s*[:=,\-–_\s]+\s*(\d+)\s*개',
            text,
            re.IGNORECASE)
        if wc_match:
            return int(wc_match.group(1))

        # "화장실 [특수기호] 숫자개" 형식 (일반 화장실, 모든 특수기호 허용)
        # 예: "화장실 : 6개", "화장실 - 1개", "화장실 = 3개", "화장실_3개", "화장실 2개"
        # "3개 옆에 3개" 같은 경우 첫 번째 숫자만 추출
        match_with_count = re.search(r'화장실\s*[:=,\-–_\s]+\s*(\d+)\s*개', text)
        if match_with_count:
            return int(match_with_count.group(1))

        # "화장실 숫자개" 형식 (특수기호 없음, 공백만)
        match_direct = re.search(r'화장실\s+(\d+)\s*개', text)
        if match_direct:
            return int(match_direct.group(1))

        # "화장실숫자개" 형식 (공백 없음)
        match_no_space = re.search(r'화장실\s*(\d+)\s*개', text)
        if match_no_space:
            return int(match_no_space.group(1))

        # "화장실 [특수기호] 숫자" 형식 (개수 없음)
        match_no_count = re.search(r'화장실\s*[:=,\-–_\s]+\s*(\d+)', text)
        if match_no_count:
            return int(match_no_count.group(1))

        # "화장실 숫자" 형식 (특수기호 없음, 공백만)
        match_simple = re.search(r'화장실\s+(\d+)', text)
        if match_simple:
            return int(match_simple.group(1))

        # "외부화장실" 같은 경우는 숫자가 없으면 None
        if '화장실' in text and ('내부' in text or '외부' in text):
            # 숫자가 명시적으로 없는 경우
            return None

        # 마지막 시도: 화장실 키워드 뒤에 나오는 첫 번째 숫자만 추출
        # "3개 옆에 3개" 같은 경우 첫 번째 숫자만
        if '화장실' in text or '욕실' in text:
            # 화장실/욕실 키워드 뒤 30자 이내의 첫 번째 숫자만 추출
            keyword_pos = max(text.find('화장실'), text.find('욕실'))
            if keyword_pos >= 0:
                after_keyword = text[keyword_pos +
                                     3:keyword_pos + 33]  # 키워드 뒤 30자
                number_match = re.search(
                    r'[:=,\-–_\s]*\s*(\d+)', after_keyword)
                if number_match:
                    return int(number_match.group(1))

        return None

    def _parse_direction(self, text: str) -> Optional[str]:
        """방향 추출 (더 긴 방향을 먼저 매칭)"""
        # 길이순으로 정렬하여 더 긴 방향(예: 북동향)을 먼저 매칭
        directions = ['남동향', '남서향', '북동향', '북서향', '동향', '서향', '남향', '북향']
        for direction in directions:
            if direction in text:
                return direction
        return None

    def _parse_registration(self, text: str) -> Optional[bool]:
        """등기 정보 추출"""
        if re.search(r'등기\s*[oO]', text) or re.search(r'등기\s*있', text):
            return True
        elif re.search(r'등기\s*[xX]', text) or re.search(r'등기\s*없', text):
            return False
        return None

    def _parse_illegal(self, text: str) -> Optional[bool]:
        """위반건축물 여부 추출 (띄어쓰기 상관없이)"""
        # ✅ 띄어쓰기 제거한 텍스트로 검색
        text_no_space = text.replace(
            ' ',
            '').replace(
            '\t',
            '').replace(
            '\n',
            '')

        print(
            f"🔍 [위반건축물 파싱] 원본: '{text[:50]}...' | 공백제거: '{text_no_space[:50]}...'")

        # "위반건축물" 키워드 검색 (띄어쓰기 무시)
        if '위반건축물' in text_no_space:
            print(f"✅ [위반건축물] '위반건축물' 키워드 발견!")
            # "위반건축물 O" 또는 "위반건축물O" 형식
            if re.search(
                    r'위반\s*건축물\s*[oO]',
                    text) or re.search(
                    r'위반\s*건축물\s*있',
                    text):
                print(f"✅ [위반건축물] O 또는 있음 → True")
                return True
            # "위반건축물 X" 또는 "위반건축물X" 형식
            elif re.search(r'위반\s*건축물\s*[xX]', text) or re.search(r'위반\s*건축물\s*없', text):
                print(f"✅ [위반건축물] X 또는 없음 → False")
                return False
            # 키워드만 있고 O/X 표시 없으면 True로 간주
            else:
                print(f"✅ [위반건축물] 키워드만 있음 → True (기본값)")
                return True

        # 기존 "불법" 키워드도 지원 (하위 호환)
        if re.search(r'불법\s*[oO]', text) or re.search(r'불법\s*있', text):
            print(f"✅ [위반건축물] '불법' 키워드 O → True")
            return True
        elif re.search(r'불법\s*[xX]', text) or re.search(r'불법\s*없', text):
            print(f"✅ [위반건축물] '불법' 키워드 X → False")
            return False

        print(f"❌ [위반건축물] 키워드 없음 → None")
        return None

    def _parse_phone(self, text: str) -> Optional[str]:
        """전화번호 추출"""
        # 010-1234-5678 형식
        match = re.search(r'(\d{3}[-.\s]?\d{3,4}[-.\s]?\d{4})', text)
        if match:
            phone = match.group(1).replace('.', '-').replace(' ', '-')
            return phone
        return None


if __name__ == "__main__":
    # 테스트
    test_text = """중구 대안동 70-1 4층
1. 500/35 부가세없음
2. 관리비 실비정산
3. 무권리
4. 제1종근생 사무소 / 24.36m2 / 약 7평
5. 1층 주차장 있지만 협소 / 내부화장실1개
6. 동향
7. 등기 o 불법 x
8. 임대인 010 3547 3814"""

    parser = KakaoPropertyParser()
    result = parser.parse(test_text)

    print("파싱 결과:")
    for key, value in result.items():
        print(f"{key}: {value}")
