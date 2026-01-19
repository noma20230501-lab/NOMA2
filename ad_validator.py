"""
네이버 부동산 광고 필수표시사항 검증 모듈
"""
import re
from typing import Dict, List, Tuple


class AdValidator:
    """광고 필수표시사항 검증 클래스"""

    # 필수표시사항 항목 (순서대로)
    REQUIRED_ITEMS = [
        "소재지",
        "전용면적",
        "보증금/월세",
        "중개대상물 종류",
        "거래형태",
        "총층수",
        "해당 층",
        "입주 가능일",
        "사용승인일",
        "화장실 형태",
        "주차 가능 여부",
        "방향",
        "건축물대장상 위반 건축물",
    ]

    # 조건부 필수 항목
    CONDITIONAL_ITEMS = [
        "미등기 건물"
    ]

    def __init__(self):
        pass

    def validate(self, ad_text: str) -> Dict:
        """
        광고 텍스트를 검증

        Args:
            ad_text: 네이버 뱅크 광고 텍스트 (전체 복사)

        Returns:
            {
                'success': bool,  # 전체 검증 통과 여부
                'valid_items': List[Dict],  # 정확한 항목들
                'missing_items': List[str],  # 누락된 항목들
                'format_errors': List[Dict],  # 형식 오류 항목들
                'total_items': int,  # 전체 항목 수
                'valid_count': int,  # 정확한 항목 수
                'missing_count': int,  # 누락된 항목 수
                'error_count': int,  # 오류 항목 수
            }
        """
        result = {
            'success': False,
            'valid_items': [],
            'missing_items': [],
            'format_errors': [],
            'total_items': len(self.REQUIRED_ITEMS),
            'valid_count': 0,
            'missing_count': 0,
            'error_count': 0,
        }

        # 각 항목 검증
        for item_name in self.REQUIRED_ITEMS:
            validation = self._validate_item(item_name, ad_text)

            if validation['status'] == 'valid':
                result['valid_items'].append({
                    'name': item_name,
                    'value': validation['value'],
                    'message': validation.get('message', '정확합니다')
                })
                result['valid_count'] += 1
            elif validation['status'] == 'missing':
                result['missing_items'].append(item_name)
                result['missing_count'] += 1
            elif validation['status'] == 'error':
                result['format_errors'].append({
                    'name': item_name,
                    'value': validation.get('value', ''),
                    'message': validation.get('message', '형식 오류')
                })
                result['error_count'] += 1

        # 조건부 항목 확인 (미등기 건물)
        if '미등기 건물' in ad_text or '미등기' in ad_text:
            unregistered_validation = self._validate_item('미등기 건물', ad_text)
            if unregistered_validation['status'] == 'valid':
                result['valid_items'].append({
                    'name': '미등기 건물',
                    'value': unregistered_validation['value'],
                    'message': '조건부 필수항목 포함'
                })
                result['valid_count'] += 1

        # 전체 검증 성공 여부 (누락/오류 없음)
        result['success'] = (result['missing_count'] ==
                             0 and result['error_count'] == 0)

        return result

    def _validate_item(self, item_name: str, ad_text: str) -> Dict:
        """
        개별 항목 검증

        Returns:
            {
                'status': 'valid' | 'missing' | 'error',
                'value': str,  # 추출된 값
                'message': str  # 상세 메시지
            }
        """
        # 항목별 검증 함수 매핑
        validators = {
            "소재지": self._validate_address,
            "전용면적": self._validate_area,
            "보증금/월세": self._validate_deposit_rent,
            "중개대상물 종류": self._validate_property_type,
            "거래형태": self._validate_transaction_type,
            "총층수": self._validate_total_floors,
            "해당 층": self._validate_floor,
            "입주 가능일": self._validate_move_in_date,
            "사용승인일": self._validate_approval_date,
            "화장실 형태": self._validate_bathroom,
            "주차 가능 여부": self._validate_parking,
            "방향": self._validate_direction,
            "건축물대장상 위반 건축물": self._validate_illegal_building,
            "미등기 건물": self._validate_unregistered,
        }

        validator_func = validators.get(item_name)
        if validator_func:
            return validator_func(ad_text)
        else:
            return {'status': 'error', 'value': '', 'message': '검증 함수 없음'}

    def _extract_value(self, ad_text: str, item_name: str) -> str:
        """항목명 뒤의 값 추출"""
        # "• 항목명: 값" 형식에서 값 추출
        pattern = rf'•\s*{re.escape(item_name)}\s*[:：]\s*(.+?)(?=\n•|\n\n|$)'
        match = re.search(pattern, ad_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _validate_address(self, ad_text: str) -> Dict:
        """소재지 검증"""
        value = self._extract_value(ad_text, "소재지")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '소재지가 입력되지 않았습니다'}

        # "대구" 포함 확인
        if '대구' not in value:
            return {
                'status': 'error',
                'value': value,
                'message': '"대구"가 포함되어야 합니다'}

        # 번지수 확인 (숫자-숫자 또는 숫자)
        if not re.search(r'\d+(-\d+)?', value):
            return {
                'status': 'error',
                'value': value,
                'message': '번지수가 포함되어야 합니다'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_area(self, ad_text: str) -> Dict:
        """전용면적 검증"""
        value = self._extract_value(ad_text, "전용면적")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '전용면적이 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # m² 또는 ㎡ 포함 확인
        if 'm2' not in value.lower() and '㎡' not in value:
            return {
                'status': 'error',
                'value': value,
                'message': '면적 단위(㎡)가 포함되어야 합니다'}

        # 숫자 확인
        if not re.search(r'\d+\.?\d*', value):
            return {
                'status': 'error',
                'value': value,
                'message': '면적 수치가 포함되어야 합니다'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_deposit_rent(self, ad_text: str) -> Dict:
        """보증금/월세 검증"""
        value = self._extract_value(ad_text, "보증금/월세")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '보증금/월세가 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # "만 원" 포함 확인
        if '만 원' not in value and '만원' not in value:
            return {
                'status': 'error',
                'value': value,
                'message': '"만 원" 단위가 포함되어야 합니다'}

        # 숫자 확인
        if not re.search(r'\d+', value):
            return {
                'status': 'error',
                'value': value,
                'message': '금액이 포함되어야 합니다'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_property_type(self, ad_text: str) -> Dict:
        """중개대상물 종류 검증"""
        value = self._extract_value(ad_text, "중개대상물 종류")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '중개대상물 종류가 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # 유효한 종류 목록
        valid_types = ['제1종 근린생활시설', '제2종 근린생활시설', '근린생활시설',
                       '업무시설', '판매시설', '공동주택', '단독주택', '다세대주택',
                       '다가구주택', '연립주택', '오피스텔']

        # 하나라도 포함되어 있는지 확인
        if not any(vt in value for vt in valid_types):
            return {
                'status': 'error',
                'value': value,
                'message': '유효한 건축물 용도가 아닙니다'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_transaction_type(self, ad_text: str) -> Dict:
        """거래형태 검증"""
        value = self._extract_value(ad_text, "거래형태")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '거래형태가 입력되지 않았습니다'}

        # "임대차계약"이 포함되어야 함
        if '임대차계약' not in value:
            return {
                'status': 'error',
                'value': value,
                'message': '"임대차계약"이 포함되어야 합니다'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_total_floors(self, ad_text: str) -> Dict:
        """총층수 검증"""
        value = self._extract_value(ad_text, "총층수")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '총층수가 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # 숫자와 "층" 확인
        if not re.search(r'\d+\s*층', value):
            return {
                'status': 'error',
                'value': value,
                'message': '층수가 올바르지 않습니다 (예: 5층)'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_floor(self, ad_text: str) -> Dict:
        """해당 층 검증"""
        value = self._extract_value(ad_text, "해당 층")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '해당 층이 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # 지상, 지하, 숫자층 확인
        if not (re.search(r'\d+\s*층', value)
                or '지하' in value or '지상' in value):
            return {
                'status': 'error',
                'value': value,
                'message': '층수가 올바르지 않습니다'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_move_in_date(self, ad_text: str) -> Dict:
        """입주 가능일 검증"""
        value = self._extract_value(ad_text, "입주 가능일")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '입주 가능일이 입력되지 않았습니다'}

        # "즉시" 또는 날짜 형식
        if '즉시' in value or re.search(r'\d{4}[년.-]\d{1,2}[월.-]\d{1,2}', value):
            return {'status': 'valid', 'value': value, 'message': '정확합니다'}

        return {'status': 'error', 'value': value,
                'message': '"즉시 입주" 또는 날짜(YYYY-MM-DD)가 필요합니다'}

    def _validate_approval_date(self, ad_text: str) -> Dict:
        """사용승인일 검증"""
        value = self._extract_value(ad_text, "사용승인일")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '사용승인일이 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # 날짜 형식 확인 (YYYY-MM-DD 또는 YYYY.MM.DD 또는 YYYY년MM월DD일)
        if not re.search(r'\d{4}[년.-]\d{1,2}[월.-]\d{1,2}', value):
            return {'status': 'error', 'value': value,
                    'message': '날짜 형식이 올바르지 않습니다 (예: 2020-01-01)'}

        return {'status': 'valid', 'value': value, 'message': '정확합니다'}

    def _validate_bathroom(self, ad_text: str) -> Dict:
        """화장실 형태 검증"""
        value = self._extract_value(ad_text, "화장실 형태")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '화장실 형태가 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value or '확인 필요' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # 숫자 + "개" 또는 특수 표현 확인
        if re.search(r'\d+\s*개', value) or '남녀별도' in value or '각' in value:
            return {'status': 'valid', 'value': value, 'message': '정확합니다'}

        return {'status': 'error', 'value': value,
                'message': '개수 또는 형태가 명시되어야 합니다 (예: 2개)'}

    def _validate_parking(self, ad_text: str) -> Dict:
        """주차 가능 여부 검증"""
        value = self._extract_value(ad_text, "주차 가능 여부")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '주차 가능 여부가 입력되지 않았습니다'}

        # "가능" 또는 "불가" 또는 "확인요망"
        if any(
            keyword in value for keyword in [
                '가능',
                '불가',
                '없음',
                '확인요망',
                '주차']):
            return {'status': 'valid', 'value': value, 'message': '정확합니다'}

        return {'status': 'error', 'value': value,
                'message': '"가능", "불가", "없음" 중 하나가 포함되어야 합니다'}

    def _validate_direction(self, ad_text: str) -> Dict:
        """방향 검증"""
        value = self._extract_value(ad_text, "방향")
        if not value:
            return {
                'status': 'missing',
                'value': '',
                'message': '방향이 입력되지 않았습니다'}

        # "확인요망"은 허용
        if '확인요망' in value:
            return {'status': 'valid', 'value': value, 'message': '확인요망으로 표시됨'}

        # 방향 키워드 확인
        directions = [
            '동',
            '서',
            '남',
            '북',
            '남동',
            '남서',
            '북동',
            '북서',
            '동향',
            '서향',
            '남향',
            '북향']
        if any(d in value for d in directions):
            return {'status': 'valid', 'value': value, 'message': '정확합니다'}

        return {
            'status': 'error',
            'value': value,
            'message': '방향이 명시되어야 합니다 (예: 남향)'}

    def _validate_illegal_building(self, ad_text: str) -> Dict:
        """건축물대장상 위반 건축물 검증"""
        value = self._extract_value(ad_text, "건축물대장상 위반 건축물")
        if not value:
            return {'status': 'missing', 'value': '',
                    'message': '건축물대장상 위반 건축물이 입력되지 않았습니다'}

        # "해당없음", "불법건축물", "확인요망" 중 하나
        if any(
            keyword in value for keyword in [
                '해당없음',
                '해당 없음',
                '불법건축물',
                '불법 건축물',
                '확인요망']):
            return {'status': 'valid', 'value': value, 'message': '정확합니다'}

        return {'status': 'error', 'value': value,
                'message': '"해당없음", "불법건축물", "확인요망" 중 하나가 필요합니다'}

    def _validate_unregistered(self, ad_text: str) -> Dict:
        """미등기 건물 검증 (조건부)"""
        value = self._extract_value(ad_text, "미등기 건물")
        if not value:
            # 조건부 항목이므로 없어도 됨
            return {
                'status': 'missing',
                'value': '',
                'message': '미등기 건물 항목 없음 (조건부 항목)'}

        return {'status': 'valid', 'value': value, 'message': '미등기 건물 표시됨'}
