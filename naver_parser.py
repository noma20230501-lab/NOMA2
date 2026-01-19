# -*- coding: utf-8 -*-
"""
네이버 부동산 정보 파싱 모듈
네이버 부동산에서 복사한 텍스트에서 매물 정보를 추출합니다.
"""
import re
from typing import Dict, Optional, Tuple


class NaverPropertyParser:
    """네이버 부동산 정보 파서"""

    def __init__(self):
        pass

    def parse(self, text: str) -> Dict:
        """
        네이버 부동산 텍스트를 파싱하여 매물 정보 추출

        지원 형식:
        1. 탭으로 구분된 키-값 형식:
           소재지	대구시 중구 삼덕동2가
           계약/전용면적	53.19㎡/44.43㎡

        2. 콜론으로 구분된 형식:
           소재지: 대구 중구 삼덕동2가
           보증금: 2,000만원

        3. 인라인 형식:
           월세2,000/150
           해당층/총층: 1/5층
        """
        result = {
            'address': None,
            'deposit': None,
            'monthly_rent': None,
            'contract_area_m2': None,  # 계약면적
            'exclusive_area_m2': None,  # 전용면적
            'area_m2': None,  # 전용면적 (하위 호환성)
            'area_pyeong': None,
            'floor': None,
            'total_floors': None,
            'usage': None,
            'bathroom_count': None,
            'parking': None,
            'parking_count': None,  # 총 주차 대수 (숫자)
            'direction': None,
            'approval_date': None,
            'raw_text': text
        }

        # 전체 텍스트에서 직접 패턴 매칭 (인라인 형식 처리)
        self._parse_inline_patterns(text, result)

        # "필수" 키워드로 표시된 부분만 우선적으로 파싱
        self._parse_required_fields(text, result)

        # 줄 단위로 파싱 (탭/콜론 구분 형식 처리)
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        for line in lines:
            # 탭으로 구분된 형식 처리
            if '\t' in line:
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    self._parse_key_value(key, value, result)
                    continue

            # 콜론으로 구분된 형식 처리
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    self._parse_key_value(key, value, result)
                    continue

            # 소재지 추출 (특별 처리)
            if not result['address']:
                address = self._parse_address(line)
                if address:
                    result['address'] = address

            # 보증금 추출
            if not result['deposit']:
                deposit = self._parse_deposit(line)
                if deposit is not None:
                    result['deposit'] = deposit

            # 월세 추출
            if not result['monthly_rent']:
                monthly_rent = self._parse_monthly_rent(line)
                if monthly_rent is not None:
                    result['monthly_rent'] = monthly_rent

            # 면적 추출
            if not result['area_m2'] or not result['area_pyeong'] or not result['contract_area_m2'] or not result['exclusive_area_m2']:
                area_result = self._parse_area(line)
                if isinstance(area_result, tuple) and len(area_result) == 4:
                    contract_area, exclusive_area, area_m2, area_pyeong = area_result
                    if contract_area and not result['contract_area_m2']:
                        result['contract_area_m2'] = contract_area
                    if exclusive_area and not result['exclusive_area_m2']:
                        result['exclusive_area_m2'] = exclusive_area
                        result['area_m2'] = exclusive_area  # 하위 호환성
                    if area_m2 and not result['area_m2']:
                        result['area_m2'] = area_m2
                    if area_pyeong and not result['area_pyeong']:
                        result['area_pyeong'] = area_pyeong
                elif isinstance(area_result, tuple) and len(area_result) == 2:
                    # 기존 형식 호환성
                    area_m2, area_pyeong = area_result
                    if area_m2 and not result['area_m2']:
                        result['area_m2'] = area_m2
                        result['exclusive_area_m2'] = area_m2  # 전용면적으로 설정
                    if area_pyeong and not result['area_pyeong']:
                        result['area_pyeong'] = area_pyeong

            # 층수 추출
            if not result['floor']:
                floor, total_floors = self._parse_floor(line)
                if floor is not None:
                    result['floor'] = floor
                if total_floors is not None:
                    result['total_floors'] = total_floors

            # 용도 추출
            if not result['usage']:
                usage = self._parse_usage(line)
                if usage:
                    result['usage'] = usage

            # 화장실 추출
            if not result['bathroom_count']:
                bathroom_count = self._parse_bathroom(line)
                if bathroom_count is not None:
                    result['bathroom_count'] = bathroom_count

            # 주차 추출
            if not result['parking'] or result['parking_count'] is None:
                parking, parking_count = self._parse_parking(line)
                if parking and not result['parking']:
                    result['parking'] = parking
                if parking_count is not None and result['parking_count'] is None:
                    result['parking_count'] = parking_count

            # 방향 추출
            if not result['direction']:
                direction = self._parse_direction(line)
                if direction:
                    result['direction'] = direction

            # 사용승인일 추출
            if not result['approval_date']:
                approval_date = self._parse_approval_date(line)
                if approval_date:
                    result['approval_date'] = approval_date

        return result

    def _parse_required_fields(self, text: str, result: Dict):
        """
        "필수" 키워드로 표시된 필드만 정확하게 추출
        텍스트가 길어도 "필수" 키워드가 있는 부분만 찾아서 파싱
        """
        # [금액: 일천만 /일백이십만 원] 형식 (한글 숫자) - 우선 처리
        korean_price_match = re.search(
            r'\[금액:\s*([^/]+)\s*/\s*([^\]]+)\s*원\]', text)
        if korean_price_match:
            deposit_text = korean_price_match.group(1).strip()
            rent_text = korean_price_match.group(2).strip()

            deposit_num = self._convert_korean_number(deposit_text)
            if deposit_num and result['deposit'] is None:
                result['deposit'] = deposit_num

            rent_num = self._convert_korean_number(rent_text)
            if rent_num and result['monthly_rent'] is None:
                result['monthly_rent'] = rent_num

        # 필수 계약면적\t123.74 형식 (탭 또는 공백으로 구분)
        # 패턴: "필수 계약면적" 다음에 탭이나 공백이 있고, 그 다음 숫자
        contract_patterns = [
            r'필수\s*계약면적\s*\t\s*(\d+\.?\d*)',  # 탭 구분
            r'필수\s*계약면적\s+(\d+\.?\d*)',  # 공백 구분
            r'필수\s*계약면적[^\d]*(\d+\.?\d*)',  # 유연한 패턴
        ]
        for pattern in contract_patterns:
            contract_match = re.search(pattern, text)
            if contract_match and result['contract_area_m2'] is None:
                try:
                    result['contract_area_m2'] = float(contract_match.group(1))
                    break
                except BaseException:
                    pass

        # 필수 전용면적\t123.74 또는 필수 전용면적 123.74 형식
        exclusive_patterns = [
            r'필수\s*전용면적\s*\t\s*(\d+\.?\d*)',  # 탭 구분
            r'필수\s*전용면적\s+(\d+\.?\d*)',  # 공백 구분
            r'필수\s*전용면적[^\d]*(\d+\.?\d*)',  # 유연한 패턴
        ]
        for pattern in exclusive_patterns:
            exclusive_match = re.search(pattern, text)
            if exclusive_match and result['exclusive_area_m2'] is None:
                try:
                    result['exclusive_area_m2'] = float(
                        exclusive_match.group(1))
                    result['area_m2'] = result['exclusive_area_m2']  # 하위 호환성
                    break
                except BaseException:
                    pass

        # 필수 층\t해당층 2 층 / 총층 4 층 형식 (여러 줄에 걸쳐 있을 수 있음)
        # 패턴을 더 유연하게: 탭 다음에 여러 줄에 걸쳐 있을 수 있음
        floor_patterns = [
            r'필수\s*층\s*\t\s*해당층\s*(\d+)\s*층\s*/\s*총층\s*(\d+)\s*층',  # 한 줄
            r'필수\s*층\s*\t\s*해당층\s*(\d+)\s*층\s*/\s*총층\s*(\d+)\s*층',  # 여러 줄
            # 유연한 패턴
            r'필수\s*층[^\d]*해당층[^\d]*(\d+)[^\d]*층[^\d]*/\s*총층[^\d]*(\d+)[^\d]*층',
        ]
        for pattern in floor_patterns:
            floor_match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if floor_match:
                try:
                    if result['floor'] is None:
                        result['floor'] = int(floor_match.group(1))
                    if result['total_floors'] is None:
                        result['total_floors'] = int(floor_match.group(2))
                    break
                except BaseException:
                    pass

        # 필수건축물용도\t제2종 근린생활시설 형식
        # 탭 다음에 오는 값 추출 (줄바꿈 전까지)
        usage_patterns = [
            r'필수건축물용도\s*\t\s*([^\n\t]+?)(?:\n|$)',  # 탭 구분, 줄바꿈 전까지
            r'필수건축물용도\s+([^\n]+?)(?:\n|$)',  # 공백 구분
            r'필수건축물용도[^\w]*([가-힣\s]+)',  # 유연한 패턴
        ]
        for pattern in usage_patterns:
            usage_match = re.search(pattern, text)
            if usage_match and not result['usage']:
                usage = usage_match.group(1).strip()
                # 의미있는 값인지 확인
                if usage and not usage.isdigit() and len(usage) > 0:
                    result['usage'] = usage
                    break

        # 필수 욕실(화장실)수\t1 형식
        bathroom_patterns = [
            r'필수\s*욕실\s*\(?화장실\)?\s*수\s*\t\s*(\d+)',  # 탭 구분
            r'필수\s*욕실\s*\(?화장실\)?\s*수\s+(\d+)',  # 공백 구분
            r'필수\s*욕실[^\d]*화장실[^\d]*수[^\d]*(\d+)',  # 유연한 패턴
        ]
        for pattern in bathroom_patterns:
            bathroom_match = re.search(pattern, text)
            if bathroom_match and result['bathroom_count'] is None:
                try:
                    result['bathroom_count'] = int(bathroom_match.group(1))
                    break
                except BaseException:
                    pass

        # 필수 총 주차대수\t3 대 형식
        parking_patterns = [
            r'필수\s*총\s*주차대수\s*\t\s*(\d+)\s*대?',  # 탭 구분
            r'필수\s*총\s*주차대수\s+(\d+)\s*대?',  # 공백 구분
            r'필수\s*총\s*주차대수[^\d]*(\d+)\s*대?',  # 유연한 패턴
        ]
        for pattern in parking_patterns:
            parking_match = re.search(pattern, text)
            if parking_match and result['parking_count'] is None:
                try:
                    result['parking_count'] = int(parking_match.group(1))
                    break
                except BaseException:
                    pass

        # 필수 방향 (주출입구기준)\t남 형식
        direction_patterns = [
            r'필수\s*방향\s*\([^)]*\)\s*\t\s*([가-힣]+)',  # 탭 구분
            r'필수\s*방향\s*\([^)]*\)\s+([가-힣]+)',  # 공백 구분
            r'필수\s*방향[^\w]*([남북동서]+)',  # 유연한 패턴 (방향만)
        ]
        for pattern in direction_patterns:
            direction_match = re.search(pattern, text)
            if direction_match and not result['direction']:
                direction = direction_match.group(1).strip()
                # "남", "북", "동", "서" 등만 있으면 "향" 추가
                if direction in ['남', '북', '동', '서', '남동', '남서', '북동', '북서']:
                    result['direction'] = direction + '향'
                    break
                elif direction and len(direction) > 0:
                    result['direction'] = direction
                    break

        # 필수 건축물일자\t사용승인일 2019 년 3 월 18 일 형식 (여러 줄에 걸쳐 있을 수 있음)
        approval_patterns = [
            # 한 줄
            r'필수\s*건축물일자\s*\t\s*사용승인일\s*(\d+)\s*년\s*(\d+)\s*월\s*(\d+)\s*일',
            # 여러 줄
            r'필수\s*건축물일자[^\d]*사용승인일[^\d]*(\d+)\s*년[^\d]*(\d+)\s*월[^\d]*(\d+)\s*일',
        ]
        for pattern in approval_patterns:
            approval_match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if approval_match and not result['approval_date']:
                try:
                    year = approval_match.group(1)
                    month = approval_match.group(2)
                    day = approval_match.group(3)
                    result['approval_date'] = f"{year}.{
                        month.zfill(2)}.{
                        day.zfill(2)}"
                    break
                except BaseException:
                    pass

        # 소재지 추출 (필수소재지 + 필수주소)
        # 형식: "필수소재지\t대구\n\t수성구\n\t만촌동\n필수주소\t일반 산 421-35 번지"
        address_parts = []

        # 더 강력한 패턴: 필수소재지 섹션 전체 추출 (필수주소 전까지)
        # 패턴: 필수소재지 다음 탭 이후 모든 줄을 추출 (필수주소 전까지)
        # 형식: "필수소재지\t대구\n\t수성구\n\t만촌동" 또는 "필수소재지\t\n대구\n수성구\n만촌동"
        # 빈 줄도 포함하여 모든 줄 처리
        required_address_section = re.search(
            r'필수소재지\s*\t\s*((?:[^\n]*\n)*?)(?=\n\s*필수주소|\n\s*\[|$)',
            text,
            re.MULTILINE | re.DOTALL)
        if required_address_section:
            address_section = required_address_section.group(1)
            # 줄바꿈으로 구분된 각 줄에서 주소 요소 추출
            # 빈 줄도 포함하여 모든 줄 처리
            all_lines = address_section.split('\n')
            seen_parts = set()  # 중복 체크용

            for line in all_lines:
                line = line.strip()
                if not line:
                    continue

                # 탭으로 구분된 경우도 처리
                parts = [p.strip() for p in line.split('\t') if p.strip()]
                for part in parts:
                    if part and part != '선택' and len(part) > 0:
                        # "필수주소", "일반", "산" 같은 불필요한 단어 제거
                        if part in ['필수주소', '일반', '산', '필수소재지']:
                            continue

                        # 중복 제거: 정확히 같은 문자열이면 추가하지 않음
                        if part not in seen_parts:
                            # 부분 일치 체크: "만촌동"이 이미 있으면 다시 추가하지 않음
                            is_duplicate = False
                            for existing in address_parts:
                                # 정확히 같거나, 한쪽이 다른 쪽에 포함되어 있으면 중복
                                if part == existing or (
                                        len(part) > 2 and part in existing) or (
                                        len(existing) > 2 and existing in part):
                                    is_duplicate = True
                                    break
                            if not is_duplicate:
                                # 주소 요소 순서 정렬: 시/도 -> 시/군/구 -> 읍/면/동
                                if not address_parts:
                                    address_parts.append(part)
                                    seen_parts.add(part)
                                else:
                                    # 이미 있는 요소와 비교하여 적절한 위치에 삽입
                                    inserted = False
                                    # 시/도 체크
                                    if part in [
                                            '대구', '서울', '부산', '인천', '광주', '대전', '울산', '세종']:
                                        if part not in address_parts:
                                            address_parts.insert(0, part)
                                            seen_parts.add(part)
                                            inserted = True
                                    # 시/군/구 체크
                                    elif '구' in part or '군' in part:
                                        # 이미 구/군이 있으면 추가하지 않음
                                        has_gu = any(
                                            '구' in e or '군' in e for e in address_parts)
                                        if not has_gu:
                                            # 시/도 다음에 삽입
                                            if address_parts and address_parts[0] in [
                                                    '대구', '서울', '부산', '인천', '광주', '대전', '울산', '세종']:
                                                address_parts.insert(1, part)
                                            else:
                                                address_parts.insert(0, part)
                                            seen_parts.add(part)
                                            inserted = True
                                    # 동 체크
                                    elif '동' in part:
                                        # 동은 마지막에 추가
                                        address_parts.append(part)
                                        seen_parts.add(part)
                                        inserted = True

                                    if not inserted:
                                        address_parts.append(part)
                                        seen_parts.add(part)

        # 필수주소 추출: "필수주소\t일반 산 421-35 번지" 형식
        # 여러 줄에 걸쳐 있고 숫자와 하이픈이 분리되어 있을 수 있음
        detail_address_match = re.search(
            r'필수주소\s*\t\s*([^\n]+(?:\n[^\t\n]+)*?)(?=\n\s*\[|상세주소|필수|$)',
            text,
            re.MULTILINE | re.DOTALL)
        if detail_address_match:
            detail_addr_raw = detail_address_match.group(1)

            # 원본 텍스트에서 숫자와 하이픈을 직접 찾기 (줄바꿈 포함)
            # "421\n-\n35" 형식 처리
            numbers = re.findall(r'\d+', detail_addr_raw)
            if len(numbers) >= 2:
                # 두 개 이상의 숫자가 있으면 번지 형식으로 추출
                detail_addr = f"{numbers[0]}-{numbers[1]}번지"
            elif len(numbers) == 1:
                detail_addr = f"{numbers[0]}번지"
            else:
                # 정규화된 텍스트에서 패턴 매칭 시도
                detail_addr_normalized = re.sub(
                    r'\s+', ' ', detail_addr_raw).strip()
                bunji_match = re.search(
                    r'(?:일반\s*)?(?:산\s*)?(\d+)\s*-\s*(\d+)\s*번지?',
                    detail_addr_normalized)
                if bunji_match:
                    bun = bunji_match.group(1)
                    ji = bunji_match.group(2)
                    detail_addr = f"{bun}-{ji}번지"
                else:
                    bunji_match = re.search(
                        r'(?:일반\s*)?(?:산\s*)?(\d+)\s*번지?',
                        detail_addr_normalized)
                    if bunji_match:
                        bun = bunji_match.group(1)
                        detail_addr = f"{bun}번지"
                    else:
                        # 번지 패턴을 찾지 못한 경우 원본에서 "일반"과 "산"만 제거
                        detail_addr = re.sub(
                            r'일반\s*', '', detail_addr_normalized)
                        detail_addr = re.sub(r'산\s*', '', detail_addr).strip()

            if address_parts:
                # 소재지 + 상세주소 조합 (산 제거)
                # "필수주소", "일반", "산" 같은 불필요한 단어 제거
                filtered_parts = [
                    p for p in address_parts if p not in [
                        '필수주소', '일반', '산', '필수소재지']]
                if filtered_parts:
                    result['address'] = ' '.join(
                        filtered_parts) + ' ' + detail_addr
                else:
                    result['address'] = detail_addr
            else:
                # 상세주소만 있는 경우
                result['address'] = detail_addr
        elif address_parts and not result['address']:
            # 소재지만 있는 경우
            # "필수주소", "일반", "산" 같은 불필요한 단어 제거
            filtered_parts = [
                p for p in address_parts if p not in [
                    '필수주소', '일반', '산', '필수소재지']]
            if filtered_parts:
                result['address'] = ' '.join(filtered_parts)
            else:
                result['address'] = None

        # 최종 결과에서 "필수주소", "일반", "산" 같은 불필요한 단어 제거
        if result.get('address'):
            # "필수주소 일반 산" 같은 패턴 제거
            address = result['address']
            # "필수주소" 제거
            address = re.sub(r'필수주소\s*', '', address)
            # "일반" 제거
            address = re.sub(r'일반\s*', '', address)
            # "산" 제거 (단, "산"이 번지 앞에 있는 경우만)
            address = re.sub(r'산\s+(\d)', r'\1', address)
            # "필수소재지" 제거
            address = re.sub(r'필수소재지\s*', '', address)
            # 연속된 공백 정리
            address = re.sub(r'\s+', ' ', address).strip()
            result['address'] = address

        # 디버깅: 소재지가 여전히 없으면 더 넓은 범위에서 찾기
        if not result.get('address'):
            # "대구", "수성구", "만촌동" 같은 키워드를 직접 찾기
            sido_patterns = ['대구', '서울', '부산', '인천', '광주', '대전', '울산', '세종']
            sigungu_patterns = [
                '수성구',
                '중구',
                '남구',
                '북구',
                '동구',
                '서구',
                '달서구',
                '달성군']
            # 동 이름은 더 넓은 패턴으로 찾기 (동으로 끝나는 모든 패턴)
            dong_pattern = re.search(r'([가-힣]+동)', text)

            found_parts = []
            # 시/도 찾기
            for pattern in sido_patterns:
                if pattern in text:
                    found_parts.append(pattern)
                    break

            # 시/군/구 찾기
            for pattern in sigungu_patterns:
                if pattern in text and pattern not in found_parts:
                    found_parts.append(pattern)
                    break

            # 동 찾기
            if dong_pattern:
                dong_name = dong_pattern.group(1)
                if dong_name not in found_parts:
                    found_parts.append(dong_name)

            # 번지 찾기 (필수주소에서)
            if detail_address_match:
                detail_addr_raw = detail_address_match.group(1)
                numbers = re.findall(r'\d+', detail_addr_raw)
                if len(numbers) >= 2:
                    bunji = f"{numbers[0]}-{numbers[1]}번지"
                elif len(numbers) == 1:
                    bunji = f"{numbers[0]}번지"
                else:
                    bunji = None

                if bunji and found_parts:
                    result['address'] = ' '.join(found_parts) + ' ' + bunji
                elif found_parts:
                    result['address'] = ' '.join(found_parts)
            elif found_parts:
                result['address'] = ' '.join(found_parts)

    def _parse_inline_patterns(self, text: str, result: Dict):
        """인라인 패턴 파싱 (예: "월세2,000/150", "해당층/총층: 1/5층")"""
        # [금액: 일천만 /일백이십만 원] 형식 (한글 숫자)
        korean_price_match = re.search(
            r'\[금액:\s*([^/]+)\s*/\s*([^\]]+)\s*원\]', text)
        if korean_price_match:
            deposit_text = korean_price_match.group(1).strip()
            rent_text = korean_price_match.group(2).strip()

            deposit_num = self._convert_korean_number(deposit_text)
            if deposit_num and result['deposit'] is None:
                result['deposit'] = deposit_num

            rent_num = self._convert_korean_number(rent_text)
            if rent_num and result['monthly_rent'] is None:
                result['monthly_rent'] = rent_num

        # 월세 패턴: "월세2,000/150" 또는 "월세 2,000/150"
        if result['deposit'] is None or result['monthly_rent'] is None:
            monthly_match = re.search(r'월세\s*([\d,]+)\s*/\s*([\d,]+)', text)
            if monthly_match:
                try:
                    if result['deposit'] is None:
                        result['deposit'] = int(
                            monthly_match.group(1).replace(',', ''))
                    if result['monthly_rent'] is None:
                        result['monthly_rent'] = int(
                            monthly_match.group(2).replace(',', ''))
                except BaseException:
                    pass

        # 보증금/월세 패턴: "2,000/150" (앞에 보증금이 없을 때)
        if result['deposit'] is None:
            deposit_match = re.search(r'보증금\s*([\d,]+)', text)
            if deposit_match:
                try:
                    result['deposit'] = int(
                        deposit_match.group(1).replace(',', ''))
                except BaseException:
                    pass

    def _parse_key_value(self, key: str, value: str, result: Dict):
        """키-값 쌍 파싱"""
        key_lower = key.lower()

        # "필수" 키워드가 있는 경우도 처리
        key_clean = key.replace('필수', '').strip()

        # 소재지
        if ('소재지' in key or '소재지' in key_clean) and not result['address']:
            result['address'] = value.strip().replace(
                '대구시', '대구').replace('시 ', ' ')

        # 보증금
        if ('보증금' in key or '보증금' in key_clean) and result['deposit'] is None:
            deposit = self._parse_deposit(value)
            if deposit is not None:
                result['deposit'] = deposit

        # 월세
        if (
                '월세' in key or '월세' in key_clean) and result['monthly_rent'] is None:
            monthly_rent = self._parse_monthly_rent(value)
            if monthly_rent is not None:
                result['monthly_rent'] = monthly_rent

        # 계약면적: "필수 계약면적\t123.74"
        if (
                '계약면적' in key or '계약면적' in key_clean) and not result['contract_area_m2']:
            # 숫자만 추출 (단위 제거)
            area_match = re.search(r'(\d+\.?\d*)', value)
            if area_match:
                try:
                    result['contract_area_m2'] = float(area_match.group(1))
                except BaseException:
                    pass

        # 전용면적: "필수 전용면적 123.74"
        if (
                '전용면적' in key or '전용면적' in key_clean) and not result['exclusive_area_m2']:
            # 숫자만 추출 (단위 제거)
            area_match = re.search(r'(\d+\.?\d*)', value)
            if area_match:
                try:
                    result['exclusive_area_m2'] = float(area_match.group(1))
                    result['area_m2'] = result['exclusive_area_m2']  # 하위 호환성
                except BaseException:
                    pass

        # 면적 (기존 패턴도 지원)
        if (
                '면적' in key or '면적' in key_clean) and not result['exclusive_area_m2']:
            area_result = self._parse_area(value)
            if isinstance(area_result, tuple) and len(area_result) == 4:
                contract_area, exclusive_area, area_m2, area_pyeong = area_result
                if contract_area and not result['contract_area_m2']:
                    result['contract_area_m2'] = contract_area
                if exclusive_area and not result['exclusive_area_m2']:
                    result['exclusive_area_m2'] = exclusive_area
                    result['area_m2'] = exclusive_area  # 하위 호환성
                if area_m2 and not result['area_m2']:
                    result['area_m2'] = area_m2
                if area_pyeong and not result['area_pyeong']:
                    result['area_pyeong'] = area_pyeong
            elif isinstance(area_result, tuple) and len(area_result) == 2:
                # 기존 형식 호환성
                area_m2, area_pyeong = area_result
                if area_m2 and not result['area_m2']:
                    result['area_m2'] = area_m2
                    result['exclusive_area_m2'] = area_m2
                if area_pyeong and not result['area_pyeong']:
                    result['area_pyeong'] = area_pyeong

        # 층수: "필수 층\t해당층 2 층 / 총층 4 층"
        if ('층' in key or '층' in key_clean) and (
                result['floor'] is None or result['total_floors'] is None):
            # 여러 줄에 걸쳐 있을 수 있으므로 전체 텍스트에서 다시 검색
            floor, total_floors = self._parse_floor(value)
            if floor is not None and result['floor'] is None:
                result['floor'] = floor
            if total_floors is not None and result['total_floors'] is None:
                result['total_floors'] = total_floors

        # 건축물용도: "필수건축물용도\t제2종 근린생활시설"
        if ('건축물용도' in key or '건축물용도' in key_clean) and not result['usage']:
            usage = value.strip()
            if usage and not usage.isdigit():
                result['usage'] = usage

        # 용도 (기존 패턴도 지원)
        if ('용도' in key or '용도' in key_clean) and not result['usage']:
            usage = self._parse_usage(value)
            if usage:
                result['usage'] = usage

        # 화장실: "필수 욕실(화장실)수\t1"
        if (
                '욕실' in key or '화장실' in key or '욕실' in key_clean or '화장실' in key_clean) and result['bathroom_count'] is None:
            bathroom_count = self._parse_bathroom(value)
            if bathroom_count is not None:
                result['bathroom_count'] = bathroom_count

        # 주차: "필수 총 주차대수\t3 대"
        if ('주차' in key or '주차' in key_clean):
            parking, parking_count = self._parse_parking(value)
            if parking and not result['parking']:
                result['parking'] = parking
            if parking_count is not None and result['parking_count'] is None:
                result['parking_count'] = parking_count

        # 방향: "필수 방향 (주출입구기준)\t남" - "향"이 빠져있을 수 있음
        if ('방향' in key or '방향' in key_clean) and not result['direction']:
            direction = value.strip()
            # "남", "북", "동", "서" 등만 있으면 "향" 추가
            if direction in ['남', '북', '동', '서', '남동', '남서', '북동', '북서']:
                result['direction'] = direction + '향'
            else:
                # 기존 파싱 로직 사용
                direction_parsed = self._parse_direction(value)
                if direction_parsed:
                    result['direction'] = direction_parsed

        # 건축물일자/사용승인일: "필수 건축물일자\t사용승인일 2019 년 3 월 18 일"
        if (
                '건축물일자' in key or '건축물일자' in key_clean or '승인일' in key or '사용승인' in key) and not result['approval_date']:
            # 날짜 형식 추출
            date_match = re.search(r'(\d+)\s*년\s*(\d+)\s*월\s*(\d+)\s*일', value)
            if date_match:
                year = date_match.group(1)
                month = date_match.group(2)
                day = date_match.group(3)
                result['approval_date'] = f"{year}.{
                    month.zfill(2)}.{
                    day.zfill(2)}"
            else:
                # 기존 파싱 로직 사용
                approval_date = self._parse_approval_date(value)
                if approval_date:
                    result['approval_date'] = approval_date

    def _parse_address(self, text: str) -> Optional[str]:
        """소재지 추출"""
        # "소재지: 대구 중구 삼덕동2가 122" 형식
        match = re.search(
            r'소재지[:\s\t]+([가-힣\s\d-]+(?:동|가|로|길)[가-힣\s\d-]*)', text)
        if match:
            addr = match.group(1).strip()
            # "대구시" -> "대구" 변환
            addr = addr.replace('대구시', '대구').replace('시 ', ' ')
            return addr

        # "주소: ..." 형식
        match = re.search(
            r'주소[:\s\t]+([가-힣\s\d-]+(?:동|가|로|길)[가-힣\s\d-]*)', text)
        if match:
            addr = match.group(1).strip()
            addr = addr.replace('대구시', '대구').replace('시 ', ' ')
            return addr

        # "대구시 중구 삼덕동2가" 형식 (탭이나 콜론 없이)
        match = re.search(r'대구시?\s+중구\s+[가-힣\d\s-]+(?:동|가)', text)
        if match:
            addr = match.group(0).strip()
            addr = addr.replace('대구시', '대구').replace('시 ', ' ')
            return addr

        # 첫 줄이 주소 형식인 경우
        if re.search(r'대구\s+중구', text) or re.search(r'중구\s+[가-힣]+동', text):
            addr = text.strip()
            addr = addr.replace('대구시', '대구').replace('시 ', ' ')
            return addr

        return None

    def _parse_deposit(self, text: str) -> Optional[int]:
        """보증금 추출 (만원 단위)"""
        # "보증금: 2,000만원" 또는 "보증금: 2000만원" 형식
        match = re.search(r'보증금[:\s]*([\d,]+)\s*만원?', text)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except BaseException:
                pass

        # "보증금: 2,000" 형식 (만원 생략)
        match = re.search(r'보증금[:\s]*([\d,]+)\s*$', text)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except BaseException:
                pass

        return None

    def _parse_monthly_rent(self, text: str) -> Optional[int]:
        """월세 추출 (만원 단위)"""
        # "월세: 150만원" 형식
        match = re.search(r'월세[:\s]*([\d,]+)\s*만원?', text)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except BaseException:
                pass

        # "월세: 150" 형식 (만원 생략)
        match = re.search(r'월세[:\s]*([\d,]+)\s*$', text)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except BaseException:
                pass

        return None

    def _parse_area(self,
                    text: str) -> Tuple[Optional[float],
                                        Optional[float],
                                        Optional[float],
                                        Optional[float]]:
        """
        면적 추출 (계약면적, 전용면적, 전용면적(하위호환), 평)
        Returns: (contract_area_m2, exclusive_area_m2, area_m2, area_pyeong)
        """
        contract_area_m2 = None
        exclusive_area_m2 = None
        area_m2 = None
        area_pyeong = None

        # "계약/전용면적: 53.19㎡/44.43㎡" 형식
        # "계약/전용면적	53.19㎡/44.43㎡(전용률84%)" 형식
        contract_exclusive_match = re.search(
            r'계약\s*면적[:\s\t]*(\d+\.?\d*)\s*㎡\s*/\s*전용\s*면적[:\s\t]*(\d+\.?\d*)\s*㎡', text)
        if contract_exclusive_match:
            try:
                contract_area_m2 = float(contract_exclusive_match.group(1))
                exclusive_area_m2 = float(contract_exclusive_match.group(2))
                area_m2 = exclusive_area_m2  # 하위 호환성
            except BaseException:
                pass

        # "전용/계약면적: 44.43㎡/53.19㎡" 형식 (순서 반대)
        if not contract_area_m2:
            exclusive_contract_match = re.search(
                r'전용\s*면적[:\s\t]*(\d+\.?\d*)\s*㎡\s*/\s*계약\s*면적[:\s\t]*(\d+\.?\d*)\s*㎡', text)
            if exclusive_contract_match:
                try:
                    exclusive_area_m2 = float(
                        exclusive_contract_match.group(1))
                    contract_area_m2 = float(exclusive_contract_match.group(2))
                    area_m2 = exclusive_area_m2  # 하위 호환성
                except BaseException:
                    pass

        # "계약/전용면적: 53.19㎡/44.43㎡" 형식 (슬래시로만 구분)
        if not contract_area_m2:
            slash_match = re.search(
                r'(\d+\.?\d*)\s*㎡\s*/\s*(\d+\.?\d*)\s*㎡', text)
            if slash_match:
                try:
                    first_area = float(slash_match.group(1))
                    second_area = float(slash_match.group(2))
                    # 첫 번째가 더 크면 계약면적, 두 번째가 전용면적
                    if first_area > second_area:
                        contract_area_m2 = first_area
                        exclusive_area_m2 = second_area
                    else:
                        contract_area_m2 = second_area
                        exclusive_area_m2 = first_area
                    area_m2 = exclusive_area_m2  # 하위 호환성
                except BaseException:
                    pass

        # "전용면적: 44.43㎡" 형식 (전용면적만 있는 경우)
        if not exclusive_area_m2:
            exclusive_match = re.search(
                r'전용\s*면적[:\s\t]*(\d+\.?\d*)\s*㎡', text)
            if exclusive_match:
                try:
                    exclusive_area_m2 = float(exclusive_match.group(1))
                    area_m2 = exclusive_area_m2  # 하위 호환성
                except BaseException:
                    pass

        # "계약면적: 53.19㎡" 형식 (계약면적만 있는 경우)
        if not contract_area_m2:
            contract_match = re.search(r'계약\s*면적[:\s\t]*(\d+\.?\d*)\s*㎡', text)
            if contract_match:
                try:
                    contract_area_m2 = float(contract_match.group(1))
                except BaseException:
                    pass

        # 일반적인 "44.43㎡" 형식 (구분 없이)
        if not area_m2:
            m2_match = re.search(r'(\d+\.?\d*)\s*㎡', text)
            if m2_match:
                try:
                    area_m2 = float(m2_match.group(1))
                    exclusive_area_m2 = area_m2  # 전용면적으로 가정
                except BaseException:
                    pass

        # 평수 추출
        pyeong_match = re.search(r'(\d+\.?\d*)\s*평', text)
        if pyeong_match:
            try:
                area_pyeong = float(pyeong_match.group(1))
            except BaseException:
                pass

        return contract_area_m2, exclusive_area_m2, area_m2, area_pyeong

    def _parse_floor(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """층수 추출"""
        floor = None
        total_floors = None

        # "해당층 2 층 / 총층 4 층" 형식 (네이버 입력란 형식)
        match = re.search(r'해당층\s*(\d+)\s*층\s*/\s*총층\s*(\d+)\s*층', text)
        if match:
            try:
                floor = int(match.group(1))
                total_floors = int(match.group(2))
            except BaseException:
                pass

        # "해당층/총층: 1/5층" 형식 (실제 네이버 형식)
        if not floor:
            match = re.search(r'(\d+)\s*/\s*(\d+)\s*층', text)
            if match:
                try:
                    floor = int(match.group(1))
                    total_floors = int(match.group(2))
                except BaseException:
                    pass

        # "해당층/총층: 1층 / 5층" 형식
        if not floor:
            match = re.search(r'(\d+)\s*층\s*/\s*(\d+)\s*층', text)
            if match:
                try:
                    floor = int(match.group(1))
                    total_floors = int(match.group(2))
                except BaseException:
                    pass

        # "해당층 2" 형식만 있는 경우
        if not floor:
            match = re.search(r'해당층\s*(\d+)', text)
            if match:
                try:
                    floor = int(match.group(1))
                except BaseException:
                    pass

        # "총층 4" 형식만 있는 경우
        if not total_floors:
            match = re.search(r'총층\s*(\d+)', text)
            if match:
                try:
                    total_floors = int(match.group(1))
                except BaseException:
                    pass

        # "1층" 형식만 있는 경우
        if not floor:
            match = re.search(r'(\d+)\s*층', text)
            if match:
                try:
                    floor = int(match.group(1))
                except BaseException:
                    pass

        return floor, total_floors

    def _parse_usage(self, text: str) -> Optional[str]:
        """용도 추출"""
        # "건축물 용도	제1종 근린생활시설" 형식 (탭 구분)
        match = re.search(r'건축물\s*용도[:\s\t]+([가-힣\s]+)', text)
        if match:
            return match.group(1).strip()

        # "중개대상물 종류: 제1종 근린생활시설" 형식
        match = re.search(r'중개대상물\s*종류[:\s\t]+([가-힣\s]+)', text)
        if match:
            return match.group(1).strip()

        # "용도: ..." 형식
        match = re.search(r'용도[:\s\t]+([가-힣\s]+)', text)
        if match:
            return match.group(1).strip()

        return None

    def _parse_bathroom(self, text: str) -> Optional[int]:
        """화장실 개수 추출"""
        # "필수 욕실(화장실)수\t1" 형식 (탭 구분, 단위 없음)
        match = re.search(r'욕실\s*\(?화장실\)?\s*수?[:\s\t]*(\d+)', text)
        if match:
            try:
                return int(match.group(1))
            except BaseException:
                pass

        # "화장실 수	1개" 형식 (탭 구분)
        match = re.search(r'화장실\s*수?[:\s\t]*(\d+)\s*개?', text)
        if match:
            try:
                return int(match.group(1))
            except BaseException:
                pass

        # "화장실: 1개" 형식
        match = re.search(r'화장실[:\s\t]*(\d+)\s*개?', text)
        if match:
            try:
                return int(match.group(1))
            except BaseException:
                pass

        return None

    def _parse_parking(self, text: str) -> Tuple[Optional[str], Optional[int]]:
        """
        주차 정보 추출
        Returns: (parking_text, parking_count)
        """
        parking_text = None
        parking_count = None

        # "필수 총 주차대수\t3 대" 형식 (탭 구분)
        count_match = re.search(r'총\s*주차\s*대수?[:\s\t]+(\d+)\s*대?', text)
        if count_match:
            try:
                parking_count = int(count_match.group(1))
                parking_text = f"{parking_count}대"
            except BaseException:
                pass

        # "총주차대수	4대" 또는 "총 주차 대수: 4대" 형식 (숫자 우선 추출)
        if parking_count is None:
            count_match = re.search(r'총\s*주차\s*대수?[:\s\t]+(\d+)\s*대?', text)
            if count_match:
                try:
                    parking_count = int(count_match.group(1))
                    parking_text = f"{parking_count}대"
                except BaseException:
                    pass

        # "주차: 4대" 형식
        if parking_count is None:
            count_match = re.search(r'주차[:\s\t]+(\d+)\s*대', text)
            if count_match:
                try:
                    parking_count = int(count_match.group(1))
                    parking_text = f"{parking_count}대"
                except BaseException:
                    pass

        # "주차가능여부	가능" 형식 (탭 구분)
        if not parking_text:
            match = re.search(r'주차\s*가능\s*여부?[:\s\t]+([가-힣]+)', text)
            if match:
                parking_text = match.group(1).strip()

        # "주차: 가능" 또는 "주차: 불가능" 형식
        if not parking_text:
            match = re.search(r'주차[:\s\t]+([가-힣]+)', text)
            if match:
                parking_text = match.group(1).strip()

        return parking_text, parking_count

    def _parse_direction(self, text: str) -> Optional[str]:
        """방향 추출"""
        # "방향	북동향(주된 출입구 기준)" 형식 (탭 구분, 괄호 제거)
        # 정규식에서 괄호 안의 내용도 포함하여 매칭하되, 괄호는 제거
        match = re.search(r'방향[:\s\t]+([가-힣]+향)', text)
        if match:
            direction = match.group(1).strip()
            # 괄호 제거 (예: "북동향(주된 출입구 기준)" -> "북동향")
            direction = re.sub(r'\([^)]*\)', '', direction).strip()
            return direction

        # 방향 키워드 직접 찾기 (긴 것부터 매칭하여 "북동향"이 "동향"보다 우선)
        # 정확한 단어 경계를 사용하여 부분 매칭 방지
        directions = ['남동향', '남서향', '북동향', '북서향', '동향', '서향', '남향', '북향']
        for direction in directions:
            # 단어 경계를 사용하여 정확한 매칭 (예: "북동향"이 "동향"에 매칭되지 않도록)
            pattern = re.escape(direction)
            if re.search(pattern, text):
                return direction

        return None

    def _parse_approval_date(self, text: str) -> Optional[str]:
        """사용승인일 추출"""
        # "필수 건축물일자\t사용승인일 2019 년 3 월 18 일" 형식 (여러 줄에 걸쳐 있을 수 있음)
        # 전체 텍스트에서 검색
        date_match = re.search(r'(\d+)\s*년\s*(\d+)\s*월\s*(\d+)\s*일', text)
        if date_match:
            year = date_match.group(1)
            month = date_match.group(2)
            day = date_match.group(3)
            return f"{year}.{month.zfill(2)}.{day.zfill(2)}"

        # "사용승인일	2012.01.25" 형식 (탭 구분)
        match = re.search(
            r'사용승인일[:\s\t]+(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})', text)
        if match:
            return match.group(1).strip()

        # "승인일: ..." 형식
        match = re.search(
            r'승인일[:\s\t]+(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})', text)
        if match:
            return match.group(1).strip()

        return None

    def _convert_korean_number(self, text: str) -> Optional[int]:
        """
        한글 숫자를 아라비아 숫자로 변환 (만원 단위)
        예: "일천만" -> 1000, "일백이십만" -> 120

        Args:
            text: 한글 숫자 텍스트

        Returns:
            변환된 숫자 (만원 단위) 또는 None
        """
        if not text:
            return None

        # 한글 숫자 매핑
        korean_digits = {
            '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
            '육': 6, '칠': 7, '팔': 8, '구': 9, '십': 10,
            '백': 100, '천': 1000, '만': 10000
        }

        # "일천만" -> 1000만원 = 1000
        # "일백이십만" -> 120만원 = 120

        # 만 단위 추출
        if '만' in text:
            # 만 앞의 숫자 추출
            before_man = text.split('만')[0].strip()
            if not before_man:
                return None

            # "일백이십만" = 일(1) * 백(100) + 이(2) * 십(10) = 100 + 20 = 120
            # "일천만" = 일(1) * 천(1000) = 1000

            # 백 단위가 있는 경우 먼저 처리
            if '백' in before_man:
                # "일백이십" 형식
                parts = before_man.split('백')
                if len(parts) == 2:
                    hundred_part = parts[0].strip()
                    rest_part = parts[1].strip()

                    hundred = korean_digits.get(hundred_part, 0) * 100
                    rest = 0

                    if rest_part:
                        if '십' in rest_part:
                            # "이십" 형식
                            ten_parts = rest_part.split('십')
                            if len(ten_parts) == 2:
                                ten_digit = korean_digits.get(
                                    ten_parts[0].strip(), 0)
                                one_digit = korean_digits.get(
                                    ten_parts[1].strip(), 0)
                                rest = ten_digit * 10 + one_digit
                            else:
                                # "십"만 있는 경우 (10)
                                rest = 10
                        else:
                            # 일의 자리만
                            rest = korean_digits.get(rest_part, 0)

                    return hundred + rest

            # 간단한 패턴: "일천" -> 1000
            if '천' in before_man:
                # 천 단위
                parts = before_man.split('천')
                if len(parts) == 2:
                    thousand_part = parts[0].strip()
                    rest_part = parts[1].strip()

                    thousand = korean_digits.get(thousand_part, 0) * 1000
                    rest = 0

                    if rest_part:
                        if '백' in rest_part:
                            hundred_parts = rest_part.split('백')
                            if len(hundred_parts) == 2:
                                hundred = korean_digits.get(
                                    hundred_parts[0].strip(), 0) * 100
                                ten_part = hundred_parts[1].strip()
                                if '십' in ten_part:
                                    ten_parts = ten_part.split('십')
                                    if len(ten_parts) == 2:
                                        ten = 10
                                        one = korean_digits.get(
                                            ten_parts[1].strip(), 0)
                                        rest = hundred + ten + one
                                    else:
                                        ten = 10
                                        rest = hundred + ten
                                else:
                                    one = korean_digits.get(ten_part, 0)
                                    rest = hundred + one
                            else:
                                rest = korean_digits.get(rest_part.strip(), 0)
                        elif '십' in rest_part:
                            ten_parts = rest_part.split('십')
                            if len(ten_parts) == 2:
                                ten = 10
                                one = korean_digits.get(
                                    ten_parts[1].strip(), 0)
                                rest = ten + one
                            else:
                                rest = 10
                        else:
                            rest = korean_digits.get(rest_part, 0)

                    return thousand + rest
            elif '백' in before_man:
                # 백 단위
                parts = before_man.split('백')
                if len(parts) == 2:
                    hundred = korean_digits.get(parts[0].strip(), 0) * 100
                    rest_part = parts[1].strip()
                    if '십' in rest_part:
                        ten_parts = rest_part.split('십')
                        if len(ten_parts) == 2:
                            ten = 10
                            one = korean_digits.get(ten_parts[1].strip(), 0)
                            return hundred + ten + one
                        else:
                            return hundred + 10
                    else:
                        one = korean_digits.get(rest_part, 0)
                        return hundred + one
            elif '십' in before_man:
                # 십 단위
                parts = before_man.split('십')
                if len(parts) == 2:
                    ten = 10
                    one = korean_digits.get(parts[1].strip(), 0)
                    return ten + one
                else:
                    return 10
            else:
                # 일의 자리만
                return korean_digits.get(before_man, 0)

        return None


if __name__ == "__main__":
    # 테스트
    test_text = """소재지: 대구 중구 삼덕동2가 122
보증금: 2,000만원
월세: 150만원
전용면적: 44.43㎡ (13.4평)
해당층/총층: 1층 / 5층
중개대상물 종류: 제1종 근린생활시설
화장실: 1개
주차: 가능
방향: 북동향
사용승인일: 1996.02.15"""

    parser = NaverPropertyParser()
    result = parser.parse(test_text)

    print("파싱 결과:")
    for key, value in result.items():
        print(f"{key}: {value}")
