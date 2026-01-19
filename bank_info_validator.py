"""
네이버 부동산뱅크 정보 검증 모듈
파싱된 정보와 건축물대장을 비교하여 정확성 검증
"""
from typing import Dict, List, Optional
import re


class BankInfoValidator:
    """부동산뱅크 정보 검증 클래스"""

    def __init__(self, api_system):
        """
        Args:
            api_system: PropertyAdSystem 인스턴스
        """
        self.system = api_system  # ✅ 모드A 전체 시스템 저장
        self.api = api_system.api if hasattr(api_system, 'api') else api_system

    def validate(
            self,
            parsed_data: Dict,
            building_data: Dict,
            floor_result: Dict,
            area_result: Dict,
            kakao_data: Optional[Dict] = None,
            usage_judgment: Optional[Dict] = None) -> Dict:
        """
        파싱된 정보와 건축물대장 비교 (3-way 검증: 네이버뱅크 vs 건축물대장 vs 카톡)

        Returns:
            {
                'items': [
                    {
                        'name': str,  # 항목명
                        'status': 'correct' | 'warning' | 'error' | 'info',
                        'parsed_value': str,  # 네이버뱅크 입력값
                        'registry_value': str,  # 건축물대장 값
                        'kakao_value': str,  # 카톡 실제 매물 정보 (있는 경우)
                        'message': str  # 상세 메시지
                    }
                ],
                'summary': {
                    'correct': int,  # 정확한 항목 수
                    'warning': int,  # 주의 항목 수
                    'error': int,  # 오류 항목 수
                    'total': int  # 전체 항목 수
                }
            }
        """
        items = []

        # ✅ 네이버 뱅크 파싱 순서대로 정렬
        # 1. 소재지
        items.append(
            self._validate_address(
                parsed_data,
                building_data,
                kakao_data))

        # 2. 계약면적 / 전용면적
        items.append(
            self._validate_contract_area(
                parsed_data,
                floor_result,
                area_result,
                kakao_data))
        items.append(
            self._validate_exclusive_area(
                parsed_data,
                area_result,
                kakao_data))

        # 3. 보증금/월세
        if kakao_data:
            items.append(self._validate_deposit_rent(parsed_data, kakao_data))

        # 4. 중개대상물 종류(건축물용도)
        items.append(
            self._validate_property_type(
                parsed_data,
                floor_result,
                area_result,
                usage_judgment,
                kakao_data))  # ✅ 카톡 데이터 전달

        # 5. 총층수
        items.append(self._validate_total_floors(parsed_data, building_data))

        # 6. 해당 층
        items.append(
            self._validate_floor(
                parsed_data,
                floor_result,
                area_result,
                kakao_data))

        # 7. 사용승인일
        items.append(self._validate_approval_date(parsed_data, building_data))

        # 8. 화장실 수
        if kakao_data:
            items.append(self._validate_bathroom(parsed_data, kakao_data))

        # 9. 총 주차대수
        items.append(self._validate_parking(parsed_data, building_data))

        # 10. 방향
        if kakao_data:
            items.append(self._validate_direction(parsed_data, kakao_data))

        # 11. 위반건축물 (네이버 뱅크 또는 카톡 정보가 있으면 표시)
        items.append(self._validate_illegal(parsed_data, kakao_data))

        # 통계 계산
        summary = {
            'correct': sum(1 for item in items if item['status'] == 'correct'),
            'warning': sum(1 for item in items if item['status'] == 'warning'),
            'error': sum(1 for item in items if item['status'] == 'error'),
            'info': sum(1 for item in items if item['status'] == 'info'),
            'total': len(items)
        }

        return {
            'items': items,
            'summary': summary
        }

    def _validate_deposit_rent(
            self,
            parsed_data: Dict,
            kakao_data: Dict) -> Dict:
        """보증금/월세 비교 (부동산뱅크 vs 카톡 실제 매물, 숫자만 비교)"""
        bank_deposit = parsed_data.get('deposit', '')
        bank_rent = parsed_data.get('rent', '')

        kakao_deposit = kakao_data.get('deposit', '')
        kakao_rent = kakao_data.get('monthly_rent', '')

        kakao_display = f"{kakao_deposit}/{kakao_rent}" if (
            kakao_deposit and kakao_rent) else '-'

        if not bank_deposit or not bank_rent:
            return {
                'name': '보증금/월세',
                'status': 'error',
                'parsed_value': '(파싱 실패)',
                'registry_value': '-',
                'kakao_value': kakao_display,
                'message': '부동산뱅크 정보를 파싱하지 못했습니다'
            }

        if not kakao_deposit or not kakao_rent:
            return {
                'name': '보증금/월세',
                'status': 'info',
                'parsed_value': f"{bank_deposit}만원/{bank_rent}만원",
                'registry_value': '-',
                'kakao_value': '(카톡 정보 없음)',
                'message': '🚨 카톡 정보 필요: 실제 매물 가격 확인 불가'
            }

        # 숫자만 추출 (쉼표, "만원" 등 제거)
        bank_deposit_num = int(
            re.sub(
                r'[^\d]',
                '',
                str(bank_deposit))) if bank_deposit else 0
        bank_rent_num = int(
            re.sub(
                r'[^\d]',
                '',
                str(bank_rent))) if bank_rent else 0
        kakao_deposit_num = int(kakao_deposit) if kakao_deposit else 0
        kakao_rent_num = int(kakao_rent) if kakao_rent else 0

        if bank_deposit_num == kakao_deposit_num and bank_rent_num == kakao_rent_num:
            return {
                'name': '보증금/월세',
                'status': 'correct',
                'parsed_value': f"{bank_deposit_num}/{bank_rent_num}",
                'registry_value': '-',
                'kakao_value': kakao_display,
                'message': '✅ 카톡 실제 매물 정보와 일치합니다'
            }
        else:
            return {
                'name': '보증금/월세',
                'status': 'error',
                'parsed_value': f"{bank_deposit_num}/{bank_rent_num}",
                'registry_value': '-',
                'kakao_value': kakao_display,
                'message': f'❌ 금액 불일치 (보증금 차이: {abs(bank_deposit_num - kakao_deposit_num)}만원, 월세 차이: {abs(bank_rent_num - kakao_rent_num)}만원)'
            }

    def _validate_bathroom(self, parsed_data: Dict, kakao_data: Dict) -> Dict:
        """화장실 수 비교 (부동산뱅크 vs 카톡)"""
        bank_bathroom = parsed_data.get('bathroom_count', '')
        kakao_bathroom = kakao_data.get('bathroom_count', '')

        # ✅ 카톡 화장실 수 표시
        kakao_value_str = f"{kakao_bathroom}개" if kakao_bathroom else '-'

        if not bank_bathroom:
            return {
                'name': '화장실 수',
                'status': 'error',
                'parsed_value': '(파싱 실패)',
                'registry_value': '-',
                'kakao_value': kakao_value_str,
                'message': '부동산뱅크 정보를 파싱하지 못했습니다'}

        if not kakao_bathroom:
            return {
                'name': '화장실 수',
                'status': 'info',
                'parsed_value': bank_bathroom,
                'registry_value': '-',
                'kakao_value': '-',
                'message': '카톡 정보와 비교할 수 없습니다'
            }

        # 숫자 추출
        bank_num = int(
            re.search(
                r'\d+',
                bank_bathroom).group()) if re.search(
            r'\d+',
            bank_bathroom) else 0
        kakao_num = int(kakao_bathroom) if str(kakao_bathroom).isdigit() else 0

        if bank_num == kakao_num:
            return {
                'name': '화장실 수',
                'status': 'correct',
                'parsed_value': bank_bathroom,
                'registry_value': '-',
                'kakao_value': kakao_value_str,
                'message': '카톡 정보와 일치합니다'
            }
        else:
            return {
                'name': '화장실 수',
                'status': 'error',
                'parsed_value': bank_bathroom,
                'registry_value': '-',
                'kakao_value': kakao_value_str,
                'message': f'개수가 다릅니다 (차이: {abs(bank_num - kakao_num)}개)'
            }

    def _validate_direction(self, parsed_data: Dict, kakao_data: Dict) -> Dict:
        """방향 비교 (부동산뱅크 vs 카톡)"""
        bank_direction = parsed_data.get('direction', '')
        kakao_direction = kakao_data.get('direction', '')

        # ✅ 카톡 방향 표시
        kakao_value_str = kakao_direction if kakao_direction else '-'

        if not bank_direction:
            return {
                'name': '방향',
                'status': 'error',
                'parsed_value': '(파싱 실패)',
                'registry_value': '-',
                'kakao_value': kakao_value_str,
                'message': '부동산뱅크 정보를 파싱하지 못했습니다'}

        if not kakao_direction:
            return {
                'name': '방향',
                'status': 'info',
                'parsed_value': bank_direction,
                'registry_value': '-',
                'kakao_value': '-',
                'message': '카톡 정보와 비교할 수 없습니다'
            }

        # 방향 추출 (동, 서, 남, 북 등)
        bank_dir = re.sub(r'향', '', bank_direction)
        kakao_dir = re.sub(r'향', '', kakao_direction)

        if bank_dir == kakao_dir:
            return {
                'name': '방향',
                'status': 'correct',
                'parsed_value': bank_direction,
                'registry_value': '-',
                'kakao_value': kakao_value_str,
                'message': '카톡 정보와 일치합니다'
            }
        else:
            return {
                'name': '방향',
                'status': 'error',
                'parsed_value': bank_direction,
                'registry_value': '-',
                'kakao_value': kakao_value_str,
                'message': '카톡 정보와 다릅니다'
            }

    def _validate_illegal(self, parsed_data: Dict, kakao_data: Dict) -> Dict:
        """위반건축물 여부 확인 (네이버 뱅크 vs 카톡 비교)"""
        # 네이버 뱅크 정보
        bank_illegal_str = parsed_data.get(
            'illegal_building')  # "해당없음" 또는 "해당됨"

        # 네이버 뱅크 정보를 boolean으로 변환
        bank_illegal = None
        if bank_illegal_str == "해당됨":
            bank_illegal = True
        elif bank_illegal_str == "해당없음":
            bank_illegal = False

        # 카톡 정보
        kakao_illegal = kakao_data.get('illegal') if kakao_data else None

        # 네이버 뱅크 표시값
        bank_display = '-'
        if bank_illegal is True:
            bank_display = '⚠️ 해당됨'
        elif bank_illegal is False:
            bank_display = '✅ 해당없음'

        # 카톡 표시값
        kakao_display = '-'
        if kakao_illegal is True:
            kakao_display = '⚠️ 위반건축물 O'
        elif kakao_illegal is False:
            kakao_display = '✅ 위반건축물 X'

        # 비교 로직
        # 1. 둘 다 정보가 있는 경우
        if bank_illegal is not None and kakao_illegal is not None:
            if bank_illegal == kakao_illegal:
                # 일치
                if bank_illegal is True:
                    return {
                        'name': '위반건축물',
                        'status': 'warning',
                        'parsed_value': bank_display,
                        'registry_value': '-',
                        'kakao_value': kakao_display,
                        'message': '⚠️ 위반건축물입니다 (일치)'
                    }
                else:
                    return {
                        'name': '위반건축물',
                        'status': 'correct',
                        'parsed_value': bank_display,
                        'registry_value': '-',
                        'kakao_value': kakao_display,
                        'message': '✅ 위반건축물 아님 (일치)'
                    }
            else:
                # 불일치
                return {
                    'name': '위반건축물',
                    'status': 'error',
                    'parsed_value': bank_display,
                    'registry_value': '-',
                    'kakao_value': kakao_display,
                    'message': '❌ 네이버 뱅크와 카톡 정보가 다릅니다'
                }

        # 2. 네이버 뱅크 정보만 있는 경우
        elif bank_illegal is not None:
            if bank_illegal is True:
                return {
                    'name': '위반건축물',
                    'status': 'warning',
                    'parsed_value': bank_display,
                    'registry_value': '-',
                    'kakao_value': kakao_display,
                    'message': '⚠️ 위반건축물입니다 (카톡 정보 없음)'
                }
            else:
                return {
                    'name': '위반건축물',
                    'status': 'correct',
                    'parsed_value': bank_display,
                    'registry_value': '-',
                    'kakao_value': kakao_display,
                    'message': '✅ 위반건축물 아님 (카톡 정보 없음)'
                }

        # 3. 카톡 정보만 있는 경우
        elif kakao_illegal is not None:
            if kakao_illegal is True:
                return {
                    'name': '위반건축물',
                    'status': 'warning',
                    'parsed_value': bank_display,
                    'registry_value': '-',
                    'kakao_value': kakao_display,
                    'message': '⚠️ 위반건축물입니다 (네이버 뱅크 정보 없음)'
                }
            else:
                return {
                    'name': '위반건축물',
                    'status': 'info',
                    'parsed_value': bank_display,
                    'registry_value': '-',
                    'kakao_value': kakao_display,
                    'message': 'ℹ️ 위반건축물 아님 (네이버 뱅크 정보 없음)'
                }

        # 4. 둘 다 정보가 없는 경우
        else:
            return {
                'name': '위반건축물',
                'status': 'info',
                'parsed_value': bank_display,
                'registry_value': '-',
                'kakao_value': kakao_display,
                'message': 'ℹ️ 정보 없음'
            }

    def _validate_address(
            self,
            parsed_data: Dict,
            building_data: Dict,
            kakao_data: Optional[Dict] = None) -> Dict:
        """소재지 비교 (대구 생략 허용)"""
        parsed_addr = parsed_data.get('address', '')
        registry_addr = building_data.get(
            'platPlc', '') or building_data.get(
            'newPlatPlc', '')
        kakao_addr = kakao_data.get('address', '') if kakao_data else ''

        if not parsed_addr:
            return {
                'name': '소재지',
                'status': 'error',
                'parsed_value': '(파싱 실패)',
                'registry_value': registry_addr,
                'kakao_value': kakao_addr if kakao_addr else '-',
                'message': '소재지를 파싱하지 못했습니다'
            }

        # "대구" 생략 허용 - 정규화
        parsed_addr_normalized = parsed_addr.replace(
            '대구광역시 ', '').replace('대구 ', '').strip()
        registry_addr_normalized = registry_addr.replace(
            '대구광역시 ', '').replace('대구 ', '').strip()
        kakao_addr_normalized = kakao_addr.replace(
            '대구광역시 ', '').replace(
            '대구 ', '').strip() if kakao_addr else ''

        # 주소에서 번지수만 추출해서 비교
        parsed_nums = re.findall(r'\d+(?:-\d+)?', parsed_addr_normalized)
        registry_nums = re.findall(r'\d+(?:-\d+)?', registry_addr_normalized)
        kakao_nums = re.findall(
            r'\d+(?:-\d+)?',
            kakao_addr_normalized) if kakao_addr_normalized else []

        # 비교
        registry_match = parsed_nums and registry_nums and parsed_nums[-1] == registry_nums[-1]
        kakao_match = parsed_nums and kakao_nums and parsed_nums[-1] == kakao_nums[-1]

        # 카톡 정보가 있는 경우: 3-way 비교 (뱅크 == 대장 == 카톡)
        if kakao_addr:
            if registry_match and kakao_match:
                # 세 개 모두 일치
                return {
                    'name': '소재지',
                    'status': 'correct',
                    'parsed_value': parsed_addr,
                    'registry_value': registry_addr,
                    'kakao_value': kakao_addr,
                    'message': '✅ 건축물대장, 카톡 모두 일치'
                }
            elif registry_match:
                # 뱅크 == 대장, 카톡 불일치
                return {
                    'name': '소재지',
                    'status': 'error',
                    'parsed_value': parsed_addr,
                    'registry_value': registry_addr,
                    'kakao_value': kakao_addr,
                    'message': f'❌ 카톡 주소 불일치 (뱅크: {parsed_nums[-1] if parsed_nums else "?"}, 카톡: {kakao_nums[-1] if kakao_nums else "?"})'
                }
            elif kakao_match:
                # 뱅크 == 카톡, 대장 불일치
                return {
                    'name': '소재지',
                    'status': 'error',
                    'parsed_value': parsed_addr,
                    'registry_value': registry_addr,
                    'kakao_value': kakao_addr,
                    'message': f'❌ 건축물대장 주소 불일치 (뱅크: {parsed_nums[-1] if parsed_nums else "?"}, 대장: {registry_nums[-1] if registry_nums else "?"})'
                }
            else:
                # 세 개 모두 불일치
                return {
                    'name': '소재지',
                    'status': 'error',
                    'parsed_value': parsed_addr,
                    'registry_value': registry_addr,
                    'kakao_value': kakao_addr,
                    'message': '❌ 주소가 모두 다릅니다'
                }
        else:
            # 카톡 정보 없음: 뱅크 vs 대장만 비교
            if registry_match:
                return {
                    'name': '소재지',
                    'status': 'correct',
                    'parsed_value': parsed_addr,
                    'registry_value': registry_addr,
                    'kakao_value': '-',
                    'message': '✅ 건축물대장과 일치'
                }
            else:
                return {
                    'name': '소재지',
                    'status': 'warning',
                    'parsed_value': parsed_addr,
                    'registry_value': registry_addr,
                    'kakao_value': '-',
                    'message': '⚠️ 번지수를 확인해주세요'
                }

    def _validate_contract_area(
            self,
            parsed_data: Dict,
            floor_result: Dict,
            area_result: Dict,
            kakao_data: Optional[Dict] = None) -> Dict:
        """계약면적 비교 (해당층 정보 필요)"""
        parsed_area_str = parsed_data.get('contract_area', '')
        parsed_floor_str = parsed_data.get('floor', '')

        # 카톡 계약면적 (실제 면적)
        kakao_area_str = f"{
            kakao_data.get(
                'actual_area_m2',
                '')}㎡" if kakao_data and kakao_data.get('actual_area_m2') else '-'

        if not parsed_area_str:
            return {
                'name': '계약면적',
                'status': 'info',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': kakao_area_str,
                'message': '계약면적 정보 없음'
            }

        # 해당층 정보 확인
        if not parsed_floor_str:
            return {
                'name': '계약면적',
                'status': 'warning',
                'parsed_value': parsed_area_str,
                'registry_value': '-',
                'kakao_value': kakao_area_str,
                'message': '⚠️ 해당층 정보가 없어 검증할 수 없습니다'
            }

        # 파싱된 면적 추출
        parsed_area_match = re.search(r'([0-9.]+)', parsed_area_str)
        if not parsed_area_match:
            return {
                'name': '계약면적',
                'status': 'error',
                'parsed_value': parsed_area_str,
                'registry_value': '-',
                'kakao_value': kakao_area_str,
                'message': '❌ 면적 형식 오류'
            }

        parsed_area = float(parsed_area_match.group(1))

        # ✅ 모드A의 층 파싱 로직 사용
        parsed_floor = self.system.parse_floor_string(parsed_floor_str)
        print(
            f"🔍 [계약면적 검증] parsed_floor_str='{parsed_floor_str}' → parsed_floor={parsed_floor}")

        if parsed_floor is None:
            return {
                'name': '계약면적',
                'status': 'warning',
                'parsed_value': f"{parsed_area}㎡",
                'registry_value': '(층 파싱 실패)',
                'kakao_value': kakao_area_str,
                'message': f'⚠️ 층수 형식 오류: "{parsed_floor_str}"'
            }

        # 해당층의 면적 찾기 (area_result 또는 floor_result)
        registry_area = None
        debug_info = []  # ✅ 디버그 정보 수집

        # area_result에서 해당층 찾기 (전유부) - ✅ 모드A의 match_floor 사용
        if area_result and area_result.get(
                'success') and area_result.get('data'):
            debug_info.append(
                f"📊 area_result 데이터 수: {len(area_result.get('data', []))}")
            for area_info in area_result['data']:
                floor_no = str(area_info.get('flrNo', ''))
                expos = area_info.get('exposPubuseGbCdNm', '')
                area_val = area_info.get('area', 'N/A')
                debug_info.append(
                    f"  - flrNo='{floor_no}', expos='{expos}', area={area_val}")

                # ✅ 모드A 로직: 지하층은 음수, 지상층은 양수로 비교
                if floor_no and self.system.match_floor(
                        parsed_floor, floor_no):
                    if area_val and area_val != 'N/A':
                        try:
                            registry_area = float(str(area_val).strip())
                            debug_info.append(
                                f"✅ [계약면적] area_result에서 {parsed_floor}층 매칭 성공: {registry_area}㎡")
                            print(
                                f"🔍 [계약면적] area_result에서 {parsed_floor}층 매칭: {registry_area}㎡")
                            break
                        except BaseException as e:
                            debug_info.append(f"❌ area 값 변환 실패: {e}")

        # floor_result에서 해당층 찾기 - ✅ 모드A의 match_floor 사용
        if not registry_area and floor_result and floor_result.get(
                'success') and floor_result.get('data'):
            debug_info.append(
                f"📊 floor_result 데이터 수: {len(floor_result.get('data', []))}")
            for floor_info in floor_result['data']:
                floor_no_nm = str(floor_info.get('flrNoNm', ''))
                area_val = floor_info.get('area', 'N/A')

                # ✅ 디버그: match_floor 결과 확인
                match_result = self.system.match_floor(
                    parsed_floor, floor_no_nm) if floor_no_nm else False
                debug_info.append(
                    f"  - flrNoNm='{floor_no_nm}', area={area_val}, match_floor({parsed_floor}, '{floor_no_nm}')={match_result}")

                # ✅ 모드A 로직: 지하1층, 1층 정확히 구분
                if floor_no_nm and match_result:
                    if area_val and area_val != 'N/A':
                        try:
                            registry_area = float(str(area_val).strip())
                            debug_info.append(
                                f"✅ [계약면적] floor_result에서 {parsed_floor}층 매칭 성공: {registry_area}㎡")
                            print(
                                f"🔍 [계약면적] floor_result에서 {parsed_floor}층 매칭: {registry_area}㎡")
                            break
                        except BaseException as e:
                            debug_info.append(f"❌ area 값 변환 실패: {e}")

        if not registry_area:
            # ✅ 디버그 정보를 메시지에 포함
            debug_text = "\n".join(debug_info)
            return {
                'name': '계약면적',
                'status': 'warning',
                'parsed_value': f"{parsed_area}㎡ ({parsed_floor_str})",
                'registry_value': '(대장 정보 없음)',
                'kakao_value': kakao_area_str,
                'message': f'{parsed_floor_str}의 면적 정보를 건축물대장에서 찾을 수 없습니다',
                'debug_message': debug_text
            }

        # ✅ 먼저 면적 비교 (뱅크 vs 대장)
        diff = abs(parsed_area - registry_area)
        diff_ratio = diff / registry_area * 100

        # ✅ 카톡 층수와 비교 (면적 비교 후)
        kakao_floor_mismatch = False
        kakao_floor_display = None
        if kakao_data and kakao_data.get('floor') is not None:
            kakao_parsed_floor = kakao_data.get('floor')
            if kakao_parsed_floor != parsed_floor:
                kakao_floor_mismatch = True
                kakao_floor_display = f"지하{
                    abs(kakao_parsed_floor)}층" if kakao_parsed_floor < 0 else f"{kakao_parsed_floor}층"

        # 면적 차이와 층수 불일치를 모두 고려
        if kakao_floor_mismatch:
            # 층수는 다르지만 면적이 일치하는 경우
            if diff_ratio < 1:
                status = 'warning'
                message = f'⚠️ 뱅크({parsed_floor_str})와 카톡({kakao_floor_display}) 층수 불일치 (면적은 일치)'
            else:
                status = 'error'
                message = f'❌ 층수 불일치 + 면적 차이 (차이: {diff:.2f}㎡)'
        else:
            # 층수가 일치하는 경우 (또는 카톡 정보 없음)
            if diff_ratio < 1:
                # ✅ 카톡 계약면적이 없을 때 주의 표시
                if not kakao_data or not kakao_data.get('actual_area_m2'):
                    status = 'warning'
                    message = f'⚠️ 뱅크와 대장 일치 (카톡 정보 없음)'
                else:
                    status = 'correct'
                    message = f'{parsed_floor_str} 건축물대장과 일치합니다'
            elif diff_ratio < 5:
                status = 'warning'
                message = f'약간의 차이가 있습니다 (차이: {diff:.2f}㎡)'
            else:
                status = 'error'
                message = f'큰 차이가 있습니다 (차이: {diff:.2f}㎡)'

        return {
            'name': '계약면적',
            'status': status,
            'parsed_value': f"{parsed_area}㎡ ({parsed_floor_str})",
            'registry_value': f"{registry_area}㎡ ({parsed_floor_str})",
            'kakao_value': kakao_area_str,
            'message': message,
            'debug_message': "\n".join(debug_info)
        }

    def _validate_exclusive_area(
            self,
            parsed_data: Dict,
            area_result: Dict,
            kakao_data: Optional[Dict] = None) -> Dict:
        """전용면적 비교 (✅ 해당층 기반으로 검색)"""
        parsed_area_str = parsed_data.get('exclusive_area', '')
        parsed_floor_str = parsed_data.get('floor', '')  # ✅ 층 정보 추가

        # ✅ 카톡 전용면적 (area_m2가 전용면적임)
        kakao_area_str = f"{
            kakao_data.get(
                'area_m2',
                '')}㎡" if kakao_data and kakao_data.get('area_m2') else '-'

        if not parsed_area_str:
            return {
                'name': '전용면적',
                'status': 'info',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': kakao_area_str,
                'message': '전용면적 정보 없음'
            }

        # 파싱된 면적 추출
        parsed_area_match = re.search(r'([0-9.]+)', parsed_area_str)
        if not parsed_area_match:
            return {
                'name': '전용면적',
                'status': 'error',
                'parsed_value': parsed_area_str,
                'registry_value': '-',
                'kakao_value': kakao_area_str,
                'message': '면적 형식 오류'
            }

        parsed_area = float(parsed_area_match.group(1))

        # ✅ 전용면적은 대장에서 확인 불가 → 뱅크 vs 카톡만 비교
        # 카톡 전용면적 추출
        kakao_area = None
        if kakao_data and kakao_data.get('area_m2'):
            try:
                kakao_area = float(kakao_data.get('area_m2'))
            except BaseException:
                pass

        # 카톡 정보가 없으면 info 상태
        if kakao_area is None:
            return {
                'name': '전용면적',
                'status': 'info',
                'parsed_value': f"{parsed_area}㎡",
                'registry_value': '-',
                'kakao_value': kakao_area_str,
                'message': '카톡 정보 없음 (대장으로 전용면적 확인 불가)'
            }

        # 뱅크 vs 카톡 비교
        diff = abs(parsed_area - kakao_area)
        diff_ratio = diff / kakao_area * 100 if kakao_area > 0 else 0

        if diff_ratio < 1:
            status = 'correct'
            message = '뱅크와 카톡 정보 일치'
        elif diff_ratio < 5:
            status = 'warning'
            message = f'뱅크와 카톡 정보 약간 차이 (차이: {diff:.2f}㎡)'
        else:
            status = 'error'
            message = f'뱅크와 카톡 정보 불일치 (차이: {diff:.2f}㎡)'

        return {
            'name': '전용면적',
            'status': status,
            'parsed_value': f"{parsed_area}㎡",
            'registry_value': '-',
            'kakao_value': kakao_area_str,
            'message': message
        }

    def _validate_floor(
            self,
            parsed_data: Dict,
            floor_result: Dict,
            area_result: Dict,
            kakao_data: Optional[Dict] = None) -> Dict:
        """해당층 비교 (✅ 카톡 정보 포함)"""
        parsed_floor_str = parsed_data.get('floor', '')

        # ✅ 카톡 해당층
        kakao_floor_str = '-'
        if kakao_data:
            kakao_floor = kakao_data.get('floor')
            if kakao_floor:
                # 카톡 파서는 지하층을 음수로 저장
                if kakao_floor < 0:
                    kakao_floor_str = f"지하{abs(kakao_floor)}층"
                else:
                    kakao_floor_str = f"{kakao_floor}층"

        if not parsed_floor_str:
            return {
                'name': '해당 층',
                'status': 'error',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': kakao_floor_str,
                'message': '해당 층 정보 없음'
            }

        # ✅ 모드A의 층 파싱 로직 사용
        parsed_floor = self.system.parse_floor_string(parsed_floor_str)
        if parsed_floor is None:
            return {
                'name': '해당 층',
                'status': 'error',
                'parsed_value': parsed_floor_str,
                'registry_value': '-',
                'kakao_value': kakao_floor_str,
                'message': f'층수 형식 오류: "{parsed_floor_str}"'
            }

        # 건축물대장에서 층 확인 (✅ 모드A의 match_floor 사용)
        found_floor = False
        registry_floor_str = ''

        # area_result 확인
        if area_result and area_result.get(
                'success') and area_result.get('data'):
            for area_info in area_result['data']:
                floor_no = str(area_info.get('flrNo', ''))
                if floor_no and self.system.match_floor(
                        parsed_floor, floor_no):
                    found_floor = True
                    registry_floor_str = floor_no if '층' in floor_no or '지하' in floor_no else f"{floor_no}층"
                    print(
                        f"🔍 [해당층] area_result에서 {parsed_floor_str} 매칭: {registry_floor_str}")
                    break

        # floor_result 확인
        if not found_floor and floor_result and floor_result.get(
                'success') and floor_result.get('data'):
            for floor_info in floor_result['data']:
                floor_no_nm = str(floor_info.get('flrNoNm', ''))
                if floor_no_nm and self.system.match_floor(
                        parsed_floor, floor_no_nm):
                    found_floor = True
                    registry_floor_str = floor_no_nm
                    print(
                        f"🔍 [해당층] floor_result에서 {parsed_floor_str} 매칭: {registry_floor_str}")
                    break

        if found_floor:
            # ✅ 카톡 층수와 비교
            if kakao_data and kakao_data.get('floor') is not None:
                kakao_parsed_floor = kakao_data.get('floor')
                if kakao_parsed_floor != parsed_floor:
                    return {
                        'name': '해당 층',
                        'status': 'error',
                        'parsed_value': parsed_floor_str,
                        'registry_value': f"{registry_floor_str} (뱅크 기준)",
                        'kakao_value': kakao_floor_str,
                        'message': f'❌ 뱅크({parsed_floor_str})와 카톡({kakao_floor_str}) 층수 불일치'}

            return {
                'name': '해당 층',
                'status': 'correct',
                'parsed_value': parsed_floor_str,
                'registry_value': registry_floor_str,
                'kakao_value': kakao_floor_str,
                'message': '✅ 건축물대장과 일치합니다'
            }
        else:
            return {
                'name': '해당 층',
                'status': 'warning',
                'parsed_value': parsed_floor_str,
                'registry_value': '(대장에서 확인 필요)',
                'kakao_value': kakao_floor_str,
                'message': '⚠️ 건축물대장에서 해당 층을 확인해주세요'
            }

    def _validate_total_floors(
            self,
            parsed_data: Dict,
            building_data: Dict) -> Dict:
        """총층수 비교 (✅ 모드A 로직 100% 재사용)"""
        parsed_floors_str = parsed_data.get('total_floors', '')

        if not parsed_floors_str:
            return {
                'name': '총층수',
                'status': 'error',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': '-',
                'message': '❌ 총층수 정보 없음'
            }

        # 파싱된 층수 추출
        parsed_floors_match = re.search(r'(\d+)', parsed_floors_str)
        if not parsed_floors_match:
            return {
                'name': '총층수',
                'status': 'error',
                'parsed_value': parsed_floors_str,
                'registry_value': '-',
                'kakao_value': '-',
                'message': '❌ 층수 형식 오류'
            }

        parsed_floors = int(parsed_floors_match.group(1))

        # ✅ 모드A의 get_total_floors() 메서드 호출
        registry_floors = self.system.get_total_floors(building_data)

        if registry_floors == 0:
            return {
                'name': '총층수',
                'status': 'warning',
                'parsed_value': f"{parsed_floors}층",
                'registry_value': '(대장 정보 없음)',
                'kakao_value': '-',
                'message': '⚠️ 건축물대장에서 총층수 확인 필요'
            }

        if parsed_floors == registry_floors:
            return {
                'name': '총층수',
                'status': 'correct',
                'parsed_value': f"{parsed_floors}층",
                'registry_value': f"{registry_floors}층",
                'kakao_value': '-',
                'message': '✅ 건축물대장과 일치'
            }
        else:
            return {
                'name': '총층수',
                'status': 'error',
                'parsed_value': f"{parsed_floors}층",
                'registry_value': f"{registry_floors}층",
                'kakao_value': '-',
                'message': f'❌ 층수 불일치 (차이: {abs(parsed_floors - registry_floors)}층)'
            }

    def _validate_approval_date(
            self,
            parsed_data: Dict,
            building_data: Dict) -> Dict:
        """사용승인일 비교 (✅ 모드A 로직 100% 재사용)"""
        parsed_date_str = parsed_data.get('approval_date', '')

        if not parsed_date_str:
            return {
                'name': '사용승인일',
                'status': 'info',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': '-',
                'message': 'ℹ️ 사용승인일 정보 없음'
            }

        # ✅ 모드A의 get_approval_date() 메서드 호출
        registry_date_formatted = self.system.get_approval_date(building_data)

        if not registry_date_formatted:
            return {
                'name': '사용승인일',
                'status': 'warning',
                'parsed_value': parsed_date_str,
                'registry_value': '(대장 정보 없음)',
                'kakao_value': '-',
                'message': '⚠️ 건축물대장에서 확인 필요'
            }

        # 날짜 형식 통일 (YYYYMMDD)
        parsed_date_nums = re.findall(r'\d+', parsed_date_str)
        registry_date_nums = re.findall(r'\d+', registry_date_formatted)

        # 연도만 비교
        if parsed_date_nums and registry_date_nums:
            parsed_year = parsed_date_nums[0]
            registry_year = registry_date_nums[0][:4] if len(
                registry_date_nums[0]) >= 4 else registry_date_nums[0]

            if parsed_year == registry_year:
                return {
                    'name': '사용승인일',
                    'status': 'correct',
                    'parsed_value': parsed_date_str,
                    'registry_value': registry_date_formatted,
                    'kakao_value': '-',
                    'message': '✅ 건축물대장과 일치'
                }
            else:
                return {
                    'name': '사용승인일',
                    'status': 'error',
                    'parsed_value': parsed_date_str,
                    'registry_value': registry_date_formatted,
                    'kakao_value': '-',
                    'message': '❌ 날짜 불일치'
                }

        return {
            'name': '사용승인일',
            'status': 'warning',
            'parsed_value': parsed_date_str,
            'registry_value': str(registry_date),
            'message': '날짜 형식을 확인해주세요'
        }

    def _validate_parking(
            self,
            parsed_data: Dict,
            building_data: Dict) -> Dict:
        """주차대수 비교 (✅ 모드A 로직 100% 재사용)"""
        parsed_parking_str = parsed_data.get('parking_count', '')

        if not parsed_parking_str:
            return {
                'name': '주차대수',
                'status': 'info',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': '-',
                'message': 'ℹ️ 주차대수 정보 없음'
            }

        # 파싱된 주차대수 추출
        parsed_parking_match = re.search(r'(\d+)', parsed_parking_str)
        if not parsed_parking_match:
            return {
                'name': '주차대수',
                'status': 'error',
                'parsed_value': parsed_parking_str,
                'registry_value': '-',
                'kakao_value': '-',
                'message': '❌ 주차대수 형식 오류'
            }

        parsed_parking = int(parsed_parking_match.group(1))

        # ✅ 모드A의 get_parking_count() 메서드 호출 (100% 동일 로직)
        registry_parking = self.system.get_parking_count(building_data)

        if parsed_parking == registry_parking:
            return {
                'name': '주차대수',
                'status': 'correct',
                'parsed_value': f"{parsed_parking}대",
                'registry_value': f"{registry_parking}대",
                'kakao_value': '-',
                'message': '✅ 건축물대장과 일치'
            }
        else:
            return {
                'name': '주차대수',
                'status': 'warning',
                'parsed_value': f"{parsed_parking}대",
                'registry_value': f"{registry_parking}대",
                'kakao_value': '-',
                'message': f'⚠️ 주차대수 불일치 (차이: {abs(parsed_parking - registry_parking)}대)'
            }

    def _validate_property_type(
            self,
            parsed_data: Dict,
            floor_result: Dict,
            area_result: Dict,
            usage_judgment: Optional[Dict] = None,
            kakao_data: Optional[Dict] = None) -> Dict:
        """건축물 용도 비교 (✅ 3-way 비교: 뱅크 vs 대장 vs 카톡)"""
        parsed_type = parsed_data.get('property_type', '')

        # ✅ 카톡 건축물 용도 (usage 키 사용!)
        kakao_type = ''
        if kakao_data:
            kakao_type = kakao_data.get(
                'usage', '') or kakao_data.get(
                'property_type', '')
        kakao_type_str = kakao_type if kakao_type else '-'

        if not parsed_type:
            return {
                'name': '건축물 용도',
                'status': 'error',
                'parsed_value': '(없음)',
                'registry_value': '-',
                'kakao_value': kakao_type_str,
                'message': '건축물 용도 정보 없음'
            }

        # ✅ 모드 A의 _judge_usage 결과 사용
        if usage_judgment:
            registry_type = usage_judgment.get('judged_usage', '')

            # "확인요망"은 판정 실패로 처리
            if not registry_type or registry_type == '확인요망':
                registry_type = '(판정 실패)'

            # ✅ 3-way 비교: 뱅크, 대장, 카톡 모두 확인
            parsed_normalized = re.sub(r'[^\w가-힣]', '', parsed_type)
            registry_normalized = re.sub(r'[^\w가-힣]', '', registry_type)
            kakao_normalized = re.sub(
                r'[^\w가-힣]', '', kakao_type) if kakao_type else ''

            # 완전 일치 확인 (3개 모두)
            if kakao_type:
                # 카톡 정보가 있을 때: 3개 모두 일치해야 함
                if parsed_normalized == registry_normalized == kakao_normalized:
                    return {
                        'name': '건축물 용도',
                        'status': 'correct',
                        'parsed_value': parsed_type,
                        'registry_value': registry_type,
                        'kakao_value': kakao_type_str,
                        'message': '✅ 뱅크, 대장, 카톡 모두 일치'
                    }

                # 제1종/제2종 체크
                bank_has_type = '제1종' in parsed_type or '제2종' in parsed_type
                registry_has_type = '제1종' in registry_type or '제2종' in registry_type
                kakao_has_type = '제1종' in kakao_type or '제2종' in kakao_type

                # 하나라도 제1종/제2종이 있으면 정확히 비교
                if bank_has_type or registry_has_type or kakao_has_type:
                    # 뱅크 vs 대장
                    bank_registry_mismatch = (
                        ('제1종' in parsed_type and '제2종' in registry_type) or
                        ('제2종' in parsed_type and '제1종' in registry_type)
                    )
                    # 뱅크 vs 카톡
                    bank_kakao_mismatch = (
                        ('제1종' in parsed_type and '제2종' in kakao_type) or
                        ('제2종' in parsed_type and '제1종' in kakao_type)
                    )
                    # 대장 vs 카톡
                    registry_kakao_mismatch = (
                        ('제1종' in registry_type and '제2종' in kakao_type) or
                        ('제2종' in registry_type and '제1종' in kakao_type)
                    )

                    if bank_registry_mismatch or bank_kakao_mismatch or registry_kakao_mismatch:
                        return {
                            'name': '건축물 용도',
                            'status': 'error',
                            'parsed_value': parsed_type,
                            'registry_value': registry_type,
                            'kakao_value': kakao_type_str,
                            'message': '❌ 제1종/제2종이 서로 다릅니다'
                        }

                # 포함 관계 확인
                if (parsed_normalized in registry_normalized or registry_normalized in parsed_normalized) and (
                        parsed_normalized in kakao_normalized or kakao_normalized in parsed_normalized):
                    return {
                        'name': '건축물 용도',
                        'status': 'correct',
                        'parsed_value': parsed_type,
                        'registry_value': registry_type,
                        'kakao_value': kakao_type_str,
                        'message': '✅ 건축물대장과 일치'
                    }

                # 불일치
                return {
                    'name': '건축물 용도',
                    'status': 'error',
                    'parsed_value': parsed_type,
                    'registry_value': registry_type,
                    'kakao_value': kakao_type_str,
                    'message': '❌ 용도가 서로 다릅니다'
                }
            else:
                # 카톡 정보가 없을 때: 뱅크 vs 대장만 비교
                if parsed_normalized == registry_normalized:
                    return {
                        'name': '건축물 용도',
                        'status': 'correct',
                        'parsed_value': parsed_type,
                        'registry_value': registry_type,
                        'kakao_value': kakao_type_str,
                        'message': '✅ 건축물대장과 일치'
                    }

                # 제1종/제2종 체크
                if ('제1종' in parsed_type or '제2종' in parsed_type) and \
                   ('제1종' in registry_type or '제2종' in registry_type):
                    if ('제1종' in parsed_type and '제2종' in registry_type) or \
                       ('제2종' in parsed_type and '제1종' in registry_type):
                        return {
                            'name': '건축물 용도',
                            'status': 'error',
                            'parsed_value': parsed_type,
                            'registry_value': registry_type,
                            'kakao_value': kakao_type_str,
                            'message': '❌ 용도가 다릅니다 (제1종 vs 제2종)'
                        }

                # 포함 관계 확인
                if parsed_normalized in registry_normalized or registry_normalized in parsed_normalized:
                    return {
                        'name': '건축물 용도',
                        'status': 'correct',
                        'parsed_value': parsed_type,
                        'registry_value': registry_type,
                        'kakao_value': kakao_type_str,
                        'message': '✅ 건축물대장과 일치'
                    }

                # 불일치
                return {
                    'name': '건축물 용도',
                    'status': 'error',
                    'parsed_value': parsed_type,
                    'registry_value': registry_type,
                    'kakao_value': kakao_type_str,
                    'message': '❌ 용도가 다릅니다'
                }

        # usage_judgment가 없으면 fallback
        return {
            'name': '건축물 용도',
            'status': 'warning',
            'parsed_value': parsed_type,
            'registry_value': '(모드 A 로직 실행 안됨)',
            'kakao_value': kakao_type_str,
            'message': '⚠️ 용도 판정 실패'
        }

    def _format_date(self, date_str: str) -> str:
        """날짜 형식 변환 (YYYYMMDD → YYYY년 MM월 DD일)"""
        if not date_str:
            return ''

        date_nums = re.findall(r'\d+', str(date_str))
        if date_nums and len(date_nums[0]) == 8:
            date_full = date_nums[0]
            return f"{date_full[:4]}년 {date_full[4:6]}월 {date_full[6:8]}일"

        return str(date_str)
