"""
네이버 부동산뱅크 페이지 파서
Ctrl+A로 복사한 텍스트에서 필수표시사항 추출
"""
import re
from typing import Dict, Optional


class NaverBankParser:
    """네이버 부동산뱅크 페이지 파서"""

    def parse(self, text: str) -> Dict:
        """
        네이버 부동산뱅크 페이지 텍스트 파싱

        Args:
            text: Ctrl+A로 복사한 전체 텍스트

        Returns:
            {
                'address': str,  # 소재지
                'contract_area': str,  # 계약면적
                'exclusive_area': str,  # 전용면적
                'deposit': str,  # 보증금
                'rent': str,  # 월세
                'property_type': str,  # 건축물용도
                'transaction_type': str,  # 거래종류
                'total_floors': str,  # 총층수
                'floor': str,  # 해당층
                'move_in_date': str,  # 입주가능일
                'approval_date': str,  # 사용승인일
                'bathroom_count': str,  # 화장실수
                'parking_count': str,  # 총 주차대수
                'direction': str,  # 방향
                'illegal_building': str,  # 위반건축물여부
            }
        """
        result = {
            'address': None,
            'contract_area': None,
            'exclusive_area': None,
            'deposit': None,
            'rent': None,
            'property_type': None,
            'transaction_type': None,
            'total_floors': None,
            'floor': None,
            'move_in_date': None,
            'approval_date': None,
            'bathroom_count': None,
            'parking_count': None,
            'direction': None,
            'illegal_building': None,
        }

        # 1. 소재지 파싱
        result['address'] = self._parse_address(text)

        # 2. 계약면적 / 전용면적 파싱
        result['contract_area'], result['exclusive_area'] = self._parse_areas(
            text)

        # 3. 보증금/월세 파싱
        result['deposit'], result['rent'] = self._parse_deposit_rent(text)

        # 4. 건축물용도 파싱
        result['property_type'] = self._parse_property_type(text)

        # 5. 거래종류 파싱
        result['transaction_type'] = self._parse_transaction_type(text)

        # 6. 층수 파싱
        result['floor'], result['total_floors'] = self._parse_floors(text)

        # 7. 입주가능일 파싱
        result['move_in_date'] = self._parse_move_in_date(text)

        # 8. 사용승인일 파싱
        result['approval_date'] = self._parse_approval_date(text)

        # 9. 화장실수 파싱
        result['bathroom_count'] = self._parse_bathroom_count(text)

        # 10. 주차대수 파싱
        result['parking_count'] = self._parse_parking_count(text)

        # 11. 방향 파싱
        result['direction'] = self._parse_direction(text)

        # 12. 위반건축물여부 파싱
        result['illegal_building'] = self._parse_illegal_building(text)

        return result

    def _parse_address(self, text: str) -> Optional[str]:
        """소재지 파싱: 대구 중구 대봉동 741-10"""
        # 방법 1: 상세보기 페이지 - "소재지" 다음에 바로 주소
        detail_match = re.search(
            r'소재지\s+([가-힣]+구)\s+([가-힣0-9]+동[0-9]*가?)\s+(\d+)-(\d+)', text)
        if detail_match:
            gu = detail_match.group(1)
            dong = detail_match.group(2)
            bun = detail_match.group(3)
            ji = detail_match.group(4)
            return f"대구 {gu} {dong} {bun}-{ji}"

        # 방법 2: 매물 등록 페이지 - "필수소재지" 섹션
        # (디버깅은 필요시 주석 해제)
        # if '필수소재지' in text:
        #     sojaegi_idx = text.find('필수소재지')
        #     debug_text = text[sojaegi_idx:sojaegi_idx+500]
        #     print(f"🔍 [주소 파싱 디버그] 필수소재지 이후 텍스트:\n{debug_text}\n")

        # "필수소재지" 다음에 "대구" 찾기
        addr_section_match = re.search(r'필수소재지.*?대구', text, re.DOTALL)
        if addr_section_match:
            # "필수소재지" 이후 텍스트
            after_sojaegi = text[addr_section_match.start():]

            # "필수주소" 섹션에서 번지 추출
            # "필수주소"와 "번지" 사이의 텍스트 추출
            addr_match = re.search(r'필수주소(.*?)번지', after_sojaegi, re.DOTALL)

            bun = None
            ji = None

            if addr_match:
                between_bunji = addr_match.group(1)  # "필수주소"와 "번지" 사이

                # 모든 숫자 추출 (3~4자리와 1~4자리)
                numbers = re.findall(r'\d+', between_bunji)

                # 전화번호 제외
                numbers = [
                    n for n in numbers if n not in [
                        '010',
                        '070',
                        '050',
                        '031',
                        '02',
                        '051',
                        '053',
                        '032',
                        '042',
                        '062',
                        '052',
                        '044',
                        '063',
                        '061',
                        '054',
                        '055',
                        '064',
                        '043',
                        '041',
                        '033']]

                # 번지 추출
                if len(numbers) >= 1:
                    # 첫 번째 숫자를 번지로 사용 (1~4자리)
                    if 1 <= len(numbers[0]) <= 4:
                        bun = numbers[0]
                        # 두 번째 숫자가 있고 1~4자리면 지번
                        if len(numbers) >= 2 and 1 <= len(numbers[1]) <= 4:
                            ji = numbers[1]
                        else:
                            ji = "0"  # 지번 없음

            if bun and ji:

                # "필수소재지"와 "필수주소" 사이에서 구/동 추출
                between_text = after_sojaegi[:addr_match.start(
                )] if addr_match else after_sojaegi[:200]

                # 구 추출: 탭이나 공백으로 구분
                gu_match = re.search(
                    r'대구[\s\t]+(중구|동구|서구|남구|북구|수성구|달서구|달성군)', between_text)
                gu = gu_match.group(1) if gu_match else ''

                # 동 추출: 구 다음에 오는 동 (탭/공백/줄바꿈 허용)
                if gu:
                    dong_match = re.search(
                        rf'{gu}[\s\t]+([가-힣0-9]+동[0-9]*가?)', between_text)
                    dong = dong_match.group(1) if dong_match else ''
                else:
                    # 구를 못 찾았으면 "대구" 다음에서 동 찾기
                    dong_match = re.search(
                        r'대구[\s\t]+([가-힣0-9]+동[0-9]*가?)', between_text)
                    dong = dong_match.group(1) if dong_match else ''

                # 최종 주소 조합 (지번이 0이면 생략)
                if ji == "0" or ji == 0:
                    # 지번 없음
                    if gu and dong:
                        return f"대구 {gu} {dong} {bun}"
                    elif dong:
                        return f"대구 {dong} {bun}"
                    else:
                        return f"대구 {bun}"
                else:
                    # 지번 있음
                    if gu and dong:
                        return f"대구 {gu} {dong} {bun}-{ji}"
                    elif dong:
                        return f"대구 {dong} {bun}-{ji}"
                    else:
                        return f"대구 {bun}-{ji}"

        return None

    def _parse_areas(self, text: str) -> tuple:
        """계약면적 / 전용면적 파싱"""
        contract_area = None
        exclusive_area = None

        # 계약면적 찾기
        contract_match = re.search(r'필수\s*계약면적\s+([0-9.]+)\s*㎡', text)
        if contract_match:
            contract_area = f"{contract_match.group(1)}m2"

        # 전용면적 찾기
        exclusive_match = re.search(r'필수\s*전용면적\s+([0-9.]+)\s*㎡', text)
        if exclusive_match:
            exclusive_area = f"{exclusive_match.group(1)}m2"

        return contract_area, exclusive_area

    def _parse_deposit_rent(self, text: str) -> tuple:
        """보증금/월세 파싱 (쉼표 제거)"""
        deposit = None
        rent = None

        # 월세보증금과 월세금액 찾기
        deposit_match = re.search(r'월세보증금\s+([0-9,]+)\s*만원', text)
        if deposit_match:
            # 쉼표 제거
            deposit = deposit_match.group(1).replace(',', '')

        rent_match = re.search(r'월세금액\s+([0-9,]+)\s*만원', text)
        if rent_match:
            # 쉼표 제거
            rent = rent_match.group(1).replace(',', '')

        return deposit, rent

    def _parse_property_type(self, text: str) -> Optional[str]:
        """건축물용도 파싱"""
        # "필수건축물용도" 다음에 나오는 용도 찾기
        match = re.search(r'필수건축물용도\s+([^\n]+)', text)
        if match:
            prop_type = match.group(1).strip()
            # 앞뒤 공백과 불필요한 문자 제거
            prop_type = re.sub(r'\s+', '', prop_type)
            return prop_type

        return None

    def _parse_transaction_type(self, text: str) -> Optional[str]:
        """거래종류 파싱 - 항상 고정값 반환"""
        # 항상 "월세(직접 확인하세요)" 반환
        return "월세(직접 확인하세요)"

    def _parse_floors(self, text: str) -> tuple:
        """해당층 / 총층수 파싱"""
        floor = None
        total_floors = None

        # "필수 층" 섹션에서 해당층과 총층 찾기
        # ✅ "1층 일부" 같은 형식도 지원하도록 개선
        floor_match = re.search(
            r'필수\s*층\s*해당층\s+([0-9-]+)\s*층(?:\s*일부)?\s*/?\s*(?:총층\s+([0-9]+)\s*층)?', text)
        if floor_match:
            floor_num = floor_match.group(1)
            total_num = floor_match.group(2) if floor_match.group(2) else None

            # 지하층 처리
            if floor_num.startswith('-'):
                floor = f"지하{floor_num[1:]}층"
            else:
                floor = f"{floor_num}층"

            if total_num:
                total_floors = f"{total_num}층"

        return floor, total_floors

    def _parse_move_in_date(self, text: str) -> Optional[str]:
        """입주가능일 파싱"""
        # "필수입주가능일" 섹션에서 찾기
        match = re.search(r'필수입주가능일\s+(즉시입주|협의가능)', text)
        if match:
            return match.group(1)

        # 날짜 형식 찾기
        date_match = re.search(
            r'필수입주가능일.*?(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일',
            text,
            re.DOTALL)
        if date_match:
            return f"{
                date_match.group(1)}년 {
                date_match.group(2)}월 {
                date_match.group(3)}일"

        return "즉시입주"  # 기본값

    def _parse_approval_date(self, text: str) -> Optional[str]:
        """사용승인일 파싱"""
        # "필수 건축물일자" 섹션에서 찾기
        match = re.search(
            r'필수\s*건축물일자.*?(\d{4})\s*년\s+(\d{1,2})\s*월\s+(\d{1,2})\s*일',
            text,
            re.DOTALL)
        if match:
            year = match.group(1)
            month = match.group(2)
            day = match.group(3)
            return f"{year}년 {month}월 {day}일"

        return None

    def _parse_bathroom_count(self, text: str) -> Optional[str]:
        """화장실수 파싱"""
        # "필수 욕실(화장실)수" 섹션에서 찾기
        match = re.search(r'필수\s*욕실\(화장실\)수\s+(\d+)\s*개', text)
        if match:
            return f"{match.group(1)}개"

        return None

    def _parse_parking_count(self, text: str) -> Optional[str]:
        """총 주차대수 파싱"""
        # "필수 총 주차대수" 섹션에서 찾기
        match = re.search(r'필수\s*총\s*주차대수\s+(\d+)\s*대', text)
        if match:
            return f"{match.group(1)}대"

        return None

    def _parse_direction(self, text: str) -> Optional[str]:
        """방향 파싱"""
        # "필수 방향" 섹션에서 찾기
        match = re.search(r'필수\s*방향.*?(동|서|남|북|동남|동북|서남|서북)', text, re.DOTALL)
        if match:
            direction = match.group(1)
            # "향" 붙이기
            if not direction.endswith('향'):
                direction += '향'
            return direction

        return None

    def _parse_illegal_building(self, text: str) -> Optional[str]:
        """위반건축물여부 파싱"""
        # "필수 위반 건축물 여부" 섹션에서 찾기
        # 다양한 표현 지원: 해당없음, 해당 없음, 없음, 해당됨, 해당, 있음
        match = re.search(
            r'필수\s*위반\s*건축물\s*여부\s+(해당\s*없음|해당없음|없음|해당\s*됨|해당됨|있음)', text)
        if match:
            value = match.group(1).replace(' ', '')  # 공백 제거
            # 정규화
            if value in ['해당없음', '없음']:
                return '해당없음'
            elif value in ['해당됨', '해당', '있음']:
                return '해당됨'
            return value

        return None

    def format_result(self, parsed_data: Dict) -> str:
        """
        파싱된 데이터를 보기 좋게 포맷팅

        Returns:
            포맷팅된 텍스트
        """
        lines = []

        if parsed_data['address']:
            lines.append(f"✅ 소재지 : {parsed_data['address']}")

        # ✅ 보증금/월세를 계약면적보다 먼저 표시
        if parsed_data['deposit'] and parsed_data['rent']:
            lines.append(
                f"✅ 보증금/월세 : {parsed_data['deposit']}만원 / {parsed_data['rent']}만원")

        if parsed_data['contract_area'] and parsed_data['exclusive_area']:
            lines.append(
                f"✅ 계약면적 / 전용면적 : {parsed_data['contract_area']} / {parsed_data['exclusive_area']}")

        if parsed_data['property_type']:
            lines.append(f"✅ 중개대상물 종류(건축물용도) : {parsed_data['property_type']}")

        if parsed_data['transaction_type']:
            lines.append(f"✅ 거래형태(거래종류) : {parsed_data['transaction_type']}")

        if parsed_data['total_floors']:
            lines.append(f"✅ 총층수 : {parsed_data['total_floors']}")

        if parsed_data['floor']:
            lines.append(f"✅ 해당 층 : {parsed_data['floor']}")

        if parsed_data['move_in_date']:
            lines.append(f"✅ 입주 가능일 : {parsed_data['move_in_date']}")

        if parsed_data['approval_date']:
            lines.append(f"✅ 사용승인일 : {parsed_data['approval_date']}")

        if parsed_data['bathroom_count']:
            lines.append(
                f"✅ 화장실 수 (욕실(화장실)수) : {
                    parsed_data['bathroom_count']}")

        if parsed_data['parking_count']:
            lines.append(f"✅ 총 주차대수 : {parsed_data['parking_count']}")

        if parsed_data['direction']:
            lines.append(f"✅ 방향 : {parsed_data['direction']}")

        if parsed_data['illegal_building']:
            lines.append(
                f"✅ 건축물대장상 위반 건축물 (위반건축물여부) : {
                    parsed_data['illegal_building']}")

        return '\n'.join(lines)
