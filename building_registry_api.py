"""
국토교통부 건축HUB 건축물대장정보 서비스 API 클라이언트
"""
import requests
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET
from urllib.parse import urlencode


class BuildingRegistryAPI:
    """건축물대장 API 클라이언트 클래스"""

    BASE_URL = "https://apis.data.go.kr/1613000/BldRgstHubService"

    # API 엔드포인트
    ENDPOINTS = {
        'title': 'getBrTitleInfo',  # 표제부 조회
        # 기본개요 조회 (정확한 엔드포인트명은 문서 확인 필요)
        'outline': 'getBrExposPubuseAreaInfo',
        'floor': 'getBrFlrOulnInfo',  # 층별개요 조회
        'area': 'getBrExposPubuseAreaInfo',  # 전유공용면적 조회
        'price': 'getBrHsprcInfo',  # 주택가격 조회
        'unit': 'getBrTitleInfo',  # 전유부 조회 (정확한 엔드포인트명은 문서 확인 필요)
        'sewage': 'getBrWclfInfo',  # 오수정화시설 조회
        'total_title': 'getBrTotTitleInfo',  # 총괄표제부 조회
        'sub_lot': 'getBrAtchJibunInfo',  # 부속지번 조회
        'district': 'getBrJijiguInfo',  # 지역지구구역 조회
    }

    def __init__(self, api_key: str):
        """
        Args:
            api_key: 공공데이터포털 API 키
        """
        self.api_key = api_key

    def _make_request(self, endpoint: str, params: Dict) -> Dict:
        """API 요청을 수행하고 XML 응답을 파싱"""
        params = params.copy()
        params.update({
            'serviceKey': self.api_key,
            'numOfRows': params.get('numOfRows', 10),
            'pageNo': params.get('pageNo', 1),
        })

        # None이나 빈 문자열인 파라미터 제거 (API가 필터링 제대로 하도록)
        params_clean = {}
        for k, v in params.items():
            # None이나 빈 문자열이면 제외
            if v is not None and v != '':
                # dongNm 파라미터 특별 처리: 한글이 포함되면 제거
                if k == 'dongNm':
                    v_str = str(v).strip()
                    # 숫자만 또는 영문 대문자 1글자만 허용 (한글 제외)
                    if v_str.isdigit() or (v_str.isalpha() and len(v_str) == 1 and v_str.isupper()):
                        params_clean[k] = v
                    # 그 외 (한글, 긴 문자열 등)는 제외
                else:
                    params_clean[k] = v

        url = f"{self.BASE_URL}/{endpoint}"

        # 디버깅: 실제 API 호출 URL 확인
        if endpoint == 'getBrExposPubuseAreaInfo':
            try:
                # params_clean으로 URL 생성 (serviceKey 제외)
                debug_params = {k: v for k,
                                v in params_clean.items() if k != 'serviceKey'}
                debug_url = url + '?' + \
                    '&'.join([f"{k}={v}" for k, v in debug_params.items()])
                with open('api_url_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(f"=== API 호출 URL (전유공용면적 조회) ===\n")
                    f.write(f"Base URL: {url}\n")
                    f.write(f"파라미터 (serviceKey 제외):\n")
                    for k, v in debug_params.items():
                        f.write(f"  {k}: {v}\n")
                    f.write(f"\n전체 URL (serviceKey 제외):\n{debug_url}\n")
                    if 'dongNm' not in debug_params:
                        f.write(f"\n⚠️ dongNm 파라미터가 전달되지 않음 (의도된 동작)\n")
            except BaseException:
                pass

        # 재시도 로직 (최대 3회)
        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                # 타임아웃 설정 (30초)
                response = requests.get(url, params=params_clean, timeout=30)
                response.raise_for_status()

                # XML 파싱
                root = ET.fromstring(response.content)

                # 헤더 정보
                header = root.find('header')
                result_code = header.find('resultCode').text
                result_msg = header.find('resultMsg').text

                if result_code != '00':
                    return {
                        'success': False,
                        'resultCode': result_code,
                        'resultMsg': result_msg,
                        'data': None
                    }

                # 본문 정보
                body = root.find('body')
                items = []

                if body is not None:
                    items_elem = body.find('items')
                    if items_elem is not None:
                        for item in items_elem.findall('item'):
                            item_data = {}
                            for child in item:
                                item_data[child.tag] = child.text
                            items.append(item_data)

                    # 페이지네이션 정보
                    num_of_rows = body.find('numOfRows')
                    page_no = body.find('pageNo')
                    total_count = body.find('totalCount')

                    pagination = {
                        'numOfRows': int(
                            num_of_rows.text) if num_of_rows is not None else 0, 'pageNo': int(
                            page_no.text) if page_no is not None else 0, 'totalCount': int(
                            total_count.text) if total_count is not None else 0, }
                else:
                    pagination = {}

                return {
                    'success': True,
                    'resultCode': result_code,
                    'resultMsg': result_msg,
                    'data': items,
                    'pagination': pagination
                }

            except requests.exceptions.Timeout as e:
                # 타임아웃 오류
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                return {
                    'success': False,
                    'error': f'요청 시간 초과 (30초): {str(e)}',
                    'error_type': 'timeout',
                    'data': None
                }
            except requests.exceptions.ConnectionError as e:
                # 연결 오류
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                return {
                    'success': False,
                    'error': f'연결 오류: {str(e)}',
                    'error_type': 'connection',
                    'data': None
                }
            except requests.exceptions.RequestException as e:
                # 기타 네트워크 오류
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                return {
                    'success': False,
                    'error': f'네트워크 오류: {str(e)}',
                    'error_type': 'network',
                    'data': None
                }
            except ET.ParseError as e:
                # XML 파싱 오류는 재시도하지 않음
                return {
                    'success': False,
                    'error': f'XML 파싱 오류: {str(e)}',
                    'error_type': 'parse',
                    'data': None
                }

        # 모든 재시도 실패
        return {
            'success': False,
            'error': f'요청 실패 (재시도 {max_retries}회 모두 실패)',
            'error_type': 'max_retries',
            'data': None
        }

    def get_title_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 표제부 조회

        Args:
            sigungu_cd: 시군구코드 (5자리)
            bjdong_cd: 법정동코드 (5자리)
            bun: 번 (4자리)
            ji: 지 (4자리)
            plat_gb_cd: 대지구분코드 (0:대지, 1:산, 2:블록)
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['title'], params)

    def get_floor_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        mgm_bldrgst_pk: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 층별개요 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            mgm_bldrgst_pk: 관리건축물대장PK (표제부 조회에서 얻은 값)
            plat_gb_cd: 대지구분코드
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'mgmBldrgstPk': mgm_bldrgst_pk,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['floor'], params)

    def get_unit_area_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        mgm_bldrgst_pk: str,
        plat_gb_cd: str = '0',
        dong_nm: Optional[str] = None,
        ho_nm: Optional[str] = None,
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 전유공용면적 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            mgm_bldrgst_pk: 관리건축물대장PK
            plat_gb_cd: 대지구분코드
            dong_nm: 동명칭 (선택사항, 예: "302", "1")
            ho_nm: 호명칭 (선택사항, 예: "101", "201호" → "101", "201" 형태로 입력)
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'mgmBldrgstPk': mgm_bldrgst_pk,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        # 동명칭 추가 (있는 경우만, None이나 빈 문자열이면 전달하지 않음)
        # ⚠️ 중요: 동명칭이 확실하지 않으면 None으로 설정하여 API 호출 시 dongNm 파라미터를 전달하지 않음
        # "수성동4가" 같은 법정동명은 동명칭이 아니므로 제외
        # 동명칭은 건물 내 동을 의미 (예: "1", "302", "A") - 숫자나 영문 1글자만
        if dong_nm and str(dong_nm).strip() and str(dong_nm).strip() != '':
            dong_nm_clean = str(dong_nm).strip()
            # 숫자만 또는 영문 대문자 1글자만 허용 (법정동명 제외)
            # "수성" 같은 한글은 제외
            if dong_nm_clean.isdigit() or (dong_nm_clean.isalpha() and len(
                    dong_nm_clean) == 1 and dong_nm_clean.isupper()):
                params['dongNm'] = dong_nm_clean
            # 그 외의 경우 (한글, 긴 문자열 등)는 dongNm 파라미터를 전달하지 않음

        # 호명칭 추가 (있는 경우) - "호" 제거 후 숫자만 전달
        if ho_nm and str(ho_nm).strip():
            # "101호", "201호" 형태를 "101", "201"로 변환
            ho_nm_clean = str(ho_nm).strip().replace('호', '').strip()
            if ho_nm_clean:
                params['hoNm'] = ho_nm_clean

        # 디버깅: API 호출 파라미터 확인
        try:
            with open('api_call_debug.txt', 'w', encoding='utf-8') as f:
                f.write(f"=== API 호출 파라미터 (전유공용면적 조회) ===\n")
                f.write(f"ho_nm (입력): {ho_nm}\n")
                f.write(f"ho_nm_clean (전송): {params.get('hoNm', '없음')}\n")
                f.write(f"dong_nm (입력): {dong_nm}\n")
                f.write(
                    f"dongNm 파라미터: {
                        params.get(
                            'dongNm',
                            '없음 (전달 안 됨)')}\n")
                f.write(f"\n전체 파라미터 (serviceKey 제외):\n")
                for key, value in params.items():
                    if key != 'serviceKey':  # serviceKey는 보안상 제외
                        f.write(f"  {key}: {value}\n")
        except BaseException:
            pass

        return self._make_request(self.ENDPOINTS['area'], params)

    def get_housing_price_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        mgm_bldrgst_pk: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 주택가격 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            mgm_bldrgst_pk: 관리건축물대장PK
            plat_gb_cd: 대지구분코드
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'mgmBldrgstPk': mgm_bldrgst_pk,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['price'], params)

    def get_unit_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        mgm_bldrgst_pk: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 전유부 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            mgm_bldrgst_pk: 관리건축물대장PK
            plat_gb_cd: 대지구분코드
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'mgmBldrgstPk': mgm_bldrgst_pk,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['unit'], params)

    def get_total_title_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 총괄표제부 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            plat_gb_cd: 대지구분코드
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['total_title'], params)

    def get_sewage_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        mgm_bldrgst_pk: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 오수정화시설 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            mgm_bldrgst_pk: 관리건축물대장PK
            plat_gb_cd: 대지구분코드
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'mgmBldrgstPk': mgm_bldrgst_pk,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['sewage'], params)

    def get_district_info(
        self,
        sigungu_cd: str,
        bjdong_cd: str,
        bun: str,
        ji: str,
        mgm_bldrgst_pk: str,
        plat_gb_cd: str = '0',
        num_of_rows: int = 10,
        page_no: int = 1
    ) -> Dict:
        """
        건축물대장 지역지구구역 조회

        Args:
            sigungu_cd: 시군구코드
            bjdong_cd: 법정동코드
            bun: 번
            ji: 지
            mgm_bldrgst_pk: 관리건축물대장PK
            plat_gb_cd: 대지구분코드
            num_of_rows: 페이지당 건수
            page_no: 페이지 번호

        Returns:
            API 응답 결과
        """
        params = {
            'sigunguCd': sigungu_cd,
            'bjdongCd': bjdong_cd,
            'bun': bun,
            'ji': ji,
            'mgmBldrgstPk': mgm_bldrgst_pk,
            'platGbCd': plat_gb_cd,
            'numOfRows': num_of_rows,
            'pageNo': page_no,
        }

        return self._make_request(self.ENDPOINTS['district'], params)


# 사용 예시
if __name__ == "__main__":
    # API 키 설정
    API_KEY = "770b632a7abe47d5adad542d8b29350aceb52a0d82009f9acbef29101daa8a81"

    # API 클라이언트 생성
    api = BuildingRegistryAPI(API_KEY)

    # 예시: 서울특별시 강남구 개포동 12번지 건축물 표제부 조회
    result = api.get_title_info(
        sigungu_cd='11680',  # 강남구
        bjdong_cd='10300',  # 개포동
        bun='0012',
        ji='0000'
    )

    if result['success']:
        print(f"결과 코드: {result['resultCode']}")
        print(f"결과 메시지: {result['resultMsg']}")
        print(f"총 건수: {result['pagination'].get('totalCount', 0)}")
        print(f"\n조회된 건축물 수: {len(result['data'])}")

        # 첫 번째 건축물 정보 출력
        if result['data']:
            first_building = result['data'][0]
            print("\n=== 첫 번째 건축물 정보 ===")
            for key, value in first_building.items():
                print(f"{key}: {value}")
    else:
        print(
            f"오류 발생: {
                result.get(
                    'error',
                    result.get(
                        'resultMsg',
                        '알 수 없는 오류'))}")
