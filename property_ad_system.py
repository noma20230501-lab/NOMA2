"""
부동산 매물 광고 생성 및 교차 검증 통합 시스템
모드 A: 블로그 필수표시사항 생성기
모드 B: 네이버부동산 교차 검수기
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from kakao_parser import KakaoPropertyParser
from building_registry_api import BuildingRegistryAPI
from address_code_helper import parse_address
from typing import Dict, Optional
import re

# 네이버 관련 모듈은 선택적으로 import (bs4 등이 없을 수 있음)
try:
    from naver_crawler import NaverPropertyCrawler
    from naver_parser import NaverPropertyParser
    NAVER_MODULES_AVAILABLE = True
except ImportError:
    NaverPropertyCrawler = None
    NaverPropertyParser = None
    NAVER_MODULES_AVAILABLE = False
except Exception:
    # 다른 종류의 오류도 처리
    NaverPropertyCrawler = None
    NaverPropertyParser = None
    NAVER_MODULES_AVAILABLE = False


class PropertyAdSystem:
    """부동산 매물 광고 통합 시스템"""

    def __init__(self, root, skip_gui=False):
        self.root = root
        if not skip_gui and hasattr(root, 'title'):
            try:
                self.root.title("부동산 매물 광고 생성 및 검수 시스템")
                self.root.geometry("1200x800")
                self.root.resizable(True, True)
            except BaseException:
                pass  # Mock 객체인 경우 무시

        # API 클라이언트 초기화
        API_KEY = "770b632a7abe47d5adad542d8b29350aceb52a0d82009f9acbef29101daa8a81"
        self.api = BuildingRegistryAPI(API_KEY)

        # 파서 초기화
        self.kakao_parser = KakaoPropertyParser()

        # 네이버 파서와 크롤러 초기화 (선택적 사용)
        if NAVER_MODULES_AVAILABLE and NaverPropertyParser:
            self.naver_parser = NaverPropertyParser()
        else:
            self.naver_parser = None

        if NAVER_MODULES_AVAILABLE and NaverPropertyCrawler:
            self.naver_crawler = NaverPropertyCrawler()
        else:
            self.naver_crawler = None

        # 현재 모드
        if not skip_gui:
            try:
                self.current_mode = tk.StringVar(value="generate")
            except BaseException:
                self.current_mode = None
        else:
            self.current_mode = None

        # GUI 구성 (skip_gui가 True이면 건너뛰기)
        if not skip_gui:
            try:
                self.create_widgets()
            except BaseException:
                pass  # GUI 생성 실패해도 계속 진행

    def create_widgets(self):
        """GUI 위젯 생성"""
        # 상단 모드 선택
        mode_frame = ttk.LabelFrame(self.root, text="작업 모드 선택", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Radiobutton(
            mode_frame,
            text="모드 A: 블로그 필수표시사항 생성",
            variable=self.current_mode,
            value="generate",
            command=self.on_mode_change).pack(
            side=tk.LEFT,
            padx=10)
        ttk.Radiobutton(
            mode_frame,
            text="모드 B: 네이버부동산 교차 검수",
            variable=self.current_mode,
            value="verify",
            command=self.on_mode_change).pack(
            side=tk.LEFT,
            padx=10)

        # 입력 영역
        input_frame = ttk.LabelFrame(self.root, text="입력", padding=10)
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 모드 A: 카톡 텍스트 입력
        self.kakao_frame = ttk.Frame(input_frame)
        self.kakao_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(self.kakao_frame, text="카카오톡 매물 정보 (복사/붙여넣기):",
                  font=('맑은 고딕', 10, 'bold')).pack(anchor=tk.W, pady=5)

        self.kakao_text = scrolledtext.ScrolledText(
            self.kakao_frame,
            height=15,
            wrap=tk.WORD,
            spacing1=2,
            spacing2=2,
            spacing3=2)
        self.kakao_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # placeholder 텍스트 설정
        self.placeholder_text = """카카오톡 매물 정보를 여기에 붙여넣으세요

예시:
중구 대안동 70-1 4층
1. 500/35 부가세없음
2. 관리비 실비정산
3. 무권리
4. 제1종근생 사무소 / 24.36m2 / 약 7평
5. 1층 주차장 있지만 협소 / 내부화장실1개
6. 동향
7. 등기 o 불법 x
8. 임대인 010 3547 3814"""

        # placeholder 태그 설정 (반투명 회색)
        self.kakao_text.tag_config(
            "placeholder", foreground="#999999", font=(
                '맑은 고딕', 10, 'italic'))

        # placeholder 텍스트 삽입
        self.kakao_text.insert(1.0, self.placeholder_text)
        self.kakao_text.tag_add("placeholder", 1.0, tk.END)

        # placeholder 상태 추적
        self.is_placeholder = True

        # 포커스 이벤트 바인딩 (placeholder 제거)
        self.kakao_text.bind("<FocusIn>", self._on_kakao_text_focus_in)
        self.kakao_text.bind("<FocusOut>", self._on_kakao_text_focus_out)
        self.kakao_text.bind("<Key>", self._on_kakao_text_key)
        self.kakao_text.bind("<Button-1>", self._on_kakao_text_click)

        # 모드 B: 네이버부동산 정보 입력 (수동 입력)
        self.naver_frame = ttk.Frame(input_frame)
        ttk.Label(self.naver_frame, text="네이버부동산 정보 (복사/붙여넣기):",
                  font=('맑은 고딕', 10, 'bold')).pack(anchor=tk.W, pady=5)
        self.naver_text = scrolledtext.ScrolledText(
            self.naver_frame,
            height=15,
            wrap=tk.WORD,
            spacing1=2,
            spacing2=2,
            spacing3=2)
        self.naver_text.pack(fill=tk.BOTH, expand=True, pady=5)

        # placeholder 텍스트 설정
        self.naver_placeholder_text = """네이버 부동산에서 매물 정보를 복사하여 붙여넣으세요

예시:
소재지: 대구 중구 삼덕동2가 122
보증금: 2,000만원
월세: 150만원
전용면적: 44.43㎡ (13.4평)
해당층/총층: 1층 / 5층
중개대상물 종류: 제1종 근린생활시설
화장실: 1개
주차: 가능
방향: 북동향
사용승인일: 1996.02.15"""

        # placeholder 태그 설정
        self.naver_text.tag_config(
            "placeholder", foreground="#999999", font=(
                '맑은 고딕', 10, 'italic'))

        # placeholder 텍스트 삽입
        self.naver_text.insert(1.0, self.naver_placeholder_text)
        self.naver_text.tag_add("placeholder", 1.0, tk.END)

        # placeholder 상태 추적
        self.is_naver_placeholder = True

        # 포커스 이벤트 바인딩
        self.naver_text.bind("<FocusIn>", self._on_naver_text_focus_in)
        self.naver_text.bind("<FocusOut>", self._on_naver_text_focus_out)
        self.naver_text.bind("<Key>", self._on_naver_text_key)
        self.naver_text.bind("<Button-1>", self._on_naver_text_click)

        # 출력 영역 (버튼 프레임보다 먼저 생성하되, pack 순서 조정)
        output_frame = ttk.LabelFrame(self.root, text="결과", padding=10)

        # 버튼 영역 (입력 프레임과 출력 프레임 사이에 배치) - 입력 프레임 바로 아래에 pack
        self.button_frame = ttk.Frame(self.root)
        self.button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.generate_btn = tk.Button(
            self.button_frame,
            text="블로그 양식 생성",
            command=self.generate_blog_ad,
            bg='#2196F3',
            fg='white',
            font=(
                '맑은 고딕',
                12,
                'bold'),
            padx=20,
            pady=10,
            width=20)
        self.generate_btn.pack(side=tk.LEFT, padx=5)

        self.verify_btn = ttk.Button(
            self.button_frame,
            text="광고 검수 시작",
            command=self.verify_naver_ad,
            state=tk.DISABLED)
        self.verify_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(
            self.button_frame,
            text="초기화",
            command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 출력 영역을 버튼 프레임 아래에 pack
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 결과 복사 버튼 프레임
        result_button_frame = ttk.Frame(output_frame)
        result_button_frame.pack(fill=tk.X, pady=(0, 5))

        # 결과 복사 버튼
        self.copy_btn = tk.Button(
            result_button_frame,
            text="악보가완성됐다 이기러가자!!",
            command=self.copy_result_to_clipboard,
            bg='#4CAF50',
            fg='white',
            font=(
                '맑은 고딕',
                10,
                'bold'),
            padx=10,
            pady=5)
        self.copy_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 건축물대장 조회 버튼
        registry_btn = tk.Button(
            result_button_frame,
            text="건축물대장 조회",
            command=self.open_building_registry,
            bg='#2196F3',
            fg='white',
            font=(
                '맑은 고딕',
                10,
                'bold'),
            padx=10,
            pady=5)
        registry_btn.pack(side=tk.LEFT)

        self.result_text = scrolledtext.ScrolledText(
            output_frame, height=20, wrap=tk.WORD, spacing1=2, spacing2=2, spacing3=2)
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # 면적 적용 버튼 프레임 (초기에는 숨김)
        self.area_button_frame = tk.Frame(output_frame)
        # 초기에는 pack하지 않음 (면적 불일치 시에만 표시)

        # 텍스트 태그 설정
        self.result_text.tag_config(
            "warning", foreground="red", font=(
                '맑은 고딕', 10, 'bold'))
        self.result_text.tag_config(
            "bathroom_warning",
            foreground="red",
            font=(
                '맑은 고딕',
                10))
        self.result_text.tag_config(
            "violation_warning", foreground="red", font=(
                '맑은 고딕', 10, 'bold'))
        self.result_text.tag_config(
            "usage_mismatch", foreground="red", font=(
                '맑은 고딕', 10, 'bold'))
        self.result_text.tag_config(
            "kakao_area", foreground="blue", font=(
                '맑은 고딕', 10, 'bold'))
        self.result_text.tag_config(
            "registry_area", foreground="red", font=(
                '맑은 고딕', 10, 'bold'))
        self.result_text.tag_config(
            "area_clickable", foreground="blue", font=(
                '맑은 고딕', 10, 'bold'), underline=True)
        self.result_text.tag_config(
            "area_clickable_registry", foreground="red", font=(
                '맑은 고딕', 10, 'bold'), underline=True)

        # 면적 클릭 이벤트 바인딩
        self.result_text.tag_bind(
            "area_clickable",
            "<Button-1>",
            self._on_kakao_area_click)
        self.result_text.tag_bind(
            "area_clickable_registry",
            "<Button-1>",
            self._on_registry_area_click)

        # 면적 비교 정보 저장용
        self.current_area_comparison = None
        self.current_parsed = None
        self.current_registry_area = None  # 건축물대장 면적 저장
        self.selected_area = None  # 사용자가 클릭하여 선택한 면적 (None이면 둘 다 표시)

        # 건축물대장 조회용 정보 저장
        self.current_building_info = None  # 현재 조회한 건축물 정보
        self.current_address_info = None  # 현재 조회한 주소 정보

        # 상태바
        self.status_var = tk.StringVar(value="준비")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 초기 모드 설정
        self.on_mode_change()

    def _setup_placeholder_handlers(self):
        """placeholder 이벤트 핸들러 설정"""
        pass  # 이미 위에서 바인딩됨

    def _on_kakao_text_focus_in(self, event):
        """카톡 텍스트 포커스 인 이벤트"""
        if self.is_placeholder:
            self.kakao_text.delete(1.0, tk.END)
            self.is_placeholder = False

    def _on_kakao_text_focus_out(self, event):
        """카톡 텍스트 포커스 아웃 이벤트"""
        content = self.kakao_text.get(1.0, tk.END).strip()
        if not content:
            self.kakao_text.insert(1.0, self.placeholder_text)
            self.kakao_text.tag_add("placeholder", 1.0, tk.END)
            self.is_placeholder = True

    def _on_kakao_text_key(self, event):
        """카톡 텍스트 키 입력 이벤트"""
        if self.is_placeholder:
            self.kakao_text.delete(1.0, tk.END)
            self.is_placeholder = False

    def _on_kakao_text_click(self, event):
        """카톡 텍스트 클릭 이벤트"""
        if self.is_placeholder:
            self.kakao_text.delete(1.0, tk.END)
            self.is_placeholder = False

    def on_mode_change(self):
        """모드 변경 시 UI 업데이트"""
        # 복사 버튼 텍스트 초기화 (모드 전환 시에도 초기화)
        if hasattr(self, 'copy_btn'):
            self.copy_btn.config(text="악보가완성됐다 이기러가자!!")

        if self.current_mode.get() == "generate":
            self.kakao_frame.pack(fill=tk.BOTH, expand=True)
            self.naver_frame.pack_forget()
            self.generate_btn.config(state=tk.NORMAL)
            self.verify_btn.config(state=tk.DISABLED)
        else:
            self.kakao_frame.pack_forget()
            self.naver_frame.pack(fill=tk.BOTH, expand=True)
            self.generate_btn.config(state=tk.DISABLED)
            self.verify_btn.config(state=tk.NORMAL)

    def generate_blog_ad(self):
        """모드 A: 블로그 필수표시사항 생성"""
        try:
            # 복사 버튼 텍스트 초기화
            if hasattr(self, 'copy_btn'):
                self.copy_btn.config(text="악보가완성됐다 이기러가자!!")

            self.status_var.set("처리 중...")
            self.result_text.delete(1.0, tk.END)
            # 기존 버튼 프레임 숨기기
            if hasattr(self, 'area_button_frame'):
                self.area_button_frame.pack_forget()
                for widget in self.area_button_frame.winfo_children():
                    widget.destroy()

            # 새로운 검색이므로 선택된 면적 초기화 (다른 매물/층 검색 시 면적 선택 리셋)
            self.selected_area = None
            # 위반건축물 경고 플래그 초기화
            self._violation_warning_active = False

            # 카톡 텍스트 파싱 (placeholder 제외)
            kakao_text = self.kakao_text.get(1.0, tk.END).strip()
            # placeholder 텍스트인지 확인
            if kakao_text == self.placeholder_text.strip() or not kakao_text:
                messagebox.showwarning("입력 오류", "카카오톡 매물 정보를 입력해주세요.")
                return

            parsed = self.kakao_parser.parse(kakao_text)

            # 디버깅: 파싱 결과 확인
            debug_parsed = []
            debug_parsed.append("=== 카카오톡 파싱 결과 ===")
            debug_parsed.append(
                f"원본 텍스트 (첫 줄): {
                    kakao_text.split(
                        chr(10))[0] if chr(10) in kakao_text else kakao_text.split('\n')[0]}")
            debug_parsed.append(f"주소: {parsed.get('address', '')}")
            debug_parsed.append(f"층수: {parsed.get('floor', '')}")
            debug_parsed.append(f"호수: {parsed.get('ho', '없음')}")  # 호수 정보 추가
            debug_parsed.append(f"면적(m2): {parsed.get('area_m2', '')}")
            debug_parsed.append(f"면적(평): {parsed.get('area_pyeong', '')}")
            debug_parsed.append(f"용도: {parsed.get('usage', '')}")
            try:
                with open('parsed_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_parsed))
            except BaseException:
                pass

            # 주소에서 건축물대장 정보 조회
            if not parsed['address']:
                messagebox.showerror("오류", "주소를 찾을 수 없습니다.")
                return

            address = parsed['address']
            floor = parsed['floor']

            # 주소 파싱
            address_info = parse_address(address)

            # 디버깅: 주소 파싱 결과 확인
            debug_address = []
            debug_address.append("=== 주소 파싱 결과 ===")
            debug_address.append(f"입력 주소: {address}")
            debug_address.append(
                f"시군구 코드: {
                    address_info.get(
                        'sigungu_code',
                        'None')}")
            debug_address.append(
                f"시군구 이름: {
                    address_info.get(
                        'sigungu_name',
                        'None')}")
            debug_address.append(
                f"법정동 코드: {
                    address_info.get(
                        'bjdong_code',
                        'None')}")
            debug_address.append(
                f"법정동 이름: {
                    address_info.get(
                        'bjdong_name',
                        'None')}")
            debug_address.append(f"번: {address_info.get('bun', 'None')}")
            debug_address.append(f"지: {address_info.get('ji', 'None')}")
            try:
                with open('address_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_address))
            except BaseException:
                pass

            if not address_info['sigungu_code'] or not address_info['bjdong_code']:
                error_msg = f"주소를 파싱할 수 없습니다: {address}\n\n"
                error_msg += f"시군구 코드: {
                    address_info.get(
                        'sigungu_code', '없음')}\n"
                error_msg += f"법정동 코드: {address_info.get('bjdong_code', '없음')}"
                messagebox.showerror("오류", error_msg)
                return

            # 건축물대장 조회
            title_result = self.api.get_title_info(
                sigungu_cd=address_info['sigungu_code'],
                bjdong_cd=address_info['bjdong_code'],
                bun=address_info['bun'],
                ji=address_info['ji'],
                num_of_rows=10
            )

            if not title_result['success'] or not title_result['data']:
                # 더 자세한 오류 메시지 표시
                error_type = title_result.get('error_type', 'unknown')
                error_msg = title_result.get(
                    'error', '') or title_result.get(
                    'resultMsg', '알 수 없는 오류')

                if error_type == 'timeout':
                    error_message = f"건축물대장 정보 조회 시간이 초과되었습니다.\n\n"
                    error_message += f"오류: {error_msg}\n\n"
                    error_message += "네트워크 상태를 확인하고 잠시 후 다시 시도해주세요."
                elif error_type == 'connection':
                    error_message = f"건축물대장 정보 서버에 연결할 수 없습니다.\n\n"
                    error_message += f"오류: {error_msg}\n\n"
                    error_message += "인터넷 연결을 확인하고 잠시 후 다시 시도해주세요."
                elif error_type == 'network':
                    error_message = f"네트워크 오류가 발생했습니다.\n\n"
                    error_message += f"오류: {error_msg}\n\n"
                    error_message += "잠시 후 다시 시도해주세요."
                elif 'resultCode' in title_result and title_result.get('resultCode') != '00':
                    error_message = f"건축물대장 정보를 조회할 수 없습니다.\n\n"
                    error_message += f"오류 코드: {
                        title_result.get(
                            'resultCode', '알 수 없음')}\n"
                    error_message += f"오류 메시지: {error_msg}\n\n"
                    error_message += f"주소: {parsed.get('address', '')}\n"
                    if address_info:
                        error_message += f"법정동 코드: {
                            address_info.get(
                                'bjdong_code', '없음')}\n"
                        error_message += f"번지: {
                            address_info.get(
                                'bun', '없음')}-{
                            address_info.get(
                                'ji', '없음')}"
                else:
                    error_message = f"건축물대장 정보를 조회할 수 없습니다.\n\n"
                    error_message += f"오류: {error_msg}\n\n"
                    error_message += f"주소: {parsed.get('address', '')}\n\n"
                    error_message += "주소가 정확한지 확인하고 잠시 후 다시 시도해주세요."

                messagebox.showerror("오류", error_message)
                return

            # 여러 건축물이 있는 경우 "일반건축물" 우선 선택
            buildings = title_result['data']
            building = None

            # "일반건축물" 또는 "일반 건축물"이 포함된 건축물 우선 선택
            for bld in buildings:
                # 건축물 종류를 나타내는 필드 확인 (여러 가능한 필드명 시도)
                bld_type_fields = [
                    'regstrKindCdNm',  # 등기 종류 명
                    'regstrKindCd',    # 등기 종류 코드
                    'bldrgstKindCdNm',  # 건축물대장 종류 명
                    'bldrgstKindCd',   # 건축물대장 종류 코드
                    'regstrKind',      # 등기 종류
                    'bldrgstKind',     # 건축물대장 종류
                ]

                is_general = False
                for field in bld_type_fields:
                    value = bld.get(field, '')
                    if value:
                        value_str = str(value).strip()
                        # "일반건축물" 또는 "일반 건축물" 확인
                        if '일반건축물' in value_str or '일반 건축물' in value_str or '일반' in value_str:
                            is_general = True
                            break

                if is_general:
                    building = bld
                    break

            # "일반건축물"이 없으면 첫 번째 건축물 사용
            if not building:
                building = buildings[0]

            # 디버깅: 건축물대장 응답의 모든 키 출력 (주차 대수, 위반건축물 필드 확인용)
            debug_info = []
            debug_info.append("=== 건축물대장 응답 키 (전체) ===")
            for key in sorted(building.keys()):
                value = building.get(key)
                debug_info.append(f"{key}: {value}")

            # 위반건축물 관련 필드만 별도로 추출
            debug_info.append("\n=== 위반건축물 관련 필드 ===")
            violat_related_keys = []
            for key in sorted(building.keys()):
                key_lower = key.lower()
                value = building.get(key)
                value_str = str(value) if value else ''

                # 위반 관련 키워드가 필드명에 있는 경우
                if ('위반' in key or 'violat' in key_lower or 'excp' in key_lower or
                    '예외' in key or 'rserthqk' in key_lower or 'illegal' in key_lower or
                        '불법' in key or '위법' in key):
                    violat_related_keys.append(key)
                    debug_info.append(f"{key}: {value}")

                # 필드 값에 "위반건축물" 키워드가 있는 경우
                elif '위반건축물' in value_str:
                    violat_related_keys.append(key)
                    debug_info.append(f"{key}: {value} [위반건축물 키워드 발견]")

                # 변동사항 관련 필드
                elif ('변동' in key or 'change' in key_lower or '이력' in key or 'history' in key_lower):
                    if '위반건축물' in value_str:
                        violat_related_keys.append(key)
                        debug_info.append(
                            f"{key}: {value} [변동사항에 위반건축물 키워드 발견]")

            if not violat_related_keys:
                debug_info.append("위반건축물 관련 필드를 찾을 수 없습니다.")

            # 파일로 저장 (디버깅용)
            try:
                with open('building_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_info))
            except BaseException:
                pass

            # 층별 현황 조회 (해당 층 정보) - 층수 없으면 1층으로 가정하여 조회
            floor_result = None
            area_result = None  # 전유공용면적 조회 결과
            if building.get('mgmBldrgstPk'):
                search_floor = floor if floor else 1  # 층수 없으면 1층으로
                floor_result = self.api.get_floor_info(
                    sigungu_cd=address_info['sigungu_code'],
                    bjdong_cd=address_info['bjdong_code'],
                    bun=address_info['bun'],
                    ji=address_info['ji'],
                    mgm_bldrgst_pk=building['mgmBldrgstPk'],
                    num_of_rows=50
                )

                # 전유공용면적 조회 (해당 층의 전용면적 확인용)
                ho = parsed.get('ho')
                dong_nm = None
                # ⚠️ 중요: 동명칭(dongNm)은 건물 내 동을 의미 (예: "1동", "302동", "A동")
                # "수성동4가" 같은 법정동명은 동명칭이 아니므로 제외해야 함!
                #
                # 동명칭이 있는 경우: "수성롯데캐슬 아파트 1동 101호" → dongNm: 1
                # 동명칭이 없는 경우: "상가1층 101호" → dongNm: None (비워둠)
                #
                # API 홈페이지에서 테스트했을 때는 dongNm을 비워두고 hoNm만 사용했을 것입니다.
                # 동명칭이 확실하지 않으면 None으로 설정하여 API 호출 시 dongNm 파라미터를 전달하지 않음

                # 현재 입력: "수성구 수성동4가 1085-28 수성롯데캐슬 아파트 상가1층 101호 이루팜"
                # → 동명칭이 없으므로 dong_nm = None 유지

                area_result = self.api.get_unit_area_info(
                    sigungu_cd=address_info['sigungu_code'],
                    bjdong_cd=address_info['bjdong_code'],
                    bun=address_info['bun'],
                    ji=address_info['ji'],
                    mgm_bldrgst_pk=building['mgmBldrgstPk'],
                    dong_nm=dong_nm,  # 동명칭 추가
                    ho_nm=ho,  # 호명칭 추가 (API에서 필터링)
                    num_of_rows=50
                )

                # 전유부 조회 (호수별 면적 확인용 - 101호 등) - 호수가 있는 경우에만
                unit_result = None
                unit_matched = False  # 전유부에서 호수 매칭 성공 여부
                if ho:
                    unit_result = self.api.get_unit_info(
                        sigungu_cd=address_info['sigungu_code'],
                        bjdong_cd=address_info['bjdong_code'],
                        bun=address_info['bun'],
                        ji=address_info['ji'],
                        mgm_bldrgst_pk=building['mgmBldrgstPk'],
                        num_of_rows=50
                    )
                    # 전유부에서 호수 매칭 확인
                    if unit_result and unit_result.get(
                            'success') and unit_result.get('data'):
                        ho_normalized = str(ho).replace('호', '').strip()
                        for unit_info in unit_result['data']:
                            ho_fields = [
                                'ho',
                                'hoNo',
                                'hoNm',
                                'hoNoNm',
                                '호수',
                                '호',
                                'unitNo',
                                'unit',
                                'dongNo',
                                'dongNm',
                                'hoStr',
                                'hoStrNm']
                            for ho_field in ho_fields:
                                ho_value = unit_info.get(ho_field, '')
                                if ho_value:
                                    ho_value_str = str(ho_value).strip()
                                    ho_value_normalized = ho_value_str.replace(
                                        '호', '').strip()
                                    if (ho == ho_value_str or
                                        ho_normalized == ho_value_normalized or
                                        ho_value_normalized.startswith(ho_normalized) or
                                            ho_normalized.startswith(ho_value_normalized)):
                                        unit_matched = True
                                        break
                            if unit_matched:
                                break

                    # 호수가 있는데 전유부에서 찾을 수 없으면 알림
                    if not unit_matched:
                        messagebox.showwarning("전유부 매칭 실패",
                                               f"소재지에 호수('{ho}호') 정보가 있지만,\n"
                                               f"전유부에서 해당 호수를 찾을 수 없습니다.\n\n"
                                               f"표제부 정보를 기준으로 표시합니다.")
            else:
                # building.get('mgmBldrgstPk')가 없으면 unit_result도 None으로 초기화
                unit_result = None
                unit_matched = False

            # 용도 판정 (area_result 포함)
            usage_judgment = self._judge_usage(
                building, parsed, floor_result, floor, area_result)

            # 디버깅: 용도 판정 결과 확인
            debug_info = []
            debug_info.append(f"=== 용도 판정 디버깅 ===")
            debug_info.append(f"해당 층: {floor if floor else 1}층")
            debug_info.append(
                f"표제부 API 용도: {
                    building.get(
                        'mainPurpsCdNm',
                        '')}")
            debug_info.append(f"표제부 기타 용도: {building.get('etcPurps', '')}")
            debug_info.append(
                f"판정에 사용된 API 용도: {
                    usage_judgment.get(
                        'api_usage', '')}")
            debug_info.append(
                f"판정에 사용된 기타 용도: {
                    usage_judgment.get(
                        'etc_usage', '')}")
            debug_info.append(f"카톡 용도: {parsed.get('usage', '')}")
            debug_info.append(f"면적: {usage_judgment.get('area_m2', '')}")
            debug_info.append(
                f"판정된 용도: {
                    usage_judgment.get(
                        'judged_usage',
                        '')}")

            # 층별개요 정보도 추가 (모든 층 정보 출력)
            if floor_result and floor_result.get(
                    'success') and floor_result.get('data'):
                debug_info.append(f"\n=== 층별개요 정보 (전체) ===")
                for idx, floor_info in enumerate(floor_result['data']):
                    floor_num = floor_info.get(
                        'flrNoNm',
                        '') or floor_info.get(
                        'flrNo',
                        '') or floor_info.get(
                        'flrNoNm1',
                        '') or floor_info.get(
                        'flrNo1',
                        '')
                    floor_usage = floor_info.get(
                        'mainPurpsCdNm', '') or floor_info.get(
                        'mainPurps', '')
                    floor_etc = floor_info.get('etcPurps', '')
                    debug_info.append(
                        f"[{idx + 1}] 층번호: {floor_num}, 용도: {floor_usage}, 기타용도: {floor_etc}")
                    # 모든 필드 출력
                    debug_info.append(f"    모든 필드: {list(floor_info.keys())}")
                    for key, value in floor_info.items():
                        if '층' in key or 'flr' in key.lower() or '용도' in key or 'purps' in key.lower():
                            debug_info.append(f"    {key}: {value}")

                debug_info.append(
                    f"\n=== 해당 층 ({floor if floor else 1}층) 찾기 ===")
                search_floor = floor if floor else 1
                for floor_info in floor_result['data']:
                    floor_num = floor_info.get(
                        'flrNoNm',
                        '') or floor_info.get(
                        'flrNo',
                        '') or floor_info.get(
                        'flrNoNm1',
                        '') or floor_info.get(
                        'flrNo1',
                        '')
                    floor_num_str = str(floor_num).strip()
                    search_floor_str = str(search_floor)

                    # 정확한 층 매칭
                    is_match = (floor_num_str == search_floor_str or
                                floor_num_str == f"{search_floor_str}층" or
                                floor_num_str == f"{search_floor_str}F" or
                                floor_num_str.startswith(f"{search_floor_str}층") or
                                (search_floor == 1 and ('1층' in floor_num_str or floor_num_str == '1' or floor_num_str.startswith('1층'))))

                    debug_info.append(
                        f"  층번호: '{floor_num}' (문자열: '{floor_num_str}') vs 찾는층: '{search_floor_str}' -> 매칭: {is_match}")

                    if is_match:
                        debug_info.append(
                            f"  ✓ 매칭됨! 해당 층 ({floor_num}) 용도: {
                                floor_info.get(
                                    'mainPurpsCdNm', '')}")
                        debug_info.append(
                            f"  ✓ 해당 층 ({floor_num}) 기타 용도: {
                                floor_info.get(
                                    'etcPurps', '')}")
                        break

            try:
                with open('usage_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_info))
            except BaseException:
                pass

            # 면적 비교 및 케이스 분석 (전유부 결과 포함)
            area_comparison = self._compare_areas(
                parsed, building, floor_result, area_result, floor, unit_result)

            # 면적 비교 정보 저장 (버튼 클릭 시 사용)
            self.current_area_comparison = area_comparison
            self.current_parsed = parsed
            self.current_registry_area = area_comparison.get(
                'registry_area') if area_comparison else None

            # 건축물대장 조회용 정보 저장
            self.current_building_info = building
            self.current_address_info = address_info

            # 블로그 필수표시사항 생성 (전유부 결과 포함)
            blog_lines, show_usage_warning, show_usage_mismatch_warning = self._generate_blog_text(
                parsed, building, floor_result, floor, usage_judgment, area_comparison, area_result, unit_result)

            # 주택 관련 용도일 경우 경고 다이얼로그 표시
            if show_usage_warning:
                messagebox.showwarning("경고", "건축물용도를 한번 더 확인해주세요!")

            # 입력값과 결과값 용도가 다를 경우 경고 다이얼로그 표시
            if show_usage_mismatch_warning:
                input_usage = parsed.get('usage', '')
                # 파싱된 용도가 없으면 원본 텍스트에서 직접 추출 시도
                if not input_usage:
                    try:
                        kakao_text = self.kakao_text.get(1.0, tk.END).strip()
                        # 원본 텍스트에서 용도 키워드 직접 검색
                        usage_keywords = [
                            '판매시설',
                            '기타판매시설',
                            '제1종',
                            '제2종',
                            '1종',
                            '2종',
                            '근생',
                            '근린',
                            '사무소',
                            '사무실',
                            '상가',
                            '점포',
                            '소매점',
                            '휴게음식점',
                            '일반음식점',
                            '학원']
                        for keyword in usage_keywords:
                            if keyword in kakao_text:
                                input_usage = keyword
                                break
                    except BaseException:
                        pass
                input_usage_normalized = self._normalize_usage(input_usage)
                # 결과값에서 중개대상물 종류 추출
                result_usage = usage_judgment.get('judged_usage', '확인요망')
                # blog_lines에서 중개대상물 종류 찾기
                for line in blog_lines:
                    if "중개대상물 종류:" in line:
                        result_usage = line.split("중개대상물 종류:")[-1].strip()
                        break
                # 입력 용도 표시 (정규화된 값이 있으면 그것을 사용, 없으면 원본 사용)
                input_usage_display = input_usage_normalized if input_usage_normalized else (
                    input_usage if input_usage else '확인요망')
                messagebox.showwarning("경고",
                                       f"입력하신 용도와 건축물대장 용도가 다릅니다!\n\n"
                                       f"입력하신 용도: {input_usage_display}\n"
                                       f"건축물대장 용도: {result_usage}\n\n"
                                       f"결과값은 건축물대장 기준으로 표시됩니다.")

            # 결과 텍스트에 삽입 (면적 클릭 가능 처리 포함)
            actual_area_value = None  # 실면적(계약면적)
            kakao_area_value = None  # 전용면적
            registry_area_value = None
            area_selection_active = False
            pending_area_line = None  # 전용면적 라인을 임시 저장

            for line in blog_lines:
                if line == "__WARNING_PYEONG__":
                    continue  # 플래그는 건너뛰기

                # 용도 불일치 마커는 중개대상물 종류 줄 삽입 시 이미 처리되었으므로 건너뛰기
                if line == "__USAGE_MISMATCH__":
                    continue
                # 확인 필요 마커도 중개대상물 종류 줄 삽입 시 이미 처리되었으므로 건너뛰기
                if line == "__USAGE_NEEDS_CHECK__":
                    continue

                # 화장실 경고 마커 확인 및 처리
                if line == "__BATHROOM_WARNING__":
                    # 이전 줄이 화장실 수 라인인지 확인하고 경고 문구 추가
                    current_content = self.result_text.get(1.0, tk.END)
                    if "화장실 수:" in current_content:
                        # 마지막 줄의 끝에 경고 문구 추가
                        warning_text = " (화장실 개수 확인 필요)"
                        start_pos = self.result_text.index(tk.END + "-1c")
                        self.result_text.insert(tk.END, warning_text + "\n")
                        end_pos = self.result_text.index(tk.END + "-2c")
                        # 경고 문구를 빨간색으로 표시
                        self.result_text.tag_add(
                            "bathroom_warning", start_pos, end_pos)
                        self.result_text.tag_config(
                            "bathroom_warning", foreground="red", font=(
                                '맑은 고딕', 10))
                    continue

                # 면적 선택 마커 확인
                if line == "__AREA_SELECTION__":
                    area_selection_active = True
                    continue
                elif line.startswith("__ACTUAL_AREA__"):
                    actual_area_value = line.replace(
                        "__ACTUAL_AREA__", "").replace(
                        "__", "")
                    try:
                        if actual_area_value and actual_area_value.strip():
                            actual_area_value = float(
                                actual_area_value.strip())
                        else:
                            actual_area_value = None
                    except (ValueError, TypeError):
                        actual_area_value = None
                    continue
                elif line.startswith("__KAKAO_AREA__"):
                    kakao_area_value = line.replace(
                        "__KAKAO_AREA__", "").replace(
                        "__", "")
                    try:
                        if kakao_area_value and kakao_area_value.strip():
                            kakao_area_value = float(kakao_area_value.strip())
                        else:
                            kakao_area_value = None
                    except (ValueError, TypeError):
                        kakao_area_value = None
                    continue
                elif line.startswith("__REGISTRY_AREA__"):
                    registry_area_value = line.replace(
                        "__REGISTRY_AREA__", "").replace("__", "")
                    try:
                        if registry_area_value and registry_area_value.strip():
                            registry_area_value = float(
                                registry_area_value.strip())
                        else:
                            registry_area_value = None
                    except (ValueError, TypeError):
                        registry_area_value = None
                    continue

                # 전용면적 라인 처리 (클릭 가능하게)
                if "전용면적:" in line:
                    # 접두사만 삽입하고 나머지는 _insert_clickable_area_line에서 처리
                    pending_area_line = line  # "• 전용면적: " 임시 저장
                    # 마커들이 모두 처리될 때까지 기다림 (다음 반복에서 처리)
                    continue

                # 전용면적 라인이 저장되어 있고, 마커 처리가 완료된 경우
                if pending_area_line and area_selection_active:
                    self.result_text.insert(
                        tk.END, pending_area_line)  # "• 전용면적: " 삽입
                    # 면적 값이 없어도 표시 (하나만 있어도 표시)
                    if actual_area_value is not None or kakao_area_value is not None or registry_area_value is not None:
                        self._insert_clickable_area_line(
                            "", actual_area_value, kakao_area_value, registry_area_value)
                    else:
                        # 면적 값이 없으면 확인요망 표시 (빨간색 굵은 글씨)
                        start_pos = self.result_text.index(tk.END + "-1c")
                        self.result_text.insert(tk.END, "확인요망\n")
                        end_pos = self.result_text.index(tk.END + "-2c")
                        self.result_text.tag_add(
                            "violation_warning", start_pos, end_pos)
                    pending_area_line = None
                    area_selection_active = False
                    actual_area_value = None
                    kakao_area_value = None
                    registry_area_value = None
                    continue

                # 전용면적 라인이 저장되어 있지만 마커가 없는 경우 (일반 텍스트)
                if pending_area_line:
                    self.result_text.insert(tk.END, pending_area_line + "\n")
                    pending_area_line = None
                    continue
                # 평수 경고가 있는 경우 빨간색 표시
                elif "카톡:" in line:
                    # "카톡: XX평" 부분을 빨간색으로 표시
                    kakao_start = line.find("카톡:")
                    if kakao_start != -1:
                        # 카톡 부분 이전까지 삽입
                        before_kakao = line[:kakao_start]
                        self.result_text.insert(tk.END, before_kakao)

                        # 카톡 부분을 빨간색으로 삽입
                        kakao_part = line[kakao_start:]
                        start_pos = self.result_text.index(tk.END + "-1c")
                        self.result_text.insert(tk.END, kakao_part + "\n")
                        # 줄 끝까지 태그 적용
                        end_pos = self.result_text.index(tk.END + "-2c")
                        self.result_text.tag_add("warning", start_pos, end_pos)
                # "중개대상물 종류:" 줄 처리 (용도 불일치 마커가 있으면 빨간색 굵은 글씨로 표시, 확인요망도 빨간색 굵은 글씨)
                elif "중개대상물 종류:" in line:
                    # 현재 라인의 인덱스를 확인하여 다음 줄에 마커가 있는지 확인
                    current_line_idx = blog_lines.index(line)
                    has_mismatch_marker = (current_line_idx +
                                           1 < len(blog_lines) and blog_lines[current_line_idx +
                                                                              1] == "__USAGE_MISMATCH__")
                    has_needs_check_marker = (current_line_idx +
                                              1 < len(blog_lines) and blog_lines[current_line_idx +
                                                                                 1] == "__USAGE_NEEDS_CHECK__")

                    # "확인요망"이 포함되어 있는지 확인
                    has_confirmation_needed = "확인요망" in line

                    if has_mismatch_marker or has_needs_check_marker or has_confirmation_needed:
                        # 빨간색 굵은 글씨로 삽입
                        start_pos = self.result_text.index(tk.END)
                        self.result_text.insert(tk.END, line + "\n")
                        end_pos = self.result_text.index(tk.END + "-1c")
                        # 빨간색 굵은 글씨 태그 적용
                        self.result_text.tag_add(
                            "usage_mismatch", start_pos, end_pos)
                    else:
                        # 일반 삽입
                        self.result_text.insert(tk.END, line + "\n")
                # "확인요망"이 포함된 모든 라인을 빨간색 굵은 글씨로 표시
                elif "확인요망" in line:
                    # "확인요망" 부분만 빨간색 굵은 글씨로 표시
                    warning_start = line.find("확인요망")
                    if warning_start != -1:
                        # "확인요망" 이전까지 삽입
                        before_warning = line[:warning_start]
                        self.result_text.insert(tk.END, before_warning)

                        # "확인요망" 부분을 빨간색 굵은 글씨로 삽입
                        warning_part = line[warning_start:]
                        start_pos = self.result_text.index(tk.END + "-1c")
                        self.result_text.insert(tk.END, warning_part + "\n")
                        end_pos = self.result_text.index(tk.END + "-2c")
                        # 빨간색 굵은 글씨 태그 적용
                        self.result_text.tag_add(
                            "violation_warning", start_pos, end_pos)
                else:
                    self.result_text.insert(tk.END, line + "\n")

            # 면적 불일치 시 버튼 추가 (기존 버튼 방식은 유지)
            if area_comparison and area_comparison.get('mismatch'):
                self._add_area_buttons(area_comparison, parsed)

            self.status_var.set("생성 완료")

        except Exception as e:
            messagebox.showerror("오류", f"처리 중 오류가 발생했습니다:\n{str(e)}")
            self.status_var.set("오류 발생")

    def _classify_usage_master(
            self,
            api_usage_str,
            area_m2,
            floor_result,
            floor,
            area_result,
            ho,
            unit_result):
        """
        중개대상물 종류 판정 마스터 함수 (3단계 프로세스)

        Args:
            api_usage_str: API에서 추출한 해당 층 용도(소분류) 문자열
            area_m2: 바닥면적(㎡)
            floor_result: 층별개요 조회 결과
            floor: 층수
            area_result: 전유공용면적 조회 결과
            ho: 호수
            unit_result: 전유부 조회 결과

        Returns:
            (final_usage, show_usage_warning, show_usage_warning_point)
            - final_usage: 최종 분류된 용도
            - show_usage_warning: 미분류 용도 경고 플래그
            - show_usage_warning_point: 점포 표시 플래그
        """
        show_usage_warning = False
        show_usage_warning_point = False

        # 사무소와 사무실은 동일하게 처리
        if api_usage_str:
            api_usage_str = api_usage_str.replace('사무실', '사무소')

        # 3단계: 출력 예외 규칙 (최우선 처리)
        # 1. "점포 및 주택" 복합 용도
        if api_usage_str and ('점포 및 주택' in api_usage_str or '주택 및 점포' in api_usage_str or (
                '점포' in api_usage_str and '주택' in api_usage_str and '및' in api_usage_str)):
            return (api_usage_str, True, False)  # 원문 그대로, 경고 플래그

        # 2. "점포"만 있는 경우 - 사용자 선택 필요
        if api_usage_str and api_usage_str.strip() == '점포':
            return ('__NEED_USAGE_SELECTION__', False, False)  # 선택 필요 마커

        # 3. 이미 법정 명칭이 포함된 경우 (제1종/제2종 근린생활시설 등)
        if api_usage_str:
            if '제1종근린생활시설' in api_usage_str or '제1종 근린생활시설' in api_usage_str:
                return ('제1종 근린생활시설', False, False)
            elif '제2종근린생활시설' in api_usage_str or '제2종 근린생활시설' in api_usage_str:
                return ('제2종 근린생활시설', False, False)

        # ★ 층별개요 용도 우선 처리 (법정 대분류로 매핑) ★
        # API에서 추출한 층별 용도가 있으면 우선적으로 대분류로 매핑
        if api_usage_str and area_m2:
            usage_lower = api_usage_str.lower()
            area = float(area_m2) if area_m2 else 0

            # 소매점 → 면적 기준 분류
            if '소매점' in usage_lower:
                if area < 1000:
                    return ('제1종 근린생활시설', False, False)
                else:
                    return ('판매시설', False, False)  # ✅ 1000㎡ 이상은 판매시설

            # 휴게음식점, 카페 → 면적 기준 분류
            if any(kw in usage_lower for kw in ['휴게음식점', '커피숍', '제과점', '카페']):
                if area < 300:
                    return ('제1종 근린생활시설', False, False)
                else:
                    return ('제2종 근린생활시설', False, False)

            # 일반음식점 → 무조건 제2종
            if '일반음식점' in usage_lower:
                return ('제2종 근린생활시설', False, False)

            # 사무소, 사무실 → 면적 기준 분류
            if '사무소' in usage_lower:
                if area < 30:
                    return ('제1종 근린생활시설', False, False)
                elif area < 500:
                    return ('제2종 근린생활시설', False, False)
                else:
                    return ('업무시설', False, False)

            # 학원, 교습소 → 면적 기준 분류
            if any(kw in usage_lower for kw in ['학원', '교습소']):
                if area < 500:
                    return ('제2종 근린생활시설', False, False)
                else:
                    return ('교육연구시설', False, False)

            # 노래연습장 → 제2종
            if '노래연습장' in usage_lower or '노래방' in usage_lower:
                return ('제2종 근린생활시설', False, False)

            # 의원, 치과, 한의원 → 제1종
            if any(kw in usage_lower for kw in ['의원', '치과', '한의원']):
                return ('제1종 근린생활시설', False, False)

            # 이용원, 미용원, 세탁소 → 제1종
            if any(
                kw in usage_lower for kw in [
                    '이용원',
                    '미용원',
                    '세탁소',
                    '미용실',
                    '이발소']):
                return ('제1종 근린생활시설', False, False)

            # 체육도장 → 면적 기준
            if '체육도장' in usage_lower or '헬스장' in usage_lower:
                if area < 500:
                    return ('제1종 근린생활시설', False, False)
                else:
                    return ('운동시설', False, False)

            # PC방, 게임장 → 면적 기준
            if 'pc방' in usage_lower or '게임장' in usage_lower:
                if area < 500:
                    return ('제2종 근린생활시설', False, False)
                else:
                    return ('위락시설', False, False)

        # 2단계: 28가지 대분류 매칭 규칙 (층별개요 용도가 없을 때)
        if not api_usage_str or not area_m2:
            return ("확인요망", False, False)

        usage_lower = api_usage_str.lower()
        area = float(area_m2) if area_m2 else 0

        # 0. 먼저 상업/업무 용도 키워드 확인 (주택 판정 오류 방지)
        commercial_keywords = ['점포', '소매점', '슈퍼마켓', '마트', '편의점', '상점', '매장',
                               '사무소', '사무실', '휴게음식점', '일반음식점', '카페', '커피숍',
                               '학원', '교습소', '노래연습장', '의원', '병원', '미용원', '이용원']
        has_commercial_keyword = any(
            keyword in usage_lower for keyword in commercial_keywords)

        # 1. 주택 판정 (상업 용도가 없을 때만)
        if not has_commercial_keyword:
            # 단독주택
            if any(
                kw in usage_lower for kw in [
                    '단독',
                    '단독주택',
                    '다중',
                    '다중주택',
                    '다가구',
                    '다가구주택',
                    '공관']):
                return ('단독주택', False, False)

            # 공동주택
            if any(
                kw in usage_lower for kw in [
                    '아파트',
                    '연립',
                    '연립주택',
                    '다세대',
                    '다세대주택',
                    '기숙사',
                    '공동주택']):
                return ('공동주택', False, False)

        # 2. 제1종 근린생활시설
        # 소매점(1000㎡ 미만)
        if any(
            kw in usage_lower for kw in [
                '소매점',
                '슈퍼마켓',
                '마트',
                '편의점',
                '상점',
                '매장',
                '일용품']) and area < 1000:
            return ('제1종 근린생활시설', False, False)
        # 휴게음식점/카페/제과점(300㎡ 미만)
        if any(
            kw in usage_lower for kw in [
                '휴게음식점',
                '커피숍',
                '제과점',
                '카페']) and area < 300:
            return ('제1종 근린생활시설', False, False)
        # 이용원, 미용원, 목욕장, 세탁소
        if any(
            kw in usage_lower for kw in [
                '이용원',
                '미용원',
                '목욕장',
                '세탁소',
                '미용실',
                '이발소']):
            return ('제1종 근린생활시설', False, False)
        # 의원, 치과, 한의원, 산후조리원
        if any(kw in usage_lower for kw in ['의원', '치과의원', '한의원', '산후조리원']):
            return ('제1종 근린생활시설', False, False)
        # 탁구장/체육도장(500㎡ 미만)
        if any(kw in usage_lower for kw in ['탁구장', '체육도장']) and area < 500:
            return ('제1종 근린생활시설', False, False)
        # 공공업무시설(1000㎡ 미만)
        if '공공업무시설' in usage_lower and area < 1000:
            return ('제1종 근린생활시설', False, False)
        # 사무소/중개사무소(30㎡ 미만)
        if any(kw in usage_lower for kw in ['사무소', '중개사무소']) and area < 30:
            return ('제1종 근린생활시설', False, False)

        # 3. 제2종 근린생활시설
        # 공연장/종교집회장(500㎡ 미만)
        if any(kw in usage_lower for kw in ['공연장', '종교집회장']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        # 자동차영업소(1000㎡ 미만)
        if '자동차영업소' in usage_lower and area < 1000:
            return ('제2종 근린생활시설', False, False)
        # 서점, 사진관, 동물병원
        if any(kw in usage_lower for kw in ['서점', '사진관', '동물병원']):
            return ('제2종 근린생활시설', False, False)
        # PC방/게임장(500㎡ 미만)
        if any(kw in usage_lower for kw in ['pc방', '게임장']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        # 휴게음식점/카페/제과점(300㎡ 이상)
        if any(
            kw in usage_lower for kw in [
                '휴게음식점',
                '커피숍',
                '제과점',
                '카페']) and area >= 300:
            return ('제2종 근린생활시설', False, False)
        # 일반음식점, 안마시술소, 노래연습장
        if any(kw in usage_lower for kw in ['일반음식점', '안마시술소', '노래연습장', '노래방']):
            return ('제2종 근린생활시설', False, False)
        # 단란주점(150㎡ 미만)
        if '단란주점' in usage_lower and area < 150:
            return ('제2종 근린생활시설', False, False)
        # 학원/교습소(500㎡ 미만)
        if any(kw in usage_lower for kw in ['학원', '교습소']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        # 운동시설(500㎡ 미만)
        if any(kw in usage_lower for kw in ['운동시설', '체육시설']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        # 사무소/중개사무소(30㎡~500㎡ 미만)
        if any(
            kw in usage_lower for kw in [
                '사무소',
                '중개사무소']) and 30 <= area < 500:
            return ('제2종 근린생활시설', False, False)
        # 고시원(500㎡ 미만)
        if '고시원' in usage_lower and area < 500:
            return ('제2종 근린생활시설', False, False)
        # 제조업소/수리점(500㎡ 미만)
        if any(kw in usage_lower for kw in ['제조업소', '수리점']) and area < 500:
            return ('제2종 근린생활시설', False, False)

        # 5. 문화 및 집회시설
        if (any(kw in usage_lower for kw in ['공연장', '집회장']) and area >= 300) or \
           (any(kw in usage_lower for kw in ['관람장']) and area >= 1000) or \
           any(kw in usage_lower for kw in ['전시장', '동식물원']):
            return ('문화 및 집회시설', False, False)

        # 6. 종교시설
        if any(kw in usage_lower for kw in ['종교집회장', '봉안당']) and area >= 300:
            return ('종교시설', False, False)

        # 7. 판매시설
        if any(
            kw in usage_lower for kw in [
                '농수산물도매시장',
                '대규모점포']) or (
            any(
                kw in usage_lower for kw in [
                    '소매점',
                    '슈퍼마켓',
                    '마트',
                    '편의점',
                    '상점',
                    '매장',
                    '일용품']) and area >= 1000) or (
                        any(
                            kw in usage_lower for kw in [
                                '오락실',
                                'pc방',
                                '게임장']) and area >= 500):
            return ('판매시설', False, False)

        # 8. 운수시설
        if any(kw in usage_lower for kw in ['여객자동차터미널', '철도', '공항', '항만시설']):
            return ('운수시설', False, False)

        # 9. 의료시설
        if any(
            kw in usage_lower for kw in [
                '병원',
                '종합병원',
                '치과병원',
                '한방병원',
                '격리병원',
                '전염병원',
                '정신병원',
                '요양소']):
            return ('의료시설', False, False)

        # 10. 교육연구시설
        if any(kw in usage_lower for kw in ['학교', '교육원', '연구소', '도서관']) or (
                '사설강습소' in usage_lower and '근생' not in usage_lower and '무도' not in usage_lower):
            return ('교육연구시설', False, False)

        # 11. 노유자시설
        if any(kw in usage_lower for kw in ['아동관련시설', '노인복지시설', '사회복지시설']):
            return ('노유자시설', False, False)

        # 12. 수련시설
        if any(kw in usage_lower for kw in ['청소년수련관', '수련원', '야영장', '유스호스텔']):
            return ('수련시설', False, False)

        # 13. 운동시설
        if (any(kw in usage_lower for kw in ['탁구장', '체육도장', '볼링장']) and area >= 500) or (
                any(kw in usage_lower for kw in ['체육관', '운동장']) and area >= 1000):
            return ('운동시설', False, False)

        # 14. 업무시설
        if any(kw in usage_lower for kw in ['국가청사', '지자체청사', '오피스텔']) or \
           (any(kw in usage_lower for kw in ['금융업소', '사무소']) and area >= 500):
            return ('업무시설', False, False)

        # 15. 숙박시설
        if any(kw in usage_lower for kw in ['호텔', '여관', '여인숙']) or \
           ('고시원' in usage_lower and area >= 500):
            return ('숙박시설', False, False)

        # 16. 위락시설
        if any(kw in usage_lower for kw in ['유흥음식점', '무도장']) or \
           ('단란주점' in usage_lower and area >= 150):
            return ('위락시설', False, False)

        # 17. 공장
        if any(kw in usage_lower for kw in ['제조', '가공', '수리']) and area >= 500:
            return ('공장', False, False)

        # 18. 창고시설
        if any(kw in usage_lower for kw in ['일반창고', '냉장창고', '냉동창고', '물류터미널']):
            return ('창고시설', False, False)

        # 19. 위험물 저장 및 처리시설
        if any(
            kw in usage_lower for kw in [
                '주유소',
                '석유판매소',
                '액화가스충전소',
                '위험물제조소']):
            return ('위험물 저장 및 처리시설', False, False)

        # 20. 자동차 관련시설
        if any(
            kw in usage_lower for kw in [
                '주차장',
                '세차장',
                '폐차장',
                '검사장',
                '정비공장',
                '정비학원']):
            return ('자동차 관련시설', False, False)

        # 21. 동물 및 식물 관련시설
        if any(
            kw in usage_lower for kw in [
                '축사',
                '도축장',
                '작물재배사',
                '종묘배양시설',
                '온실']):
            return ('동물 및 식물 관련시설', False, False)

        # 22. 분뇨 및 쓰레기 처리시설
        if any(kw in usage_lower for kw in ['고물상', '폐기물재활용', '폐기물감량화']):
            return ('분뇨 및 쓰레기 처리시설', False, False)

        # 23. 교정 및 군사시설
        if any(kw in usage_lower for kw in ['교정시설', '소년원', '국방시설', '군사시설']):
            return ('교정 및 군사시설', False, False)

        # 24. 방송통신시설
        if any(kw in usage_lower for kw in ['방송국', '촬영소', '통신용시설']):
            return ('방송통신시설', False, False)

        # 25. 발전시설
        if '발전소' in usage_lower:
            return ('발전시설', False, False)

        # 26. 묘지 관련 시설
        if any(
            kw in usage_lower for kw in [
                '화장시설',
                '봉안당']) and '종교시설' not in usage_lower or any(
                kw in usage_lower for kw in ['묘지부수건축물']):
            return ('묘지 관련 시설', False, False)

        # 27. 관광 휴게시설
        if any(kw in usage_lower for kw in ['야외음악당', '야외극장', '어린이회관', '휴게소']):
            return ('관광 휴게시설', False, False)

        # 28. 장례식장
        if '장례식장' in usage_lower:
            return ('장례식장', False, False)

        # 미분류 용도 처리 (3단계 예외 규칙)
        return (api_usage_str, True, False)  # 원문 그대로, 경고 플래그

    def get_approval_date(self, building):
        """
        건축물대장에서 사용승인일 추출 (모드A/B 공통 사용)

        Returns:
            str: 포맷팅된 사용승인일 (예: "2022.04.15") 또는 빈 문자열
        """
        use_apr_day = building.get(
            'useAprDay', '') or building.get(
            'pmsDay', '')
        if use_apr_day and str(use_apr_day).strip():
            return self._format_date(str(use_apr_day))
        return ''

    def get_total_floors(self, building):
        """
        건축물대장에서 총층수 추출 (모드A/B 공통 사용)

        Returns:
            int: 총층수 또는 0 (정보 없음)
        """
        total_floor = building.get(
            'grndFlrCnt',
            '') or building.get(
            'heit',
            '') or building.get(
            'flrCnt',
            '')
        if total_floor and str(total_floor).strip():
            try:
                return int(str(total_floor).strip())
            except BaseException:
                pass
        return 0

    def get_parking_count(self, building):
        """
        건축물대장에서 주차대수 추출 (모드A/B 공통 사용)

        Returns:
            int: 주차대수 (0 이상, 정보 없으면 0)
        """
        parking_spaces = None

        # 모든 주차 관련 필드 수집 및 합산
        parking_fields = {
            'indrAutoUtcnt': '자주식(실내)',
            'oudrAutoUtcnt': '자주식(실외)',
            'indrMechUtcnt': '기계식(실내)',
            'oudrMechUtcnt': '기계식(실외)',
        }

        additional_parking_patterns = [
            ('vicnty', '인근'),
            ('nearby', '인근'),
            ('elctr', '전기차'),
            ('ev', '전기차'),
            ('evChrg', '전기차'),
        ]

        try:
            total_parking = 0

            # 기본 필드 확인
            for field_name, display_name in parking_fields.items():
                value = building.get(field_name)
                if value is not None and str(value).strip() != '' and str(
                        value).strip().upper() != 'N/A':
                    try:
                        cnt = int(float(str(value).strip()))
                        if cnt > 0:
                            total_parking += cnt
                    except BaseException:
                        pass

            # 추가 필드 탐색
            if building and isinstance(building, dict):
                for key, value in building.items():
                    if key in parking_fields:
                        continue

                    key_lower = key.lower()
                    is_parking_field = False

                    for pattern, label in additional_parking_patterns:
                        if pattern in key_lower and (
                                'utcnt' in key_lower or 'cnt' in key_lower or '대' in key):
                            is_parking_field = True
                            break

                    if is_parking_field and value is not None and str(
                            value).strip() != '':
                        try:
                            cnt = int(float(str(value).strip()))
                            if cnt > 0:
                                total_parking += cnt
                        except BaseException:
                            pass

            if total_parking >= 0:
                parking_spaces = total_parking
        except BaseException:
            pass

        # 위 방법으로 찾지 못한 경우
        if parking_spaces is None:
            alt_fields = [
                'prkplnNo',
                'prkplnCnt',
                'prkgCnt',
                'parkingCnt',
                'totPrkgCnt']
            for field in alt_fields:
                value = building.get(field)
                if value is not None and str(value).strip() != '':
                    try:
                        num_val = int(float(str(value).strip()))
                        if num_val >= 0:
                            parking_spaces = num_val
                            break
                    except BaseException:
                        pass

        # 키워드 기반 검색
        if parking_spaces is None and building and isinstance(building, dict):
            for key, value in building.items():
                key_lower = key.lower()
                if ('주차' in key or 'prkg' in key_lower or 'parking' in key_lower or 'auto' in key_lower):
                    if ('cnt' in key_lower or 'utcnt' in key_lower or '수' in key or '대' in key):
                        if value is not None and str(value).strip() != '':
                            try:
                                num_val = int(float(str(value).strip()))
                                if num_val >= 0:
                                    parking_spaces = num_val
                                    break
                            except BaseException:
                                pass

        # 최종 반환 (None이면 0)
        if parking_spaces is not None and parking_spaces >= 0:
            return parking_spaces
        else:
            return 0

    def _judge_usage(
            self,
            building,
            parsed,
            floor_result,
            floor,
            area_result=None):
        """용도 판정 로직 - 건축물대장 면적과 용도 분류 기준을 대조하여 법정 명칭으로 판정"""
        # ✅ 디버그: 입력 파라미터 확인
        print(
            f"🔍 [_judge_usage] 호출됨: floor={floor}, parsed.get('ho')={
                parsed.get('ho')}")

        # 우선순위: 1) 전유공용면적 API (호수별 용도) 2) 층별개요 API (층별 용도)
        api_usage = None
        etc_usage = None
        search_floor = floor if floor else 1
        ho = parsed.get('ho')

        print(f"🔍 [_judge_usage] search_floor={search_floor}, ho={ho}")

        # 1. 호수가 있으면 전유공용면적 API에서 용도 우선 확인 (집합건물)
        if ho and area_result and area_result.get(
                'success') and area_result.get('data'):
            print(f"🔍 [_judge_usage] 전유공용면적 API에서 호수별 용도 확인: ho={ho}")
            unit_area, unit_usage = self._get_unit_area_and_usage(
                ho, area_result, floor_result, floor)
            print(
                f"🔍 [_judge_usage] _get_unit_area_and_usage 반환값: unit_area={unit_area}, unit_usage={unit_usage}")
            if unit_usage:
                # 전유부 용도를 mainPurps와 etcPurps로 분리
                # unit_usage는 "소매점", "점포" 등이 될 수 있음
                api_usage = str(unit_usage).strip()
                print(f"   ✅ 전유부 주용도 사용: api_usage='{api_usage}'")
                # etc_usage는 전유공용면적 API의 etcPurps에서 가져오기
                for area_info in area_result['data']:
                    ho_nm = area_info.get('hoNm', '')
                    ho_normalized = str(ho).replace('호', '').strip()
                    ho_nm_normalized = str(ho_nm).replace('호', '').strip()
                    print(
                        f"   🔍 호수 매칭 확인: ho_normalized={ho_normalized}, ho_nm_normalized={ho_nm_normalized}")
                    if ho_normalized == ho_nm_normalized:
                        main_purps = area_info.get('mainPurpsCdNm', '')
                        etc_purps = area_info.get('etcPurps', '')
                        print(
                            f"   🔍 전유부 데이터: mainPurpsCdNm={main_purps}, etcPurps={etc_purps}")
                        if etc_purps and str(etc_purps).strip() != str(
                                unit_usage).strip():
                            etc_usage = str(etc_purps).strip()
                            print(f"   ✅ 전유부 기타용도 사용: etc_usage='{etc_usage}'")
                        break
            else:
                print(f"   ⚠️ 전유부 용도 없음 → 층별개요로 fallback")

        # 2. 층별개요에서 해당 층의 모든 용도 정보 찾기 (전유부에서 못 찾았을 때만)
        # 한 층에 여러 용도가 있을 수 있으므로 모두 수집
        api_usage_list = []  # 해당 층의 모든 주용도
        etc_usage_list = []  # 해당 층의 모든 기타 용도

        # 전유부 용도가 있으면 리스트에 추가
        if api_usage:
            api_usage_list.append(api_usage)
        if etc_usage:
            etc_usage_list.append(etc_usage)

        # 전유부 용도가 없을 때만 층별개요 확인
        if not api_usage and floor_result and floor_result.get(
                'success') and floor_result.get('data'):
            print(
                f"🔍 층별개요 루프 시작: search_floor={search_floor}, 총 {len(floor_result['data'])}개 층")
            for floor_info in floor_result['data']:
                # 층 번호 필드 여러 개 시도
                floor_num = (floor_info.get('flrNoNm', '') or
                             floor_info.get('flrNo', '') or
                             floor_info.get('flrNoNm1', '') or
                             floor_info.get('flrNo1', '') or
                             floor_info.get('flrNoNm2', '') or
                             floor_info.get('flrNo2', ''))

                floor_num_str = str(floor_num).strip()
                search_floor_str = str(search_floor)
                print(
                    f"   👉 확인중: floor_num_str='{floor_num_str}', search_floor={search_floor}, is_negative={
                        search_floor < 0}")

                # 정확한 층 매칭: "4층", "4", "4F" 등 형식 모두 처리
                # 층 번호가 정확히 일치하는지 확인 (부분 매칭 방지)
                # "4층"이 "14층"에 매칭되지 않도록 주의
                is_match = False

                # 지하층 처리 (search_floor가 음수인 경우)
                if search_floor < 0:
                    basement_floor_num = abs(search_floor)  # -1 -> 1
                    print(
                        f"      🔵 지하층 매칭 시도: floor_num_str='{floor_num_str}', basement={basement_floor_num}")
                    # "지하1층", "지하1", "지1층", "지1", "B1", "B1F", "b1", "지하1F" 등과 매칭
                    if (floor_num_str == f"지하{basement_floor_num}층" or
                        floor_num_str == f"지하{basement_floor_num}" or
                        # "지1층" 추가
                        floor_num_str == f"지{basement_floor_num}층" or
                        # "지1" 추가
                        floor_num_str == f"지{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}f" or
                        floor_num_str == f"지하{basement_floor_num}F" or
                        floor_num_str == f"-{basement_floor_num}" or
                        floor_num_str == f"-{basement_floor_num}층" or
                            floor_num_str == f"-{basement_floor_num}F"):
                        is_match = True
                        print(
                            f"         ✅ 지하층 매칭 성공! floor_num_str='{floor_num_str}'")
                # 지상층 처리 (search_floor가 양수인 경우)
                else:
                    # 1. 정확히 일치
                    if floor_num_str == search_floor_str:
                        is_match = True
                    # 2. "4층" 형식
                    elif floor_num_str == f"{search_floor_str}층":
                        is_match = True
                    # 3. "4F" 형식
                    elif floor_num_str == f"{search_floor_str}F":
                        is_match = True
                    # 4. "4층"으로 시작 (하지만 "14층"과 구분)
                    elif floor_num_str.startswith(f"{search_floor_str}층"):
                        # 앞에 숫자가 없어야 함 (예: "4층"은 OK, "14층"은 NO)
                        if len(floor_num_str) == len(f"{search_floor_str}층") or (len(floor_num_str) > len(
                                f"{search_floor_str}층") and not floor_num_str[len(f"{search_floor_str}층") - 1].isdigit()):
                            is_match = True
                    # 5. 1층 특수 처리
                    elif search_floor == 1:
                        if ('1층' in floor_num_str and '11층' not in floor_num_str and '21층' not in floor_num_str) or floor_num_str == '1' or floor_num_str.startswith(
                                '1층'):
                            is_match = True

                if is_match:
                    # 해당 층의 용도 정보 (여러 필드명 시도)
                    main_usage = (floor_info.get('mainPurpsCdNm', '') or
                                  floor_info.get('mainPurps', '') or
                                  floor_info.get('mainPurpsCdNm1', '') or
                                  floor_info.get('mainPurps1', ''))
                    other_usage = (
                        floor_info.get(
                            'etcPurps',
                            '') or floor_info.get(
                            'etcPurps1',
                            ''))  # 기타 용도 (예: 휴게음식점)

                    print(
                        f"         ✅ 용도 추출: main_usage='{main_usage}', other_usage='{other_usage}'")

                    # 중복 제거하면서 추가
                    if main_usage and main_usage not in api_usage_list:
                        api_usage_list.append(main_usage)
                        print(
                            f"            ➕ api_usage_list에 추가: {main_usage}")
                    if other_usage and other_usage not in etc_usage_list:
                        etc_usage_list.append(other_usage)
                        print(
                            f"            ➕ etc_usage_list에 추가: {other_usage}")

        # 리스트를 문자열로 변환 (여러 개면 쉼표로 구분)
        # 전유부 용도가 이미 있으면 유지, 없으면 리스트에서 생성
        if not api_usage:
            api_usage = ', '.join(api_usage_list) if api_usage_list else None
        if not etc_usage:
            etc_usage = ', '.join(etc_usage_list) if etc_usage_list else None

        print(
            f"🔍 [_judge_usage] 최종 용도: api_usage='{api_usage}', etc_usage='{etc_usage}'")

        # 해당 층 용도 정보가 없으면 None 유지 (표제부 용도는 사용하지 않음)
        # 표제부 용도는 건물 전체 용도이므로 해당 층 용도로 사용하면 부정확함

        # 카톡에서 추출한 용도 (약어는 무시하고 참고용으로만 사용)
        kakao_usage = parsed.get('usage', '')
        kakao_usage_detail = parsed.get('usage_detail', '')

        # 건축물대장에서 해당 층의 면적 가져오기 (우선순위: area_result > parsed)
        area_m2 = None
        if area_result and area_result.get(
                'success') and area_result.get('data'):
            search_floor = floor if floor else 1
            for area_info in area_result['data']:
                floor_num = area_info.get(
                    'flrNoNm',
                    '') or area_info.get(
                    'flrNo',
                    '') or area_info.get(
                    'flrNo1',
                    '')
                floor_num_str = str(floor_num).strip()
                search_floor_str = str(search_floor)

                # 정확한 층 매칭
                is_area_match = False

                # 지하층 처리
                if search_floor < 0:
                    basement_floor_num = abs(search_floor)
                    print(
                        f"🔍 지하층: search_floor={search_floor}, basement={basement_floor_num}, floor_num_str='{floor_num_str}'")
                    if (floor_num_str == f"지하{basement_floor_num}층" or
                        floor_num_str == f"지하{basement_floor_num}" or
                        # "지1층" 추가
                        floor_num_str == f"지{basement_floor_num}층" or
                        # "지1" 추가
                        floor_num_str == f"지{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}f" or
                        floor_num_str == f"지하{basement_floor_num}F" or
                        floor_num_str == f"-{basement_floor_num}" or
                        floor_num_str == f"-{basement_floor_num}층" or
                            floor_num_str == f"-{basement_floor_num}F"):
                        is_area_match = True
                # 지상층 처리
                else:
                    if (floor_num_str == search_floor_str or
                        floor_num_str == f"{search_floor_str}층" or
                        floor_num_str == f"{search_floor_str}F" or
                        floor_num_str.startswith(f"{search_floor_str}층") or
                            (search_floor == 1 and ('1층' in floor_num_str or floor_num_str == '1' or floor_num_str.startswith('1층')))):
                        is_area_match = True

                if is_area_match:
                    # 전용면적 필드 찾기
                    exclusive_area_fields = [
                        'exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                        'exclTotArea', 'exclTotArea1', 'exclTotArea2',
                        '전용면적', '전용면적1', '전용면적2'
                    ]
                    for field in exclusive_area_fields:
                        exclusive_area = area_info.get(field, '')
                        if exclusive_area:
                            try:
                                area_m2 = float(str(exclusive_area).strip())
                                if area_m2 > 0:
                                    break
                            except BaseException:
                                pass
                    if area_m2:
                        break

        # 건축물대장 면적이 없으면 카톡 면적 사용
        if not area_m2:
            area_m2 = parsed.get('area_m2')

        # 전용면적이 없으면 실면적(계약면적) 사용
        if not area_m2:
            area_m2 = parsed.get('actual_area_m2')

        # 건축물대장에서 연면적, 층수, 세대수 등 추가 정보 가져오기
        total_area = building.get(
            'totArea',
            '') or building.get(
            'totArea1',
            '')  # 연면적
        grnd_flr_cnt = building.get('grndFlrCnt', '')  # 지상층수
        hhld_cnt = building.get(
            'hhldCnt',
            '') or building.get(
            'hhldCnt1',
            '')  # 세대수

        try:
            total_area = float(str(total_area).strip()) if total_area else None
            grnd_flr_cnt = int(float(str(grnd_flr_cnt).strip())
                               ) if grnd_flr_cnt else None
            hhld_cnt = int(float(str(hhld_cnt).strip())) if hhld_cnt else None
        except BaseException:
            total_area = None
            grnd_flr_cnt = None
            hhld_cnt = None

        judgment = {
            'api_usage': api_usage,
            'etc_usage': etc_usage,
            'kakao_usage': kakao_usage,
            'judged_usage': None,
            'area_m2': area_m2,
            'total_area': total_area,
            'grnd_flr_cnt': grnd_flr_cnt,
            'hhld_cnt': hhld_cnt
        }

        # 모든 용도 정보를 문자열로 변환
        api_usage_str = str(api_usage) if api_usage else ''
        etc_usage_str = str(etc_usage) if etc_usage else ''
        kakao_usage_str = str(kakao_usage) if kakao_usage else ''
        # 사무실을 사무소로 통일
        api_usage_str = api_usage_str.replace('사무실', '사무소')
        etc_usage_str = etc_usage_str.replace('사무실', '사무소')
        kakao_usage_str = kakao_usage_str.replace('사무실', '사무소')

        # api_usage_str과 etc_usage_str을 합쳐서 하나의 문자열로 만들기
        # etc_usage_str에 명확한 법정 용도(근린생활시설 등)가 있으면 우선 사용
        print(
            f"🔍 용도 문자열: api_usage_str='{api_usage_str}', etc_usage_str='{etc_usage_str}'")
        if etc_usage_str and (
                '근린생활시설' in etc_usage_str or '제1종' in etc_usage_str or '제2종' in etc_usage_str):
            # etc_usage에 법정 명칭이 있으면 이것을 우선 사용
            usage_str_for_classify = etc_usage_str
            print(f"   ✅ etc_usage 우선 사용: '{usage_str_for_classify}'")
        else:
            # 그 외의 경우 api_usage를 우선하고 etc_usage를 추가
            usage_str_for_classify = api_usage_str
            if etc_usage_str:
                if usage_str_for_classify:
                    usage_str_for_classify = f"{usage_str_for_classify}, {etc_usage_str}"
                else:
                    usage_str_for_classify = etc_usage_str
            print(f"   ⚪ api_usage 사용: '{usage_str_for_classify}'")

        # 호수 정보 가져오기
        ho = parsed.get('ho')

        # _classify_usage_master 함수 호출하여 용도 판정
        print(
            f"🔍 _classify_usage_master 호출: usage_str='{usage_str_for_classify}', area_m2={area_m2}")
        final_usage, show_usage_warning_flag, show_usage_warning_point_flag = self._classify_usage_master(
            usage_str_for_classify, area_m2, floor_result, floor, area_result, ho, None)
        print(
            f"   ✅ 최종 판정: final_usage='{final_usage}', show_warning={show_usage_warning_flag}")
        print(
            f"   📊 판정 근거: usage_str_for_classify='{usage_str_for_classify}', area_m2={area_m2}, floor={floor}")

        # 판정 결과를 judgment에 저장
        judgment['judged_usage'] = final_usage
        judgment['show_usage_warning'] = show_usage_warning_flag  # 경고 플래그 추가
        # 점포 표시 플래그 추가
        judgment['show_usage_warning_point'] = show_usage_warning_point_flag

        return judgment

    def _compare_areas(
            self,
            parsed,
            building,
            floor_result,
            area_result,
            floor,
            unit_result=None,
            selected_units_info=None):
        """건축물대장 해당 층 전용면적과 카카오톡 매물 면적 비교 (호수 포함, 전유부 우선)"""
        kakao_area = parsed.get('area_m2')
        if not kakao_area:
            return None

        # 계약면적 추출 (입력 검증용)
        actual_area_m2 = parsed.get('actual_area_m2')

        # 해당 층의 전용면적 찾기 (호수 우선, 전유부 우선)
        registry_area = None
        search_floor = floor if floor else 1
        ho = parsed.get('ho')  # 호수 정보 가져오기

        # 디버깅: 입력 정보 출력
        print(
            f"🔍 [_compare_areas] kakao_area={kakao_area}, actual_area_m2={
                parsed.get('actual_area_m2')}, floor={floor}, ho={
                parsed.get('ho')}, selected_units_info={selected_units_info}")

        # 🔥 사용자가 선택한 전유부분 정보가 있으면 최우선으로 사용
        if selected_units_info and selected_units_info.get("area"):
            registry_area = selected_units_info["area"]
            print(
                f"🎯 [_compare_areas] 선택된 전유부분 면적 사용: registry_area={registry_area}㎡")
        else:
            # _get_floor_area_from_api를 사용하여 면적 찾기 (일관성 있는 방법)
            registry_area = self._get_floor_area_from_api(
                floor_result, floor, area_result, ho, unit_result)
            print(
                f"🔍 [_compare_areas] _get_floor_area_from_api 결과: registry_area={registry_area}")

        # 못 찾았으면 기존 로직 시도
        if not registry_area:
            print(f"🔍 [_compare_areas] 기존 로직으로 재시도")

            # 1. 전유부 조회 결과에서 호수별 면적 찾기 (최우선)
            if ho and unit_result and unit_result.get(
                    'success') and unit_result.get('data'):
                print(f"🔍 [_compare_areas] 전유부 조회 시작: ho={ho}")
                # 호수 정규화 (입력된 호수에서 "호" 제거)
                ho_normalized = str(ho).replace('호', '').strip()

                for unit_info in unit_result['data']:
                    # 호수 필드 찾기 (여러 가능한 필드명 시도)
                    ho_fields = [
                        'ho',
                        'hoNo',
                        'hoNm',
                        'hoNoNm',
                        '호수',
                        '호',
                        'unitNo',
                        'unit',
                        'dongNo',
                        'dongNm',
                        'hoStr',
                        'hoStrNm']
                    unit_ho = None

                    for ho_field in ho_fields:
                        ho_value = unit_info.get(ho_field, '')
                        if ho_value:
                            ho_value_str = str(ho_value).strip()

                            # 호수 매칭 (다양한 형식 지원)
                            ho_value_normalized = ho_value_str.replace(
                                '호', '').strip()

                            # 정확히 일치하거나, 정규화된 값이 일치하거나, 시작 부분이 일치하는지 확인
                            if (ho == ho_value_str or
                                ho_normalized == ho_value_normalized or
                                ho_value_normalized.startswith(ho_normalized) or
                                    ho_normalized.startswith(ho_value_normalized)):
                                unit_ho = ho_value_str
                                break

                    # 호수가 매칭되면 해당 호수의 면적 사용
                    if unit_ho:
                        # 전용면적 필드 찾기 (더 많은 필드명 시도)
                        exclusive_area_fields = [
                            'exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                            'exclTotArea', 'exclTotArea1', 'exclTotArea2',
                            '전용면적', '전용면적1', '전용면적2',
                            'area', 'area1', 'area2', 'totArea', 'totArea1',
                            'exclAreaNm', 'exclTotAreaNm', 'areaNm'
                        ]

                        for field in exclusive_area_fields:
                            exclusive_area = unit_info.get(field, '')
                            if exclusive_area:
                                try:
                                    area_val = float(
                                        str(exclusive_area).strip())
                                    if area_val > 0:
                                        registry_area = area_val
                                        break
                                except BaseException:
                                    pass

                        # 면적 필드를 찾지 못한 경우, 모든 필드에서 면적 관련 값 검색
                        if not registry_area:
                            for key, value in unit_info.items():
                                if value and str(value).strip():
                                    key_lower = key.lower()
                                    value_str = str(value).strip()
                                    # 면적 관련 키워드가 포함된 필드 확인
                                    if ('면적' in key or 'area' in key_lower) and (
                                            '전용' in key or 'excl' in key_lower):
                                        try:
                                            area_val = float(value_str)
                                            if area_val > 0:
                                                registry_area = area_val
                                                break
                                        except BaseException:
                                            pass

                        if registry_area:
                            break

        # 2. 전유공용면적 조회 결과에서 해당 층의 전용면적 찾기 (호수 우선, 전유 필터링 필수)
        print(
            f"🔍 [_compare_areas] area_result 확인: success={
                area_result.get('success') if area_result else None}, has_data={
                bool(
                    area_result.get('data')) if area_result else False}")
        if area_result and area_result.get('data'):
            print(
                f"🔍 [_compare_areas] area_result data_count={len(area_result['data'])}")

        if not registry_area and area_result and area_result.get(
                'success') and area_result.get('data'):
            print(
                f"🔍 [_compare_areas] 전유공용면적 조회 시작: data_count={len(area_result['data'])}")
            for area_info in area_result['data']:
                # 전유공용구분 필드 확인 (전유만 필터링) - 먼저 확인하여 공용 데이터는 제외
                pubuse_gbn = (area_info.get('exposPubuseGbCdNm', '') or
                              area_info.get('pubuseGbCdNm', '') or
                              area_info.get('pubuseGbn', '') or
                              area_info.get('pubuseGbCd', ''))
                is_exclusive = False
                if pubuse_gbn:
                    pubuse_gbn_str = str(pubuse_gbn).strip()
                    if '전유' in pubuse_gbn_str or 'exclusive' in pubuse_gbn_str.lower():
                        is_exclusive = True
                else:
                    # 필드가 없으면 exposPubuseGbCd 값으로 확인 (1=전유, 2=공용)
                    expos_pubuse_cd = area_info.get('exposPubuseGbCd', '')
                    if str(expos_pubuse_cd) == '1':
                        is_exclusive = True
                    elif str(expos_pubuse_cd) == '2':
                        is_exclusive = False

                # 층 번호 추출
                floor_num = area_info.get(
                    'flrNoNm',
                    '') or area_info.get(
                    'flrNo',
                    '') or area_info.get(
                    'flrNo1',
                    '')

                print(
                    f"   🔍 항목: floor={floor_num}, pubuse_gbn={pubuse_gbn}, is_exclusive={is_exclusive}")

                # 전유만 처리 (공용은 제외)
                if not is_exclusive:
                    print(f"   ⏭️ 공용 데이터 건너뛰기")
                    continue  # 공용 데이터는 건너뛰기
                floor_num_str = str(floor_num).strip()
                search_floor_str = str(search_floor)

                # 정확한 층 매칭 (지상1 등 처리)
                is_match = False
                # 숫자만 추출 (예: "지상1" → "1", "1층" → "1")
                floor_num_only = re.sub(r'[^0-9]', '', floor_num_str)
                search_floor_only = str(search_floor)

                if floor_num_str == search_floor_str:
                    is_match = True
                elif floor_num_only == search_floor_only:
                    # 숫자가 같으면 매칭 (지상1 → 1, 지하1 → 1 구분 필요)
                    if search_floor == 1:
                        # 1층인 경우: "지상1"은 매칭, "지하1"은 제외
                        if '지상' in floor_num_str and '지하' not in floor_num_str:
                            is_match = True
                        elif '지하' not in floor_num_str and floor_num_str == '1':
                            is_match = True
                    else:
                        # 1층이 아닌 경우: "지상"이 포함되어 있으면 매칭
                        if '지상' in floor_num_str and '지하' not in floor_num_str:
                            is_match = True
                elif floor_num_str == f"{search_floor_str}층":
                    is_match = True
                elif floor_num_str == f"지상{search_floor_str}" or floor_num_str == f"지상{search_floor_str}층":
                    is_match = True
                elif floor_num_str == f"{search_floor_str}F":
                    is_match = True
                elif floor_num_str.startswith(f"{search_floor_str}층"):
                    if len(floor_num_str) == len(f"{search_floor_str}층") or (len(floor_num_str) > len(
                            f"{search_floor_str}층") and not floor_num_str[len(f"{search_floor_str}층") - 1].isdigit()):
                        is_match = True
                elif search_floor == 1:
                    if ('지상1' in floor_num_str or '1층' in floor_num_str) and '지하' not in floor_num_str:
                        if '11층' not in floor_num_str and '21층' not in floor_num_str:
                            is_match = True
                    elif floor_num_str == '1' and '지하' not in floor_num_str:
                        is_match = True

                if is_match:
                    print(
                        f"🔍 [_compare_areas] 층 매칭 성공! floor_num_str={floor_num_str}, search_floor={search_floor}")
                    # 전유 항목이고 층 매칭 완료 - 호수 매칭 확인 후 면적 추출
                    # 호수가 있으면 호수 매칭 확인 (전유 데이터만 처리)
                    ho_matched = True  # 호수가 없으면 매칭된 것으로 간주
                    if ho:
                        ho_normalized = str(ho).replace('호', '').strip()
                        ho_nm = area_info.get('hoNm', '')
                        if ho_nm:
                            ho_nm_str = str(ho_nm).strip().replace(
                                '호', '').strip()
                            # 호수가 매칭되지 않으면 건너뛰기 (다음 항목 확인)
                            if ho_nm_str != ho_normalized:
                                ho_matched = False
                                continue  # 호수 불일치 - 다음 항목 확인
                        else:
                            # 호수가 있는데 hoNm이 없으면 매칭 실패로 간주
                            ho_matched = False
                            continue  # hoNm 없음 - 다음 항목 확인

                    # 호수 매칭 완료 (또는 호수 없음) - 면적 추출
                    if ho_matched:
                        print(
                            f"   ✅ 호수 매칭 성공! area_info keys: {
                                list(
                                    area_info.keys())}")
                        # 전유공용면적 조회 API의 'area' 필드 우선 사용 (전유 면적)
                        area_val = area_info.get('area', '')
                        print(f"   🔍 area 필드: {area_val}")
                        if area_val:
                            try:
                                area_float = float(str(area_val).strip())
                                if area_float > 0:
                                    registry_area = area_float
                                    break
                            except (ValueError, TypeError):
                                pass

                        # area 필드가 없으면 다른 필드 시도
                        if not registry_area:
                            exclusive_area_fields = [
                                'exclArea',
                                'exclArea1',
                                'exclArea2',
                                'exclArea3',
                                'exclTotArea',
                                'exclTotArea1',
                                'exclTotArea2',
                                '전용면적',
                                '전용면적1',
                                '전용면적2']
                            for field in exclusive_area_fields:
                                exclusive_area = area_info.get(field, '')
                                if exclusive_area:
                                    try:
                                        registry_area = float(
                                            str(exclusive_area).strip())
                                        if registry_area > 0:
                                            break
                                    except (ValueError, TypeError):
                                        pass

                        if registry_area:
                            print(
                                f"✅ [_compare_areas] 전유공용면적에서 registry_area 발견: {registry_area}㎡")
                            break

        if not registry_area:
            print(f"⚠️ [_compare_areas] 전유공용면적에서 registry_area 못 찾음")

        # 층별개요에서도 시도 (정확한 층 매칭)
        if registry_area is None and floor_result and floor_result.get(
                'success') and floor_result.get('data'):
            print(
                f"🔍 [_compare_areas] 층별개요 조회 시작: data_count={len(floor_result['data'])}")
            for floor_info in floor_result['data']:
                floor_num = floor_info.get(
                    'flrNoNm', '') or floor_info.get(
                    'flrNo', '')
                floor_num_str = str(floor_num).strip()
                search_floor_str = str(search_floor)

                # 정확한 층 매칭
                if (floor_num_str == search_floor_str or
                    floor_num_str == f"{search_floor_str}층" or
                    floor_num_str == f"{search_floor_str}F" or
                    floor_num_str.startswith(f"{search_floor_str}층") or
                        (search_floor == 1 and ('1층' in floor_num_str or floor_num_str == '1' or floor_num_str.startswith('1층')))):
                    # 면적 관련 필드 찾기
                    for key, value in floor_info.items():
                        if value and str(value).strip():
                            key_lower = key.lower()
                            # 전용면적 관련 필드
                            if (('면적' in key or 'area' in key_lower) and (
                                    '전용' in key or 'excl' in key_lower or 'tot' in key_lower)):
                                try:
                                    area_val = float(str(value).strip())
                                    if area_val > 0:
                                        registry_area = area_val
                                        break
                                except BaseException:
                                    pass
                    if registry_area:
                        break

        # 계약면적 검증: 입력한 계약면적 vs 건축물대장 해당 층 면적
        input_error_detected = False
        suggested_area = None

        if actual_area_m2 and registry_area:
            # 디버깅: 검증 값 출력
            print(
                f"🔍 [계약면적 검증] actual_area_m2={actual_area_m2}, registry_area={registry_area}, kakao_area={kakao_area}")

            # 입력한 계약면적이 건축물대장의 해당 층 면적보다 크면 입력 오류
            # registry_area: 건축물대장의 해당 층 전용면적
            # 1% 여유만 허용 (측정 오차 고려)
            if actual_area_m2 > registry_area * 1.01:
                input_error_detected = True
                # 전용면적을 제안 (사용자가 계약면적과 전용면적을 바꿔 적었을 가능성)
                suggested_area = kakao_area
                print(
                    f"⚠️ [계약면적 검증] 입력 오류 감지! actual_area_m2({actual_area_m2}) > registry_area({registry_area})")
            else:
                print(f"✅ [계약면적 검증] 정상 (오류 없음)")

        # registry_area가 None이면 면적 비교 불가 → 경고 정보 반환
        if registry_area is None:
            print(f"❌ [_compare_areas] registry_area를 찾지 못함 → 경고 정보 반환")
            error_comparison = {
                'kakao_area': kakao_area,
                'registry_area': None,
                'not_found': True,
                'mismatch': False,
                'rental_type': None,
                'actual_area_m2': actual_area_m2,
                'input_error_detected': False,
                'suggested_area': None
            }
            # 층/호수 찾기 정보 추가
            if hasattr(self, '_floor_search_info'):
                error_comparison['floor_search_info'] = self._floor_search_info
            return error_comparison

        print(f"✅ [_compare_areas] 최종 registry_area={registry_area}㎡")

        # 면적 비교
        diff = abs(kakao_area - registry_area)
        diff_percent = (diff / registry_area * 100) if registry_area > 0 else 0

        comparison = {
            'kakao_area': kakao_area,
            'registry_area': registry_area,
            'diff': diff,
            'diff_percent': diff_percent,
            'mismatch': diff > 0.1,  # 0.1㎡ 이상 차이면 불일치
            'case': None,
            'case_a': False,
            'case_b': False,
            'rental_type': None,  # 분할임대/통임대 여부
            'actual_area_m2': actual_area_m2,  # 계약면적
            'input_error_detected': input_error_detected,  # 입력 오류 감지
            'suggested_area': suggested_area  # 제안 면적 (전용면적)
        }

        if comparison['mismatch']:
            # Case B: 매물 면적이 대장상 면적보다 명확히 작을 때 (분할임대 가능성)
            # 10% 이상 작으면 Case B (분할임대)로 판단
            if kakao_area < registry_area and (
                    registry_area - kakao_area) / registry_area >= 0.1:
                comparison['case'] = 'B'
                comparison['case_b'] = True
                comparison['rental_type'] = '분할임대'
            # Case A: 단순 기재 오류 (수치 차이가 미미하거나 오타, 완전히 클 때)
            # 10% 미만 차이거나 매물 면적이 더 클 때
            else:
                comparison['case'] = 'A'
                comparison['case_a'] = True
                comparison['rental_type'] = '통임대'
        else:
            # 면적이 거의 일치하면 통임대
            comparison['rental_type'] = '통임대'

        # 층/호수 찾기 정보 추가
        if hasattr(self, '_floor_search_info'):
            comparison['floor_search_info'] = self._floor_search_info

        return comparison

    def _get_floor_area_from_api(
            self,
            floor_result,
            floor,
            area_result,
            ho=None,
            unit_result=None):
        """건축물대장 API에서 해당 층의 전용면적 직접 조회 (호수 포함, 전유부 우선)"""
        registry_area = None
        search_floor = floor if floor else 1

        # 층/호수 찾기 실패 시 도움말용 정보 수집
        available_floors = set()  # 사용 가능한 층 목록
        available_hos_by_floor = {}  # 층별 호수 목록
        same_ho_other_floors = []  # 같은 호수 번호의 다른 층

        # 1. 전유부 조회 결과에서 호수별 면적 찾기 (최우선)
        if ho and unit_result and unit_result.get(
                'success') and unit_result.get('data'):
            # 디버깅: 전유부 데이터 확인
            debug_unit_info = []
            debug_unit_info.append(f"=== 전유부 조회 디버깅 (호수: {ho}) ===")
            debug_unit_info.append(f"전유부 데이터 개수: {len(unit_result['data'])}")

            # 호수 정규화 (입력된 호수에서 "호" 제거)
            ho_normalized = str(ho).replace('호', '').strip()

            for idx, unit_info in enumerate(unit_result['data']):
                debug_unit_info.append(f"\n[전유부 항목 {idx + 1}]")
                debug_unit_info.append(f"모든 필드: {list(unit_info.keys())}")

                # 호수 필드 찾기 (여러 가능한 필드명 시도)
                ho_fields = [
                    'ho',
                    'hoNo',
                    'hoNm',
                    'hoNoNm',
                    '호수',
                    '호',
                    'unitNo',
                    'unit',
                    'dongNo',
                    'dongNm',
                    'hoStr',
                    'hoStrNm']
                unit_ho = None
                matched_ho_field = None

                for ho_field in ho_fields:
                    ho_value = unit_info.get(ho_field, '')
                    if ho_value:
                        ho_value_str = str(ho_value).strip()
                        debug_unit_info.append(
                            f"  {ho_field}: '{ho_value_str}'")

                        # 호수 매칭 (다양한 형식 지원)
                        ho_value_normalized = ho_value_str.replace(
                            '호', '').strip()

                        # 정확히 일치하거나, 정규화된 값이 일치하거나, 시작 부분이 일치하는지 확인
                        if (ho == ho_value_str or
                            ho_normalized == ho_value_normalized or
                            ho_value_normalized.startswith(ho_normalized) or
                                ho_normalized.startswith(ho_value_normalized)):
                            unit_ho = ho_value_str
                            matched_ho_field = ho_field
                            debug_unit_info.append(
                                f"  ✓ 호수 매칭 성공! (필드: {ho_field}, 값: {ho_value_str})")
                            break

                # 호수가 매칭되면 해당 호수의 면적 사용
                if unit_ho:
                    debug_unit_info.append(f"  매칭된 호수: {unit_ho}")

                    # 전용면적 필드 찾기 (더 많은 필드명 시도)
                    exclusive_area_fields = [
                        'exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                        'exclTotArea', 'exclTotArea1', 'exclTotArea2',
                        '전용면적', '전용면적1', '전용면적2',
                        'area', 'area1', 'area2', 'totArea', 'totArea1',
                        'exclAreaNm', 'exclTotAreaNm', 'areaNm'
                    ]

                    for field in exclusive_area_fields:
                        exclusive_area = unit_info.get(field, '')
                        if exclusive_area:
                            debug_unit_info.append(
                                f"  {field}: {exclusive_area}")
                            try:
                                area_val = float(str(exclusive_area).strip())
                                if area_val > 0:
                                    registry_area = area_val
                                    debug_unit_info.append(
                                        f"  ✓ 면적 찾음! {field} = {area_val}㎡")
                                    break
                            except BaseException:
                                pass

                    # 면적 필드를 찾지 못한 경우, 모든 필드에서 면적 관련 값 검색
                    if not registry_area:
                        debug_unit_info.append("  면적 필드를 찾지 못함. 모든 필드 검색 중...")
                        for key, value in unit_info.items():
                            if value and str(value).strip():
                                key_lower = key.lower()
                                value_str = str(value).strip()
                                # 면적 관련 키워드가 포함된 필드 확인
                                if ('면적' in key or 'area' in key_lower) and (
                                        '전용' in key or 'excl' in key_lower):
                                    try:
                                        area_val = float(value_str)
                                        if area_val > 0:
                                            registry_area = area_val
                                            debug_unit_info.append(
                                                f"  ✓ 면적 찾음! {key} = {area_val}㎡")
                                            break
                                    except BaseException:
                                        pass

                    if registry_area:
                        break

            # 디버깅 정보 저장
            try:
                with open('unit_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_unit_info))
                    if registry_area:
                        f.write(f"\n\n최종 선택된 면적: {registry_area}㎡")
                    else:
                        f.write(f"\n\n면적을 찾지 못했습니다.")
            except BaseException:
                pass

        # 2. 전유공용면적 조회 결과에서 해당 층의 전용면적 찾기 (호수 우선)
        if not registry_area and area_result and area_result.get(
                'success') and area_result.get('data'):
            for area_info in area_result['data']:
                # 사용 가능한 층/호수 정보 수집 (전유만)
                floor_num_data = area_info.get(
                    'flrNoNm', '') or area_info.get(
                    'flrNo', '')
                ho_data = area_info.get('hoNm', '')
                pubuse_cd = area_info.get('exposPubuseGbCd', '')
                etc_purps_data = area_info.get('etcPurps', '')
                main_purps_data = area_info.get('mainPurpsCdNm', '')

                # 계단실 제외 (데이터 수집 단계에서도 제외)
                # '계단실'만 정확히 체크
                is_staircase_data = False
                etc_purps_data_str = str(
                    etc_purps_data).strip() if etc_purps_data else ''
                main_purps_data_str = str(
                    main_purps_data).strip() if main_purps_data else ''

                if '계단실' in etc_purps_data_str or '계단실' in main_purps_data_str:
                    is_staircase_data = True
                elif etc_purps_data_str == '계단' or main_purps_data_str == '계단':
                    is_staircase_data = True

                if is_staircase_data:
                    continue

                # 전유 데이터만 수집
                if str(pubuse_cd) == '1':
                    if floor_num_data:
                        floor_str = str(floor_num_data).strip()
                        available_floors.add(floor_str)

                        if ho_data:
                            ho_str = str(ho_data).strip()
                            if floor_str not in available_hos_by_floor:
                                available_hos_by_floor[floor_str] = []
                            available_hos_by_floor[floor_str].append(ho_str)

                            # 같은 호수 번호의 다른 층 찾기
                            if ho:
                                ho_normalized = str(
                                    ho).replace('호', '').strip()
                                ho_data_normalized = ho_str.replace(
                                    '호', '').strip()
                                if ho_normalized == ho_data_normalized and floor_str != str(
                                        search_floor):
                                    same_ho_other_floors.append(
                                        f"{floor_str} {ho_str}")

                # 층 매칭을 위한 변수 (위에서 이미 가져왔으므로 재사용)
                floor_num_str = str(floor_num_data).strip()
                search_floor_str = str(search_floor)

                # 정확한 층 매칭 (부분 매칭 방지)
                is_match = False

                # 지하층 처리 (search_floor가 음수인 경우)
                if search_floor < 0:
                    basement_floor_num = abs(search_floor)
                    # "지하1층", "지하1", "지1층", "지1", "B1", "B1F", "b1", "지하1F" 등과 매칭
                    if (floor_num_str == f"지하{basement_floor_num}층" or
                        floor_num_str == f"지하{basement_floor_num}" or
                        floor_num_str == f"지{basement_floor_num}층" or
                        floor_num_str == f"지{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}f" or
                        floor_num_str == f"지하{basement_floor_num}F" or
                        floor_num_str == f"-{basement_floor_num}" or
                        floor_num_str == f"-{basement_floor_num}층" or
                            floor_num_str == f"-{basement_floor_num}F"):
                        is_match = True
                # 지상층 처리
                elif floor_num_str == search_floor_str:
                    is_match = True
                elif floor_num_str == f"{search_floor_str}층":
                    is_match = True
                elif floor_num_str == f"{search_floor_str}F":
                    is_match = True
                elif floor_num_str.startswith(f"{search_floor_str}층"):
                    if len(floor_num_str) == len(f"{search_floor_str}층") or (len(floor_num_str) > len(
                            f"{search_floor_str}층") and not floor_num_str[len(f"{search_floor_str}층") - 1].isdigit()):
                        is_match = True
                elif search_floor == 1:
                    if ('1층' in floor_num_str and '11층' not in floor_num_str and '21층' not in floor_num_str) or floor_num_str == '1' or floor_num_str.startswith('1층'):
                        is_match = True

                if is_match:
                    # 디버그: 매칭된 층의 모든 데이터 출력
                    area_val_debug = area_info.get('area', '')
                    print(f"\n🔍 [_get_floor_area_from_api] 층 매칭됨! 상세 정보:")
                    print(f"   - 층: {floor_num_str}")
                    print(f"   - 호수: {area_info.get('hoNm', '없음')}")
                    print(f"   - 면적: {area_val_debug}")
                    print(
                        f"   - mainPurpsCdNm: '{area_info.get('mainPurpsCdNm', '')}'")
                    print(f"   - etcPurps: '{area_info.get('etcPurps', '')}'")
                    print(
                        f"   - exposPubuseGbCdNm: '{area_info.get('exposPubuseGbCdNm', '')}'")
                    print(
                        f"   - exposPubuseGbCd: '{area_info.get('exposPubuseGbCd', '')}'")

                    # 전유/공용 구분 확인 (전유만 선택!) - 호수 매칭 전에 먼저 확인
                    pubuse_gbn = (area_info.get('exposPubuseGbCdNm', '') or
                                  area_info.get('pubuseGbCdNm', '') or
                                  area_info.get('pubuseGbn', '') or
                                  area_info.get('pubuseGbCd', ''))
                    is_exclusive = False
                    if pubuse_gbn:
                        pubuse_gbn_str = str(pubuse_gbn).strip()
                        if '전유' in pubuse_gbn_str or 'exclusive' in pubuse_gbn_str.lower():
                            is_exclusive = True
                    else:
                        # 필드가 없으면 exposPubuseGbCd 값으로 확인 (1=전유, 2=공용)
                        expos_pubuse_cd = area_info.get('exposPubuseGbCd', '')
                        if str(expos_pubuse_cd) == '1':
                            is_exclusive = True
                        elif str(expos_pubuse_cd) == '2':
                            is_exclusive = False

                    print(f"   - is_exclusive: {is_exclusive}")

                    # 공용 데이터는 건너뛰기!
                    if not is_exclusive:
                        print(f"   ⏭️ 공용 데이터 건너뛰기\n")
                        continue

                    # 계단실은 임대 대상이 아니므로 건너뛰기
                    etc_purps = area_info.get('etcPurps', '')
                    main_purps = area_info.get('mainPurpsCdNm', '')

                    # 계단실 체크: etcPurps 또는 mainPurpsCdNm에 "계단실" 또는 "계단" 포함
                    # 계단실 체크 ('계단실'만 정확히)
                    is_staircase = False
                    etc_purps_str = str(etc_purps).strip() if etc_purps else ''
                    main_purps_str = str(
                        main_purps).strip() if main_purps else ''

                    if '계단실' in etc_purps_str or '계단실' in main_purps_str:
                        is_staircase = True
                        print(f"   ⚠️ 계단실 감지!")
                    elif etc_purps_str == '계단' or main_purps_str == '계단':
                        is_staircase = True
                        print(f"   ⚠️ 계단 감지!")

                    print(f"   - is_staircase: {is_staircase}")

                    if is_staircase:
                        print(f"   ⏭️ 계단실 제외\n")
                        continue

                    print(f"   ✅ 전유 데이터 선택됨!\n")

                    # 호수가 있으면 호수 매칭 시도
                    if ho:
                        # 호수 정규화 (입력된 호수에서 "호" 제거)
                        ho_normalized = str(ho).replace('호', '').strip()

                        # 호수 필드 찾기 (여러 가능한 필드명 시도)
                        ho_fields = [
                            'ho',
                            'hoNo',
                            'hoNm',
                            'hoNoNm',
                            '호수',
                            '호',
                            'unitNo',
                            'unit']
                        area_ho = None
                        ho_found_but_not_matched = False  # 호수를 찾았지만 불일치한 경우

                        for ho_field in ho_fields:
                            ho_value = area_info.get(ho_field, '')
                            if ho_value:
                                ho_value_str = str(ho_value).strip()
                                ho_value_normalized = ho_value_str.replace(
                                    '호', '').strip()

                                # 호수 매칭 - 정규화된 값이 정확히 일치하는 경우만!
                                if ho_normalized == ho_value_normalized:
                                    area_ho = ho_value_str
                                    print(
                                        f"✅ [_get_floor_area_from_api] 호수 매칭 성공: 입력={ho}, API={ho_value_str}")
                                    break
                                else:
                                    ho_found_but_not_matched = True
                                    print(
                                        f"⏭️ [_get_floor_area_from_api] 호수 불일치: 입력={ho_normalized}, API={ho_value_normalized}")

                        # 호수를 찾았지만 불일치한 경우 → 다음 area_info 확인
                        if ho_found_but_not_matched and not area_ho:
                            print(f"   → 이 전유부분 건너뛰고 다음 항목 확인")
                            continue  # 다음 area_info로 이동

                        # 호수가 매칭되면 해당 호수의 면적 사용
                        if area_ho:
                            # 전용면적 필드 찾기 (여러 가능한 필드명 시도)
                            exclusive_area_fields = [
                                'exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                                'exclTotArea', 'exclTotArea1', 'exclTotArea2',
                                '전용면적', '전용면적1', '전용면적2',
                                'area', 'area1', 'area2'  # 단순 area 필드도 시도
                            ]
                            for field in exclusive_area_fields:
                                exclusive_area = area_info.get(field, '')
                                if exclusive_area:
                                    try:
                                        area_val = float(
                                            str(exclusive_area).strip())
                                        if area_val > 0:
                                            registry_area = area_val
                                            break
                                    except BaseException:
                                        pass
                            if registry_area:
                                break

                    # 호수 입력이 없을 때만 층 전체 면적 사용
                    if not registry_area and not ho:
                        # 전용면적 필드 찾기 (여러 가능한 필드명 시도)
                        exclusive_area_fields = [
                            'exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                            'exclTotArea', 'exclTotArea1', 'exclTotArea2',
                            '전용면적', '전용면적1', '전용면적2',
                            'area', 'area1', 'area2'  # 단순 area 필드도 시도
                        ]
                        for field in exclusive_area_fields:
                            exclusive_area = area_info.get(field, '')
                            if exclusive_area:
                                try:
                                    area_val = float(
                                        str(exclusive_area).strip())
                                    if area_val > 0:
                                        registry_area = area_val
                                        print(
                                            f"✅ [_get_floor_area_from_api] 호수 입력 없음 - 층 면적 사용: area={area_val}㎡, etcPurps={etc_purps}")
                                        break
                                except BaseException:
                                    pass
                        if registry_area:
                            break

        # 3. 층별개요에서도 시도 (정확한 층 매칭)
        if registry_area is None and floor_result and floor_result.get(
                'success') and floor_result.get('data'):
            for floor_info in floor_result['data']:
                floor_num = floor_info.get(
                    'flrNoNm', '') or floor_info.get(
                    'flrNo', '')
                floor_num_str = str(floor_num).strip()
                search_floor_str = str(search_floor)

                # 정확한 층 매칭
                is_match = False

                # 지하층 처리 (search_floor가 음수인 경우)
                if search_floor < 0:
                    basement_floor_num = abs(search_floor)
                    # "지하1층", "지하1", "지1층", "지1", "B1", "B1F", "b1", "지하1F" 등과 매칭
                    if (floor_num_str == f"지하{basement_floor_num}층" or
                        floor_num_str == f"지하{basement_floor_num}" or
                        floor_num_str == f"지{basement_floor_num}층" or
                        floor_num_str == f"지{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}" or
                        floor_num_str.lower() == f"b{basement_floor_num}f" or
                        floor_num_str == f"지하{basement_floor_num}F" or
                        floor_num_str == f"-{basement_floor_num}" or
                        floor_num_str == f"-{basement_floor_num}층" or
                            floor_num_str == f"-{basement_floor_num}F"):
                        is_match = True
                # 지상층 처리
                elif floor_num_str == search_floor_str:
                    is_match = True
                elif floor_num_str == f"{search_floor_str}층":
                    is_match = True
                elif floor_num_str == f"{search_floor_str}F":
                    is_match = True
                elif floor_num_str.startswith(f"{search_floor_str}층"):
                    if len(floor_num_str) == len(f"{search_floor_str}층") or (len(floor_num_str) > len(
                            f"{search_floor_str}층") and not floor_num_str[len(f"{search_floor_str}층") - 1].isdigit()):
                        is_match = True
                elif search_floor == 1:
                    if ('1층' in floor_num_str and '11층' not in floor_num_str and '21층' not in floor_num_str) or floor_num_str == '1' or floor_num_str.startswith('1층'):
                        is_match = True

                if is_match:
                    # 계단실 필터링 (층별개요 API)
                    etc_purps_floor = floor_info.get('etcPurps', '')
                    main_purps_floor = floor_info.get('mainPurpsCdNm', '')

                    # 디버그 로그
                    area_debug = floor_info.get('area', '')
                    print(f"\n🔍 [층별개요] 층 매칭됨! 상세 정보:")
                    print(f"   - 층: {floor_num_str}")
                    print(f"   - 면적: {area_debug}")
                    print(f"   - mainPurpsCdNm: '{main_purps_floor}'")
                    print(f"   - etcPurps: '{etc_purps_floor}'")

                    # 계단실 체크 ('계단실'만 정확히)
                    is_staircase_floor = False
                    etc_purps_floor_str = str(
                        etc_purps_floor).strip() if etc_purps_floor else ''
                    main_purps_floor_str = str(
                        main_purps_floor).strip() if main_purps_floor else ''

                    if '계단실' in etc_purps_floor_str or '계단실' in main_purps_floor_str:
                        is_staircase_floor = True
                        print(f"   ⚠️ 계단실 감지!")
                    elif etc_purps_floor_str == '계단' or main_purps_floor_str == '계단':
                        is_staircase_floor = True
                        print(f"   ⚠️ 계단 감지!")

                    print(f"   - is_staircase: {is_staircase_floor}")

                    if is_staircase_floor:
                        print(f"   ⏭️ 계단실 제외 (층별개요)\n")
                        continue

                    print(f"   ✅ 층별개요 데이터 선택됨!\n")

                    # 면적 관련 필드 찾기 (더 많은 필드명 시도)
                    for key, value in floor_info.items():
                        if value and str(value).strip():
                            key_lower = key.lower()
                            # 전용면적 관련 필드 (더 넓은 범위로 검색)
                            if ('면적' in key or 'area' in key_lower):
                                # 전용면적, 바닥면적, 연면적 등 모두 시도
                                try:
                                    area_val = float(str(value).strip())
                                    if area_val > 0:
                                        # 전용면적 우선, 없으면 바닥면적, 연면적 순서
                                        if '전용' in key or 'excl' in key_lower:
                                            registry_area = area_val
                                            break
                                        elif registry_area is None and ('바닥' in key or 'flr' in key_lower):
                                            registry_area = area_val
                                        elif registry_area is None:
                                            registry_area = area_val
                                except BaseException:
                                    pass
                    if registry_area:
                        break

        # 층/호수 찾기 실패 시 도움말 정보 저장
        self._floor_search_info = {
            'found': registry_area is not None,
            'searched_floor': search_floor,
            'searched_ho': ho,
            'available_floors': sorted(
                list(available_floors)),
            'available_hos_by_floor': {
                k: sorted(v) for k,
                v in available_hos_by_floor.items()},
            'same_ho_other_floors': same_ho_other_floors}

        return registry_area

    def _add_area_buttons(self, area_comparison, parsed):
        """면적 불일치 시 버튼 추가"""
        if not area_comparison or not area_comparison.get('mismatch'):
            return

        # 면적 비교 정보 표시
        kakao_area = area_comparison['kakao_area']
        registry_area = area_comparison['registry_area']
        kakao_pyeong = int(round(kakao_area / 3.3058, 0))
        registry_pyeong = int(round(registry_area / 3.3058, 0))

        info_text = f"\n\n[카톡면적과 대장면적이 다르네요]\n"

        # 분할임대/통임대 정보 표시 (친근한 톤)
        rental_type = area_comparison.get('rental_type', '확인필요')
        if area_comparison['case'] == 'B':  # 분할임대
            info_text += f"📐 계약 {registry_area}㎡ ({registry_pyeong}평) / 전용 {kakao_area}㎡ ({kakao_pyeong}평)\n"
            info_text += f"차이: {
                area_comparison['diff']:.2f}㎡ ({
                area_comparison['diff_percent']:.1f}%)\n\n"
            info_text += f"💡 카톡면적이 대장면적보다 많이 작네요. {rental_type}인가요?\n"
            info_text += f"   (해당 층의 일부만 임대하는 것으로 보입니다)\n\n"
            info_text += f"📌 네이버부동산 교차검증 시:\n"
            info_text += f"   계약면적 {registry_area}㎡, 전용면적 {kakao_area}㎡ 둘 다 확인하세요\n"
        elif area_comparison['case'] == 'A':  # 애매한 경우
            info_text += f"📐 계약 {registry_area}㎡ ({registry_pyeong}평) / 전용 {kakao_area}㎡ ({kakao_pyeong}평)\n"
            info_text += f"차이: {
                area_comparison['diff']:.2f}㎡ ({
                area_comparison['diff_percent']:.1f}%)\n\n"
            info_text += f"💭 면적 차이가 애매해요. 통임대인지 분할임대인지 확인이 필요합니다.\n"
            info_text += f"   (측정 오차이거나 실제 분할임대일 수 있습니다)\n\n"
            info_text += f"📌 네이버부동산 교차검증 시:\n"
            info_text += f"   계약면적과 전용면적 둘 다 정확하게 적혔는지 확인하세요\n"

        self.result_text.insert(tk.END, info_text)

        # 기존 버튼 프레임이 있으면 제거
        if hasattr(self, 'area_button_frame'):
            for widget in self.area_button_frame.winfo_children():
                widget.destroy()
        else:
            # 버튼 프레임이 없으면 생성 (이미 __init__에서 생성했지만 확인)
            pass

        # 버튼 추가
        btn1 = tk.Button(
            self.area_button_frame,
            text="[Case A] 대장 면적 적용하기",
            command=lambda: self._apply_registry_area(
                area_comparison,
                parsed,
                'A'),
            bg='#4CAF50',
            fg='white',
            font=(
                '맑은 고딕',
                10,
                'bold'),
            padx=10,
            pady=5)
        btn1.pack(side=tk.LEFT, padx=5)

        btn2 = tk.Button(
            self.area_button_frame,
            text="[Case B] 대장 면적 적용하기",
            command=lambda: self._apply_registry_area(
                area_comparison,
                parsed,
                'B'),
            bg='#2196F3',
            fg='white',
            font=(
                '맑은 고딕',
                10,
                'bold'),
            padx=10,
            pady=5)
        btn2.pack(side=tk.LEFT, padx=5)

        # 버튼 프레임 표시
        self.area_button_frame.pack(fill=tk.X, padx=10, pady=5)

    def _apply_registry_area(self, area_comparison, parsed, case):
        """대장 면적 적용"""
        if not area_comparison:
            return

        registry_area = area_comparison['registry_area']
        # 면적 적용 확인
        case_name = "Case A (단순 기재 오류)" if case == 'A' else "Case B (일부 임대)"
        confirm = messagebox.askyesno(
            "면적 적용", f"{case_name}로 판단하여\n" f"건축물대장 전용면적 {registry_area}㎡를 적용하시겠습니까?")

        if confirm:
            # 카톡 텍스트에서 면적 부분 찾아서 업데이트
            kakao_text = self.kakao_text.get(1.0, tk.END)
            lines = kakao_text.split('\n')

            # 면적이 있는 줄 찾아서 업데이트
            for i, line in enumerate(lines):
                if 'm2' in line.lower() or '㎡' in line or '평' in line:
                    # 면적 숫자 찾아서 교체
                    # 예: "전용면적 약 80m2 (약 24평)" -> "전용면적 약 {registry_area}m2 (약
                    # {pyeong}평)"
                    new_pyeong = int(round(registry_area / 3.3058, 0))
                    # 면적 숫자 교체
                    new_line = re.sub(
                        r'(\d+\.?\d*)\s*m2',
                        f'{registry_area}m2',
                        line,
                        flags=re.IGNORECASE)
                    new_line = re.sub(
                        r'(\d+\.?\d*)\s*㎡', f'{registry_area}㎡', new_line)
                    new_line = re.sub(
                        r'약\s*(\d+)\s*평', f'약 {new_pyeong}평', new_line)
                    lines[i] = new_line
                    break

            # 업데이트된 텍스트로 카톡 입력 영역 갱신
            updated_text = '\n'.join(lines)
            self.kakao_text.delete(1.0, tk.END)
            self.kakao_text.insert(1.0, updated_text)

            # 결과 재생성
            self.generate_blog_ad()

            messagebox.showinfo(
                "적용 완료", f"건축물대장 전용면적 {registry_area}㎡가 적용되었습니다.\n" f"결과가 자동으로 재생성되었습니다.")

    def _compare_unit_areas(self, kakao_area, units):
        """카톡 면적과 전유부분 면적들을 비교하여 추천"""
        if not units:
            return None

        # 전유부분이 1개면 비교 불필요
        if len(units) == 1:
            return {
                'type': 'single',
                'units': units,
                'total_area': units[0]['area'],
                'recommended': 'single'
            }

        # 전유부분이 여러 개인 경우
        total_area = sum(unit['area'] for unit in units)

        # 카톡 면적과 비교 (오차 ±5m² 허용)
        tolerance = 5.0
        match_total = False
        match_unit_idx = None

        if kakao_area:
            # 합계와 비교
            if abs(kakao_area - total_area) <= tolerance:
                match_total = True

            # 개별 호수와 비교
            for idx, unit in enumerate(units):
                if abs(kakao_area - unit['area']) <= tolerance:
                    match_unit_idx = idx
                    break

        # 추천 결정
        if match_total:
            recommended = 'total'  # 통임대 추천
        elif match_unit_idx is not None:
            recommended = f'unit_{match_unit_idx}'  # 특정 호수 추천
        else:
            recommended = 'total'  # 기본값: 통임대

        return {
            'type': 'multiple',
            'units': units,
            'total_area': total_area,
            'match_total': match_total,
            'match_unit_idx': match_unit_idx,
            'recommended': recommended
        }

    def _get_all_units_on_floor(self, area_result, floor, floor_result=None):
        """같은 층의 모든 전유부분 찾기 (통임대/분할임대 판단용)"""
        units = []

        # area_result (전유공용면적 API) 우선 사용
        use_area_result = area_result and area_result.get(
            'success') and area_result.get('data')

        if not use_area_result:
            print(f"🔍 [디버그] _get_all_units_on_floor: area_result 없음 또는 비어있음")
            # area_result가 없으면 floor_result (층별개요 API) 사용
            if floor_result and floor_result.get(
                    'success') and floor_result.get('data'):
                print(f"   → floor_result로 대체 (층별개요 API 사용)")
                return self._get_all_units_from_floor_result(
                    floor_result, floor)
            else:
                print(f"   → floor_result도 없음. 빈 리스트 반환")
                return units

        search_floor = floor if floor else 1
        print(f"🔍 [디버그] _get_all_units_on_floor 시작:")
        print(
            f"   search_floor={search_floor}, 총 데이터 개수={len(area_result.get('data', []))}")

        floor_samples = []  # 층 정보 샘플 (디버깅용)
        for idx, area_info in enumerate(area_result['data']):
            # 층 매칭 확인
            floor_num = area_info.get(
                'flrNoNm', '') or area_info.get(
                'flrNo', '')
            floor_num_str = str(floor_num).strip()

            # 처음 5개 항목의 층 정보 수집 (디버깅용)
            if idx < 5:
                floor_samples.append(floor_num_str)

            # 층 매칭 (지하층 포함)
            is_floor_match = False
            if search_floor < 0:
                # 지하층
                basement_floor_num = abs(search_floor)
                if (floor_num_str == f"지하{basement_floor_num}층" or
                    floor_num_str == f"지하{basement_floor_num}" or
                    floor_num_str == f"지{basement_floor_num}층" or
                    floor_num_str == f"지{basement_floor_num}" or
                    floor_num_str.lower() == f"b{basement_floor_num}" or
                        floor_num_str == f"-{basement_floor_num}"):
                    is_floor_match = True
                    print(
                        f"   🎯 층 매칭 성공: '{floor_num_str}' (search_floor={search_floor})")
            else:
                # 지상층
                if (floor_num_str == str(search_floor) or
                    floor_num_str == f"{search_floor}층" or
                        floor_num_str == f"지상{search_floor}층"):
                    is_floor_match = True
                    print(
                        f"   🎯 층 매칭 성공: '{floor_num_str}' (search_floor={search_floor})")

            if not is_floor_match:
                continue

            # 전유부분만 확인 (공용 제외)
            expos_pubuse = area_info.get(
                'exposPubuseGbCdNm', '') or str(
                area_info.get(
                    'exposPubuseGbCd', ''))
            is_exclusive = False
            if '전유' in str(expos_pubuse) or str(
                    area_info.get('exposPubuseGbCd', '')) == '1':
                is_exclusive = True

            if not is_exclusive:
                continue

            # 호수, 면적, 용도 추출
            ho_nm = area_info.get('hoNm', '')
            area_val = area_info.get('area', '')
            main_purps = area_info.get('mainPurpsCdNm', '')
            etc_purps = area_info.get('etcPurps', '')

            # 계단실 필터링 (임대 대상이 아니므로 제외)
            # '계단실'만 정확히 체크 (다른 용도에 '계단' 키워드가 포함될 수 있으므로)
            is_staircase = False
            etc_purps_str = str(etc_purps).strip() if etc_purps else ''
            main_purps_str = str(main_purps).strip() if main_purps else ''

            # 정확히 '계단실'이 단어로 포함되어 있는지 체크
            if '계단실' in etc_purps_str or '계단실' in main_purps_str:
                is_staircase = True
            # 또는 용도가 정확히 '계단'인 경우도 제외
            elif etc_purps_str == '계단' or main_purps_str == '계단':
                is_staircase = True

            if is_staircase:
                print(
                    f"   ⏭️  계단실 제외: 호수={ho_nm}, mainPurps={main_purps}, etcPurps={etc_purps}")
                continue

            print(
                f"   ✔️  면적 포함: 호수={ho_nm}, 면적={area_val}㎡, mainPurps={main_purps}, etcPurps={etc_purps}")

            # 면적 값 변환
            try:
                area_float = float(str(area_val).strip()) if area_val else None
            except BaseException:
                area_float = None

            if area_float and area_float > 0:
                unit_info = {
                    'ho': str(ho_nm).strip() if ho_nm else None,
                    'area': area_float,
                    'main_usage': str(main_purps).strip() if main_purps else None,
                    'etc_usage': str(etc_purps).strip() if etc_purps else None,
                    'floor': floor_num_str}
                units.append(unit_info)
                print(
                    f"   ✅ 전유부분 발견: 호수={ho_nm}, 면적={area_float}㎡, 용도={main_purps}, 기타용도={etc_purps}")

        if floor_samples:
            print(f"   📋 층 정보 샘플 (처음 5개): {floor_samples}")
        print(f"🔍 [디버그] _get_all_units_on_floor 완료: 총 {len(units)}개 전유부분 발견")
        return units

    def _get_all_units_from_floor_result(self, floor_result, floor):
        """층별개요 API에서 같은 층의 모든 면적 찾기"""
        units = []
        if not floor_result or not floor_result.get(
                'success') or not floor_result.get('data'):
            return units

        search_floor = floor if floor else 1
        print(f"🔍 [디버그] _get_all_units_from_floor_result 시작:")
        print(
            f"   search_floor={search_floor}, 총 데이터 개수={len(floor_result.get('data', []))}")

        for idx, floor_info in enumerate(floor_result['data']):
            # 층 매칭
            floor_num = floor_info.get(
                'flrNoNm', '') or floor_info.get(
                'flrNo', '')
            floor_num_str = str(floor_num).strip()

            # 층 매칭 (지하층 포함)
            is_floor_match = False
            if search_floor < 0:
                basement_floor_num = abs(search_floor)
                if (floor_num_str == f"지하{basement_floor_num}층" or
                    floor_num_str == f"지하{basement_floor_num}" or
                    floor_num_str == f"지{basement_floor_num}층" or
                    floor_num_str == f"지{basement_floor_num}" or
                    floor_num_str.lower() == f"b{basement_floor_num}" or
                        floor_num_str == f"-{basement_floor_num}"):
                    is_floor_match = True
            else:
                if (floor_num_str == str(search_floor) or
                    floor_num_str == f"{search_floor}층" or
                        floor_num_str == f"지상{search_floor}층"):
                    is_floor_match = True

            if not is_floor_match:
                continue

            print(f"   🎯 층 매칭: {floor_num_str}")

            # 면적, 용도 추출
            area_val = floor_info.get('area', '')
            main_purps = floor_info.get('mainPurpsCdNm', '')
            etc_purps = floor_info.get('etcPurps', '')

            # 계단실 제외
            is_staircase = False
            etc_purps_str = str(etc_purps).strip() if etc_purps else ''
            main_purps_str = str(main_purps).strip() if main_purps else ''

            if '계단실' in etc_purps_str or '계단실' in main_purps_str:
                is_staircase = True
            elif etc_purps_str == '계단' or main_purps_str == '계단':
                is_staircase = True

            if is_staircase:
                print(f"   ⏭️  계단실 제외: 면적={area_val}㎡, mainPurps={main_purps}")
                continue

            print(
                f"   ✔️  면적 포함: 면적={area_val}㎡, mainPurps={main_purps}, etcPurps={etc_purps}")

            # 면적 값 변환
            try:
                area_float = float(str(area_val).strip()) if area_val else None
            except BaseException:
                area_float = None

            if area_float and area_float > 0:
                unit_info = {
                    'ho': None,  # 층별개요에는 호수 정보 없음
                    'area': area_float,
                    'main_usage': str(main_purps).strip() if main_purps else None,
                    'etc_usage': str(etc_purps).strip() if etc_purps else None,
                    'floor': floor_num_str
                }
                units.append(unit_info)

        print(
            f"🔍 [디버그] _get_all_units_from_floor_result 완료: 총 {
                len(units)}개 면적 발견")
        return units

    def _get_unit_area_and_usage(
            self,
            ho,
            area_result,
            floor_result=None,
            floor=None):
        """전유공용면적 조회 결과에서 호수의 면적과 용도 가져오기"""
        if not ho:
            return None, None

        unit_area = None
        unit_usage = None
        search_floor = floor if floor else 1
        # 호수 정규화 (101호 → 101, "101" → "101")
        ho_str = str(ho).strip() if ho else ''
        ho_normalized = ho_str.replace('호', '').strip() if ho_str else None
        # 디버깅 정보 초기화
        debug_info = []
        debug_info.append(
            f"호수 매칭 시작: ho={ho}, ho_str={ho_str}, ho_normalized={ho_normalized}")

        # 디버깅: 전유공용면적 조회 결과 저장
        try:
            debug_area_info = []
            debug_area_info.append(
                f"=== 전유공용면적 조회 디버깅 (호수: {ho}, 층: {search_floor}) ===")
            if area_result and area_result.get(
                    'success') and area_result.get('data'):
                debug_area_info.append(
                    f"전유공용면적 데이터 개수: {len(area_result['data'])}")

                # 101호 데이터 찾기 (전체 데이터에서 검색)
                ho_101_items = []
                ho_101_exclusive = []  # 전유만
                all_ho_numbers = set()  # 모든 호수 목록

                for idx, area_info in enumerate(area_result['data']):
                    ho_nm = area_info.get('hoNm', '')
                    if ho_nm:
                        ho_num = str(ho_nm).strip()
                        all_ho_numbers.add(ho_num)

                        # 101호 관련 항목 찾기
                        if '101' in ho_num or ho_num == '101':
                            ho_101_items.append((idx + 1, area_info))
                            # 전유 항목만 별도 저장
                            expos = area_info.get(
                                'exposPubuseGbCdNm', '') or str(
                                area_info.get(
                                    'exposPubuseGbCd', ''))
                            if '전유' in str(expos) or str(
                                    area_info.get('exposPubuseGbCd', '')) == '1':
                                ho_101_exclusive.append((idx + 1, area_info))

                debug_area_info.append(f"\n[101호 관련 항목 찾기]")
                debug_area_info.append(f"전체 호수 목록: {sorted(all_ho_numbers)}")

                if ho_101_items:
                    debug_area_info.append(
                        f"\n101호 관련 항목 {
                            len(ho_101_items)}개 발견:")
                    for item_idx, area_info in ho_101_items:
                        debug_area_info.append(f"\n[항목 {item_idx} - 101호]")
                        debug_area_info.append(
                            f"  hoNm: {area_info.get('hoNm', '')}")
                        debug_area_info.append(
                            f"  flrNoNm: {
                                area_info.get(
                                    'flrNoNm', '')}")
                        debug_area_info.append(
                            f"  flrNo: {area_info.get('flrNo', '')}")
                        debug_area_info.append(
                            f"  exposPubuseGbCdNm: {
                                area_info.get(
                                    'exposPubuseGbCdNm', '')}")
                        debug_area_info.append(
                            f"  exposPubuseGbCd: {
                                area_info.get(
                                    'exposPubuseGbCd', '')}")
                        debug_area_info.append(
                            f"  area: {area_info.get('area', '')}")
                        debug_area_info.append(
                            f"  mainPurpsCdNm: {
                                area_info.get(
                                    'mainPurpsCdNm', '')}")
                        debug_area_info.append(
                            f"  etcPurps: {
                                area_info.get(
                                    'etcPurps', '')}")

                    if ho_101_exclusive:
                        debug_area_info.append(
                            f"\n[101호 전유 항목 {len(ho_101_exclusive)}개]")
                        for item_idx, area_info in ho_101_exclusive:
                            debug_area_info.append(f"\n항목 {item_idx} (전유):")
                            debug_area_info.append(
                                f"  hoNm: {area_info.get('hoNm', '')}")
                            debug_area_info.append(
                                f"  flrNoNm: {area_info.get('flrNoNm', '')}")
                            debug_area_info.append(
                                f"  area: {area_info.get('area', '')}")
                    else:
                        debug_area_info.append("\n101호 전유 항목 없음!")
                else:
                    debug_area_info.append("\n101호 관련 항목 없음!")
                    debug_area_info.append(f"\n[전체 호수 목록 (모든 항목)]")
                    for idx, area_info in enumerate(
                            area_result['data'][:30]):  # 처음 30개
                        ho_nm = area_info.get('hoNm', '')
                        flr_no_nm = area_info.get('flrNoNm', '')
                        expos = area_info.get(
                            'exposPubuseGbCdNm', '') or str(
                            area_info.get(
                                'exposPubuseGbCd', ''))
                        area_val = area_info.get('area', '')
                        if ho_nm:
                            debug_area_info.append(
                                f"  항목 {
                                    idx +
                                    1}: hoNm={ho_nm}, flrNoNm={flr_no_nm}, expos={expos}, area={area_val}")
            else:
                debug_area_info.append("전유공용면적 데이터 없음")

            with open('area_result_debug.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_area_info))
        except Exception as e:
            try:
                with open('area_result_debug.txt', 'w', encoding='utf-8') as f:
                    f.write(f"디버깅 오류: {str(e)}\n")
                    import traceback
                    f.write(traceback.format_exc())
            except BaseException:
                pass

        # 전유공용면적 조회 결과에서 호수별 정보 찾기
        if area_result and area_result.get(
                'success') and area_result.get('data'):
            for area_info in area_result['data']:
                # 층 매칭 확인
                floor_num = area_info.get(
                    'flrNoNm',
                    '') or area_info.get(
                    'flrNo',
                    '') or area_info.get(
                    'flrNo1',
                    '')
                floor_num_str = str(floor_num).strip()
                search_floor_str = str(search_floor)

                # 정확한 층 매칭 (지상1, 지하1, 1층 등 형식도 처리)
                is_floor_match = False
                # flrGbCdNm 확인 (지상, 지하, 각층 등)
                flr_gb_cd_nm = area_info.get('flrGbCdNm', '').strip()

                # 숫자만 추출 (예: "지상1" → "1", "1층" → "1")
                floor_num_only = re.sub(r'[^0-9]', '', floor_num_str)
                search_floor_only = str(search_floor)

                # 우선순위 1: 정확히 일치하는 경우
                if floor_num_str == search_floor_str:
                    is_floor_match = True
                # 우선순위 2: "1층" 형식 매칭 (가장 일반적)
                elif floor_num_str == f"{search_floor_str}층":
                    is_floor_match = True
                # 우선순위 3: "지상1층", "지상1" 형식
                elif floor_num_str == f"지상{search_floor_str}층" or floor_num_str == f"지상{search_floor_str}":
                    if '지하' not in floor_num_str:
                        is_floor_match = True
                # 우선순위 4: 숫자만 추출하여 비교
                elif floor_num_only == search_floor_only:
                    # 숫자가 같으면 매칭 (지상1 → 1, 지하1 → 1 구분 필요)
                    if search_floor == 1:
                        # 1층인 경우: "지상1", "1층", "1" 모두 매칭, "지하1"은 제외
                        if '지하' not in floor_num_str:
                            # "1층", "지상1", "1" 등 모두 매칭
                            if '1층' in floor_num_str or floor_num_str == '1' or '지상1' in floor_num_str:
                                is_floor_match = True
                    else:
                        # 1층이 아닌 경우: "지상"이 포함되어 있으면 매칭
                        if '지상' in floor_num_str and '지하' not in floor_num_str:
                            is_floor_match = True
                # 우선순위 5: "1F" 형식
                elif floor_num_str == f"{search_floor_str}F":
                    is_floor_match = True
                # 우선순위 6: "1층"으로 시작하는 경우
                elif floor_num_str.startswith(f"{search_floor_str}층"):
                    is_floor_match = True
                # 우선순위 7: 1층 특별 처리 (다양한 형식)
                elif search_floor == 1:
                    if '지하' not in floor_num_str:
                        # "1층", "지상1", "1" 등 모두 매칭
                        if '1층' in floor_num_str or floor_num_str == '1' or '지상1' in floor_num_str:
                            # "11층", "21층" 등은 제외
                            if '11층' not in floor_num_str and '21층' not in floor_num_str:
                                is_floor_match = True

                if is_floor_match:
                    # 전유공용구분 필드 확인 (전유만 필터링) - 먼저 확인하여 공용 데이터는 제외
                    # API 응답에서는 'exposPubuseGbCdNm' 필드 사용 (예: "전유", "공용")
                    pubuse_gbn = (area_info.get('exposPubuseGbCdNm', '') or
                                  area_info.get('pubuseGbCdNm', '') or
                                  area_info.get('pubuseGbn', '') or
                                  area_info.get('pubuseGbCd', ''))
                    is_exclusive = False
                    if pubuse_gbn:
                        pubuse_gbn_str = str(pubuse_gbn).strip()
                        # 전유 관련 키워드 확인
                        if '전유' in pubuse_gbn_str or 'exclusive' in pubuse_gbn_str.lower():
                            is_exclusive = True
                    else:
                        # 필드가 없으면 exposPubuseGbCd 값으로 확인 (1=전유, 2=공용)
                        expos_pubuse_cd = area_info.get('exposPubuseGbCd', '')
                        if str(expos_pubuse_cd) == '1':
                            is_exclusive = True
                        elif str(expos_pubuse_cd) == '2':
                            is_exclusive = False
                        else:
                            # 코드가 없으면 전유로 간주 (하지만 실제로는 필드가 있어야 함)
                            is_exclusive = True

                    # 전유만 처리 (공용은 제외)
                    if not is_exclusive:
                        continue  # 공용 데이터는 건너뛰기

                    # 계단실 제외 (임대 대상이 아니므로 제외) - '계단실'만 정확히 체크
                    etc_purps = area_info.get('etcPurps', '')
                    main_purps_check = area_info.get('mainPurpsCdNm', '')
                    is_staircase_check = False

                    etc_purps_str = str(etc_purps).strip() if etc_purps else ''
                    main_purps_check_str = str(
                        main_purps_check).strip() if main_purps_check else ''

                    if '계단실' in etc_purps_str or '계단실' in main_purps_check_str:
                        is_staircase_check = True
                    elif etc_purps_str == '계단' or main_purps_check_str == '계단':
                        is_staircase_check = True

                    if is_staircase_check:
                        print(
                            f"⏭️ [_get_unit_area_and_usage] 계단실 제외: ho={
                                area_info.get('hoNm')}, area={
                                area_info.get('area')}, mainPurps={main_purps_check}, etcPurps={etc_purps}")
                        continue

                    # 호수 매칭 (hoNm 필드 직접 확인 - 가장 확실한 방법)
                    should_extract_area = False
                    unit_ho = None

                    if ho_normalized:
                        # hoNm 필드를 직접 확인 (전유공용면적 조회 API의 기본 호수 필드)
                        ho_nm = area_info.get('hoNm', '')
                        if ho_nm:
                            ho_nm_str = str(ho_nm).strip().replace(
                                '호', '').strip()
                            # 정확히 일치하는지 확인
                            if ho_nm_str == ho_normalized or str(
                                    ho_nm).strip() == str(ho).strip():
                                # 호수 매칭 성공!
                                should_extract_area = True
                                unit_ho = str(ho_nm).strip()
                            else:
                                # 호수 불일치 - 다음 항목 확인 (continue)
                                continue
                        else:
                            # hoNm이 없으면 다른 필드도 시도 (하지만 hoNm이 일반적)
                            ho_fields = ['ho', 'hoNo', 'hoNoNm', '호수', '호']
                            ho_matched = False
                            for ho_field in ho_fields:
                                ho_value = area_info.get(ho_field, '')
                                if ho_value:
                                    ho_value_str = str(ho_value).strip()
                                    ho_value_normalized = ho_value_str.replace(
                                        '호', '').strip()
                                    if ho_value_normalized == ho_normalized or str(
                                            ho_value).strip() == str(ho).strip():
                                        should_extract_area = True
                                        unit_ho = ho_value_str
                                        ho_matched = True
                                        break
                            if not ho_matched:
                                # 호수 매칭 실패 - 다음 항목 확인 (continue)
                                continue
                    else:
                        # 호수가 없으면 전유 데이터면 무조건 추출 (해당 층의 전유 데이터 사용)
                        should_extract_area = True
                        unit_ho = "전유"

                    if should_extract_area:
                        # 전용면적 추출 (API 응답에서는 'area' 필드 사용)
                        exclusive_area_fields = [
                            'area',  # 전유공용면적 조회 API의 기본 면적 필드 (우선순위 1)
                            'exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                            'exclTotArea', 'exclTotArea1', 'exclTotArea2',
                            '전용면적', '전용면적1', '전용면적2',
                        ]

                        for field in exclusive_area_fields:
                            area_val = area_info.get(field, '')
                            if area_val:
                                try:
                                    area_float = float(str(area_val).strip())
                                    if area_float > 0:
                                        unit_area = area_float
                                        break
                                except (ValueError, TypeError):
                                    pass

                        # 용도 추출 (전유공용면적 조회 결과에서 직접 추출)
                        if not unit_usage:
                            usage_fields = [
                                'mainPurpsCdNm', 'etcPurps', 'mainPurps']
                            for field in usage_fields:
                                usage_val = area_info.get(field, '')
                                if usage_val:
                                    unit_usage = str(usage_val).strip()
                                    break

                        # 면적이나 용도가 찾아지면 종료 (면적이 찾아지면 무조건 종료)
                        if unit_area:
                            # 디버깅: 성공한 경우
                            try:
                                debug_info.append(
                                    f"면적 추출 성공: unit_area={unit_area}, unit_ho={unit_ho}")
                                with open('unit_area_debug.txt', 'a', encoding='utf-8') as f:
                                    f.write('\n' + '\n'.join(debug_info))
                            except BaseException:
                                pass
                            break
                        # 용도만 찾아졌지만 호수가 매칭된 경우 종료
                        if unit_usage and unit_ho:
                            break

        # 디버깅: 최종 결과
        try:
            debug_info.append(
                f"최종 결과: unit_area={unit_area}, unit_usage={unit_usage}")
            with open('unit_area_debug.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_info))
        except BaseException:
            pass

        return unit_area, unit_usage

    def _generate_blog_text(
            self,
            parsed,
            building,
            floor_result,
            floor,
            usage_judgment,
            area_comparison=None,
            area_result=None,
            unit_result=None):
        """블로그 필수표시사항 텍스트 생성 (호수 유무에 따라 데이터 선택)"""
        lines = []

        # 소재지 분석: 호수 유무 확인
        ho = parsed.get('ho')
        is_collective_building = False  # 집합건물 여부 (호수가 있고 전유부에서 매칭됨)
        unit_area = None
        unit_usage = None

        # Case A: 호수가 있고 전유공용면적 조회에서 매칭되는 경우 (집합건물/구분상가)
        if ho and area_result and area_result.get(
                'success') and area_result.get('data'):
            # 호수 정규화 (101호 → 101)
            ho_normalized = str(ho).replace('호', '').strip() if ho else None

            # 전유공용면적 조회 결과에서 직접 호수 매칭 시도 (더 확실한 방법)
            unit_area, unit_usage = self._get_unit_area_and_usage(
                ho, area_result, floor_result, floor)

            # 디버깅: 전유부 면적 추출 결과 확인
            try:
                debug_unit_info = []
                debug_unit_info.append(f"=== 전유부 면적 추출 디버깅 ===")
                debug_unit_info.append(f"호수: {ho}")
                debug_unit_info.append(f"호수 정규화: {ho_normalized}")
                debug_unit_info.append(f"unit_area: {unit_area}")
                debug_unit_info.append(f"unit_usage: {unit_usage}")
                debug_unit_info.append(
                    f"is_collective_building (추출 전): {is_collective_building}")

                # API 응답에서 실제 호수 목록 확인
                if area_result.get('data'):
                    all_hos = []
                    ho_101_items = []
                    for area_info in area_result['data']:
                        ho_nm = area_info.get('hoNm', '')
                        expos = area_info.get('exposPubuseGbCdNm', '')
                        area_val = area_info.get('area', '')
                        if ho_nm:
                            all_hos.append(str(ho_nm))
                            if str(ho_nm) == ho_normalized or str(
                                    ho_nm) == str(ho):
                                ho_101_items.append(
                                    f"  hoNm={ho_nm}, expos={expos}, area={area_val}")

                    debug_unit_info.append(
                        f"\nAPI 응답의 모든 호수: {
                            sorted(
                                set(all_hos))}")
                    debug_unit_info.append(f"\n매칭된 호수 항목:")
                    for item in ho_101_items:
                        debug_unit_info.append(item)
                    if not ho_101_items:
                        debug_unit_info.append("  매칭된 호수 항목 없음!")

                with open('unit_area_debug.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(debug_unit_info))
            except Exception as e:
                try:
                    with open('unit_area_debug.txt', 'w', encoding='utf-8') as f:
                        f.write(f"디버깅 오류: {str(e)}\n")
                        import traceback
                        f.write(traceback.format_exc())
                except BaseException:
                    pass

            if unit_area is not None and unit_area > 0:
                is_collective_building = True
                # 디버깅: 집합건물로 판정됨
                try:
                    with open('unit_area_debug.txt', 'a', encoding='utf-8') as f:
                        f.write(
                            f"\nis_collective_building (판정 후): {is_collective_building}\n")
                        f.write(f"사용할 전유면적: {unit_area}㎡\n")
                except BaseException:
                    pass
            elif unit_usage:
                # 면적은 없지만 용도가 있으면 집합건물로 판정
                is_collective_building = True

        # 1. 소재지: 카톡 매물정보의 주소 (대구가 없어도 "대구" 붙이기, 건물명 제거, 번지수는 표시)
        address = parsed.get('address', '')
        if address:
            import re

            # 층수 제거 (예: "1층", "4층" 등)
            address = re.sub(r'\s*\d+\s*층\s*.*$', '', address).strip()

            # 건물명 제거 (번지수 이후의 한글/영문 단어들 제거)
            # 예: "중구 삼덕동3가 137-4 전체 더포토" → "중구 삼덕동3가 137-4"
            # 번지수 패턴 찾기 (예: 137-4, 122, 122번지 등)
            bunji_patterns = [
                r'(\d+-\d+)',      # 137-4 형식
                r'(\d+번지)',      # 122번지 형식
                r'(\d+)',          # 122 형식 (마지막 숫자)
            ]

            bunji_end_pos = len(address)
            for pattern in bunji_patterns:
                matches = list(re.finditer(pattern, address))
                if matches:
                    # 마지막 번지수 패턴의 끝 위치
                    last_match = matches[-1]
                    bunji_end_pos = last_match.end()
                    break

            # 번지수 이후의 건물명 제거
            if bunji_end_pos < len(address):
                after_bunji = address[bunji_end_pos:].strip()
                # 한글/영문으로 시작하는 단어들 제거 (건물명)
                if re.match(r'^[가-힣a-zA-Z]', after_bunji):
                    address = address[:bunji_end_pos].strip()

            # 주소에 "대구"가 없으면 추가
            if '대구' not in address:
                # 시군구 정보에서 대구 확인
                daegu_gu_list = ['수성구', '중구', '동구',
                                 '서구', '남구', '북구', '달서구', '달성군']
                is_daegu = any(gu in address for gu in daegu_gu_list)
                if is_daegu:
                    # 서울 중구와 구분 (서울 특별시가 없는 경우만)
                    if '서울' not in address and '특별시' not in address:
                        # "대구"만 붙이기 (예: "수성구 범어동" → "대구 수성구 범어동")
                        address = f"대구 {address}"
            lines.append(f"• 소재지: {address}")
        else:
            lines.append("• 소재지: 확인요망")

        # 2. 전용면적: Case A (집합건물)면 전유부 면적 우선, Case B (일반건물)면 기존 로직
        kakao_area = parsed.get('area_m2')  # 전용면적
        actual_area = parsed.get('actual_area_m2')  # 실면적(계약면적)

        # 전용면적이 없으면 실면적을 카톡면적으로 사용 (키워드 없이 면적만 입력된 경우)
        if not kakao_area and actual_area:
            kakao_area = actual_area

        registry_area = None

        # 디버깅: 전용면적 결정 로직
        debug_area_decision = []
        debug_area_decision.append(f"=== 전용면적 결정 로직 디버깅 ===")
        debug_area_decision.append(f"호수: {ho}")
        debug_area_decision.append(
            f"is_collective_building: {is_collective_building}")
        debug_area_decision.append(f"unit_area: {unit_area}")
        debug_area_decision.append(
            f"area_comparison.registry_area: {
                area_comparison.get('registry_area') if area_comparison else None}")

        # Case A 우선: 집합건물이고 전유부에서 호수별 면적을 찾았으면 무조건 사용
        if is_collective_building and unit_area is not None and unit_area > 0:
            # Case A: 전유부에서 호수별 면적 사용 (최우선)
            registry_area = unit_area
            debug_area_decision.append(
                f"[Case A] 전유부 면적 사용: {registry_area}㎡ (unit_area 우선)")
        else:
            # Case B: 일반건물 또는 전유부에서 면적을 찾지 못한 경우
            # area_comparison의 registry_area는 _compare_areas에서 추출한 것인데,
            # 이게 호수를 매칭하지 못했을 수 있으므로, 다시 _get_unit_area_and_usage 시도
            if ho and area_result and area_result.get(
                    'success') and area_result.get('data'):
                # 호수가 있는데 unit_area가 None이면 다시 시도
                retry_unit_area, _ = self._get_unit_area_and_usage(
                    ho, area_result, floor_result, floor)
                if retry_unit_area is not None and retry_unit_area > 0:
                    registry_area = retry_unit_area
                    is_collective_building = True  # 재시도 성공 시 집합건물로 판정
                    debug_area_decision.append(
                        f"[Case B-재시도] 전유부 면적 재추출 성공: {registry_area}㎡")
                elif area_comparison and area_comparison.get('registry_area'):
                    registry_area = area_comparison['registry_area']
                    debug_area_decision.append(
                        f"[Case B-1] area_comparison 사용: {registry_area}㎡ (재시도 실패)")
                else:
                    registry_area = self._get_floor_area_from_api(
                        floor_result, floor, area_result, ho, unit_result)
                    debug_area_decision.append(
                        f"[Case B-2] _get_floor_area_from_api 사용: {registry_area}㎡")
            else:
                # 호수가 없으면 기존 로직 사용
                if area_comparison and area_comparison.get('registry_area'):
                    registry_area = area_comparison['registry_area']
                    debug_area_decision.append(
                        f"[Case B-1] area_comparison 사용: {registry_area}㎡ (호수 없음)")
                else:
                    registry_area = self._get_floor_area_from_api(
                        floor_result, floor, area_result, ho, unit_result)
                    debug_area_decision.append(
                        f"[Case B-2] _get_floor_area_from_api 사용: {registry_area}㎡")

        debug_area_decision.append(f"최종 registry_area: {registry_area}㎡")
        try:
            with open('area_decision_debug.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_area_decision))
        except BaseException:
            pass

        # 사용자가 선택한 면적이 있으면 해당 면적만 표시 (실면적/건축물대장 면적 텍스트 제거)
        if hasattr(self, 'selected_area') and self.selected_area:
            selected_area_value = self.selected_area.get('area')
            selected_source = self.selected_area.get('source')
            if selected_area_value:
                pyeong = int(round(selected_area_value / 3.3058, 0))
                lines.append(f"• 전용면적: {selected_area_value}㎡ ({pyeong}평)")
            else:
                lines.append("• 전용면적: 확인요망")
        # 선택된 면적이 없으면 실면적, 전용면적, 건축물대장 면적 모두 표시
        elif (actual_area is not None and actual_area > 0) or (kakao_area is not None and kakao_area > 0) or (registry_area is not None and registry_area > 0):
            # 클릭 가능한 면적 표시를 위한 특수 마커 추가
            lines.append("• 전용면적: ")  # 접두사만 먼저 추가
            lines.append("__AREA_SELECTION__")  # 면적 선택 기능 활성화 마커
            # 면적 값이 None이거나 0 이하면 빈 문자열로 전달
            actual_area_str = str(actual_area) if (
                actual_area is not None and actual_area > 0) else ''
            kakao_area_str = str(kakao_area) if (
                kakao_area is not None and kakao_area > 0) else ''
            registry_area_str = str(registry_area) if (
                registry_area is not None and registry_area > 0) else ''
            lines.append(f"__ACTUAL_AREA__{actual_area_str}__")  # 실면적(계약면적)
            lines.append(f"__KAKAO_AREA__{kakao_area_str}__")  # 전용면적
            lines.append(f"__REGISTRY_AREA__{registry_area_str}__")  # 건축물대장 면적
        else:
            lines.append("• 전용면적: 확인요망")

        # 3. 보증금/월세: 2000만 원/90만 원 형식
        if parsed.get('deposit') and parsed.get('monthly_rent'):
            deposit = parsed['deposit']
            rent = parsed['monthly_rent']
            lines.append(f"• 보증금/월세: {deposit}만 원/{rent}만 원")
        else:
            lines.append("• 보증금/월세: 확인요망")

        # 4. 중개대상물 종류: Case A (집합건물)면 전유부 용도, Case B면 표제부/층별개요 기준
        final_usage = None

        # 디버깅: 중개대상물 종류 결정 로직 추적
        debug_usage_decision = []
        debug_usage_decision.append(f"=== 중개대상물 종류 결정 로직 디버깅 ===")
        debug_usage_decision.append(f"호수: {ho}")
        debug_usage_decision.append(
            f"is_collective_building: {is_collective_building}")
        debug_usage_decision.append(f"unit_usage (전유부에서 추출): {unit_usage}")
        debug_usage_decision.append(f"floor (검색할 층): {floor}")

        # Case A: 집합건물 (호수가 있고 전유부에서 매칭됨) - 전유부 용도 사용
        # 단, 상세 용도(예: "휴게음식점")는 법정 분류(예: "제2종 근린생활시설")로 변환
        # 전유공용면적 조회 API의 용도가 부정확할 수 있으므로, 해당 층의 층별개요 정보를 우선 확인
        show_usage_warning = False  # 주택 관련 용도 경고 메시지 표시 여부 (Case A, Case B 공통)
        show_usage_mismatch_warning = False  # 입력값과 결과값 용도 불일치 경고 메시지 표시 여부
        if is_collective_building:
            debug_usage_decision.append(f"\n[Case A] 집합건물 로직 실행")
            # 먼저 해당 층의 층별개요에서 용도 확인 (전유공용면적 조회보다 정확할 수 있음)
            search_floor = floor if floor else 1
            floor_usage_str = None
            floor_etc_usage_str = None

            if floor_result and floor_result.get(
                    'success') and floor_result.get('data'):
                for floor_info in floor_result['data']:
                    floor_num = (floor_info.get('flrNoNm', '') or
                                 floor_info.get('flrNo', '') or
                                 floor_info.get('flrNoNm1', '') or
                                 floor_info.get('flrNo1', ''))
                    floor_num_str = str(floor_num).strip()
                    search_floor_str = str(search_floor)

                    # 정확한 층 매칭
                    is_match = False
                    if floor_num_str == search_floor_str or floor_num_str == f"{search_floor_str}층":
                        is_match = True
                    elif floor_num_str == f"{search_floor_str}F":
                        is_match = True
                    elif floor_num_str.startswith(f"{search_floor_str}층"):
                        if len(floor_num_str) == len(f"{search_floor_str}층") or (len(floor_num_str) > len(
                                f"{search_floor_str}층") and not floor_num_str[len(f"{search_floor_str}층") - 1].isdigit()):
                            is_match = True
                    elif search_floor == 1:
                        if ('1층' in floor_num_str and '11층' not in floor_num_str and '21층' not in floor_num_str) or floor_num_str == '1' or floor_num_str.startswith(
                                '1층'):
                            is_match = True
                    elif floor_num_str == f"지상{search_floor_str}층" or floor_num_str == f"지상{search_floor_str}":
                        if '지하' not in floor_num_str:
                            is_match = True

                    if is_match:
                        # 해당 층의 용도 정보 추출
                        main_usage = (floor_info.get('mainPurpsCdNm', '') or
                                      floor_info.get('mainPurps', ''))
                        other_usage = floor_info.get('etcPurps', '')

                        # 건물 전체 용도 필터링 (다가구주택, 다중주택, 단독주택 등은 제외)
                        building_wide_usages = [
                            '다가구주택', '다중주택', '단독주택', '공동주택', '아파트', '연립', '다세대']
                        excluded_keywords = ['계단실', '공유부분', '공유 부분']

                        if main_usage and not any(
                                bwu in str(main_usage) for bwu in building_wide_usages) and not any(
                                keyword in str(main_usage) for keyword in excluded_keywords):
                            floor_usage_str = str(main_usage).strip()
                        if other_usage and not any(
                                keyword in str(other_usage) for keyword in excluded_keywords):
                            # etcPurps에 "제1종근린생활시설(소매점)" 같은 정보가 있을 수 있음
                            floor_etc_usage_str = str(other_usage).strip()
                        if floor_usage_str or floor_etc_usage_str:
                            break

            # 층별개요에서 찾은 용도를 우선 사용, 없으면 전유공용면적 조회에서 추출한 용도 사용
            usage_str_for_judgment = None
            if floor_etc_usage_str:
                usage_str_for_judgment = floor_etc_usage_str
            elif floor_usage_str:
                usage_str_for_judgment = floor_usage_str
            elif unit_usage:
                usage_str_for_judgment = str(unit_usage).strip()

            debug_usage_decision.append(f"층별개요에서 찾은 용도:")
            debug_usage_decision.append(
                f"  floor_usage_str: {floor_usage_str}")
            debug_usage_decision.append(
                f"  floor_etc_usage_str: {floor_etc_usage_str}")
            debug_usage_decision.append(f"  unit_usage: {unit_usage}")
            debug_usage_decision.append(
                f"최종 usage_str_for_judgment: {usage_str_for_judgment}")
            print(f"🔍 [용도 디버그] floor_usage_str: {floor_usage_str}")
            print(f"🔍 [용도 디버그] floor_etc_usage_str: {floor_etc_usage_str}")
            print(f"🔍 [용도 디버그] unit_usage: {unit_usage}")
            print(
                f"🔍 [용도 디버그] 최종 usage_str_for_judgment: {usage_str_for_judgment}")

            if usage_str_for_judgment:
                unit_usage_str = usage_str_for_judgment
                unit_area_for_judgment = unit_area if unit_area else parsed.get(
                    'area_m2')

                # 면적 기준 판정 로직 (_judge_usage 함수의 로직 재사용)
                judged_usage = None

                # 0-1. 먼저 상업/업무 용도 키워드 확인 (주택 판정 오류 방지)
                commercial_keywords = [
                    '점포',
                    '소매점',
                    '슈퍼마켓',
                    '마트',
                    '편의점',
                    '상점',
                    '매장',
                    '사무소',
                    '사무실',
                    '휴게음식점',
                    '일반음식점',
                    '카페',
                    '커피숍',
                    '학원',
                    '교습소',
                    '노래연습장',
                    '의원',
                    '병원',
                    '미용원',
                    '이용원']
                has_commercial_keyword = any(
                    keyword in unit_usage_str for keyword in commercial_keywords)

                # 0-2. 주택 관련 용도 판정 (상업 용도가 없을 때만)
                if not has_commercial_keyword:
                    # 공동주택: 다세대, 연립, 아파트, 기숙사 (다세대주택, 공동주택 포함)
                    collective_house_keywords = [
                        '다세대', '다세대주택', '연립', '연립주택', '아파트', '기숙사', '공동주택']
                    is_collective_house = any(
                        keyword in unit_usage_str for keyword in collective_house_keywords)
                    if is_collective_house:
                        judged_usage = '공동주택'
                        show_usage_warning = True

                    # 단독주택: 단독, 다중, 다가구, 공관 (단독주택, 다가구주택, 다중주택 포함)
                    if not judged_usage:
                        single_house_keywords = [
                            '단독', '단독주택', '다중', '다중주택', '다가구', '다가구주택', '공관']
                        is_single_house = any(
                            keyword in unit_usage_str for keyword in single_house_keywords)
                        if is_single_house:
                            judged_usage = '단독주택'
                            show_usage_warning = True

                # 1. 판매시설 판정 (면적에 관계없이 무조건 "판매시설")
                # '판매시설', '기타판매시설'은 면적에 관계없이 무조건 "판매시설"로 기재
                sales_facility_keywords = ['판매시설', '기타판매시설']
                is_sales_facility = any(
                    keyword in unit_usage_str for keyword in sales_facility_keywords)
                if is_sales_facility:
                    judged_usage = '판매시설'

                # 2. 소매점 판정 (1000㎡ 기준)
                # '소매점', '슈퍼마켓', '일용품', '마트', '편의점' 등은 면적 기준으로 분류
                if not judged_usage:
                    retail_keywords = [
                        '소매점', '슈퍼마켓', '마트', '편의점', '상점', '매장', '일용품']
                    is_retail = any(
                        keyword in unit_usage_str for keyword in retail_keywords)
                    if is_retail and unit_area_for_judgment:
                        if unit_area_for_judgment < 1000:
                            judged_usage = '제1종 근린생활시설'
                        else:
                            # 1000㎡ 이상이면 "판매시설"로 기재
                            judged_usage = '판매시설'

                # 3. 휴게음식점, 커피숍, 제과점 판정
                if not judged_usage:
                    cafe_keywords = ['휴게음식점', '커피숍', '제과점', '카페', '음식점']
                    is_cafe = any(
                        keyword in unit_usage_str for keyword in cafe_keywords)
                    if is_cafe and unit_area_for_judgment:
                        if unit_area_for_judgment < 300:
                            judged_usage = '제1종 근린생활시설'
                        else:
                            judged_usage = '제2종 근린생활시설'

                # 4. 일반음식점, 안마시술소, 노래연습장 판정
                if not judged_usage:
                    general_food_keywords = ['일반음식점', '안마시술소', '노래연습장', '노래방']
                    is_general_food = any(
                        keyword in unit_usage_str for keyword in general_food_keywords)
                    if is_general_food:
                        judged_usage = '제2종 근린생활시설'

                # 5. 이용원, 미용원, 목욕장, 세탁소 판정
                if not judged_usage:
                    service_keywords = [
                        '이용원', '미용원', '목욕장', '세탁소', '미용실', '이발소']
                    is_service = any(
                        keyword in unit_usage_str for keyword in service_keywords)
                    if is_service:
                        judged_usage = '제1종 근린생활시설'

                # 6. 의원, 치과의원, 한의원, 안마원, 산후조리원 판정
                if not judged_usage:
                    medical_keywords = [
                        '의원', '치과의원', '한의원', '안마원', '산후조리원', '병원', '의료원']
                    is_medical = any(
                        keyword in unit_usage_str for keyword in medical_keywords)
                    if is_medical:
                        judged_usage = '제1종 근린생활시설'

                # 7. 사무소, 사무실, 부동산중개소, 금융업소 판정
                if not judged_usage:
                    office_keywords = [
                        '사무소', '사무실', '부동산중개소', '금융업소', '중개소', '은행', '금융']
                    is_office = any(
                        keyword in unit_usage_str for keyword in office_keywords)
                    if is_office and unit_area_for_judgment:
                        if unit_area_for_judgment < 30:
                            judged_usage = '제1종 근린생활시설'
                        elif unit_area_for_judgment < 500:
                            judged_usage = '제2종 근린생활시설'
                        else:
                            judged_usage = '업무시설'

                # 8. 학원, 교습소, 직업훈련소 판정
                if not judged_usage:
                    academy_keywords = ['학원', '교습소', '직업훈련소', '학원시설']
                    is_academy = any(
                        keyword in unit_usage_str for keyword in academy_keywords)
                    if is_academy and unit_area_for_judgment:
                        if unit_area_for_judgment < 500:
                            judged_usage = '제2종 근린생활시설'
                        else:
                            judged_usage = '업무시설'

                # 9. 제1종/제2종 근린생활시설이 명시된 경우 그대로 사용 (기존 로직 유지)
                if not judged_usage:
                    if '제1종 근린생활시설' in unit_usage_str or '제1종근린생활시설' in unit_usage_str:
                        judged_usage = '제1종 근린생활시설'
                    elif '제2종 근린생활시설' in unit_usage_str or '제2종근린생활시설' in unit_usage_str:
                        judged_usage = '제2종 근린생활시설'

                debug_usage_decision.append(
                    f"판정된 judged_usage: {judged_usage}")

                # 판정된 용도가 있으면 사용, 없으면 원본 사용 (하지만 상세 용도는 피해야 함)
                if judged_usage:
                    final_usage = judged_usage
                    debug_usage_decision.append(
                        f"→ final_usage = judged_usage: {final_usage}")
                else:
                    # 판정 실패 시 원본 사용 (하지만 "휴게음식점" 같은 상세 용도는 피해야 함)
                    # "제2종 근린생활시설" 같은 법정 분류가 포함되어 있으면 그대로 사용
                    if '제1종' in unit_usage_str or '제2종' in unit_usage_str or '근린생활시설' in unit_usage_str:
                        final_usage = unit_usage_str
                        debug_usage_decision.append(
                            f"→ final_usage = unit_usage_str (제1종/제2종 포함): {final_usage}")
                    else:
                        # 상세 용도인 경우 실제 용도 + (확인요망)으로 표시
                        final_usage = f"{unit_usage_str}(확인요망)"
                        debug_usage_decision.append(
                            f"→ final_usage = {unit_usage_str}(확인요망) (상세 용도로 판정 실패)")
            else:
                # usage_str_for_judgment가 없으면 확인요망
                final_usage = "확인요망"
                debug_usage_decision.append(
                    f"→ final_usage = 확인요망 (usage_str_for_judgment 없음)")
        else:
            # Case B: 일반건물 - 기존 로직 (표제부/층별개요 기준)
            debug_usage_decision.append(f"\n[Case B] 일반건물 로직 실행")
            search_floor = floor if floor else 1

            # 해당 층의 모든 실제 용도 확인 (층별개요에서)
            # 한 층에 여러 용도가 있을 수 있으므로 모두 수집
            # 면적 기준 판정은 하지 않고, 건축물대장에 실제로 나와있는 용도만 표시
            floor_actual_usage_list = []
            floor_etc_usage_list = []

            if floor_result and floor_result.get(
                    'success') and floor_result.get('data'):
                for floor_info in floor_result['data']:
                    # 층 번호 필드 여러 개 시도
                    floor_num = (floor_info.get('flrNoNm', '') or
                                 floor_info.get('flrNo', '') or
                                 floor_info.get('flrNoNm1', '') or
                                 floor_info.get('flrNo1', '') or
                                 floor_info.get('flrNoNm2', '') or
                                 floor_info.get('flrNo2', ''))

                    floor_num_str = str(floor_num).strip()
                    search_floor_str = str(search_floor)

                    # 정확한 층 매칭
                    is_match = False
                    if floor_num_str == search_floor_str:
                        is_match = True
                    elif floor_num_str == f"{search_floor_str}층":
                        is_match = True
                    elif floor_num_str == f"{search_floor_str}F":
                        is_match = True
                    elif floor_num_str.startswith(f"{search_floor_str}층"):
                        if len(floor_num_str) == len(f"{search_floor_str}층") or (len(floor_num_str) > len(
                                f"{search_floor_str}층") and not floor_num_str[len(f"{search_floor_str}층") - 1].isdigit()):
                            is_match = True
                    elif search_floor == 1:
                        if ('1층' in floor_num_str and '11층' not in floor_num_str and '21층' not in floor_num_str) or floor_num_str == '1' or floor_num_str.startswith(
                                '1층'):
                            is_match = True

                    if is_match:
                        # 해당 층의 용도 정보 (여러 필드명 시도)
                        main_usage = (floor_info.get('mainPurpsCdNm', '') or
                                      floor_info.get('mainPurps', '') or
                                      floor_info.get('mainPurpsCdNm1', '') or
                                      floor_info.get('mainPurps1', ''))
                        other_usage = (floor_info.get('etcPurps', '') or
                                       floor_info.get('etcPurps1', ''))

                        # 건물 전체 용도 필터링 (해당 층의 실제 용도가 아닌 것들)
                        # 다가구주택, 다중주택, 단독주택 등은 건물 전체 용도이므로 제외
                        building_wide_usages = [
                            '다가구주택', '다중주택', '단독주택', '공동주택', '아파트', '연립', '다세대']

                        # 제외할 용도 키워드 (계단실, 공유부분 등)
                        excluded_keywords = ['계단실', '공유부분', '공유 부분']

                        # main_usage가 건물 전체 용도인지 확인
                        is_building_wide_main = any(
                            bwu in str(main_usage) for bwu in building_wide_usages)

                        # main_usage에 제외 키워드가 포함되어 있는지 확인
                        main_has_excluded = any(
                            keyword in str(main_usage) for keyword in excluded_keywords)

                        # other_usage에 제외 키워드가 포함되어 있는지 확인
                        other_has_excluded = any(
                            keyword in str(other_usage) for keyword in excluded_keywords)

                        # etcPurps에 mainPurpsCdNm이 포함되어 있는지 확인
                        # 예: mainPurpsCdNm="사무소", etcPurps="제2종근린생활시설(사무소-사무소)"
                        # 이 경우 etcPurps가 더 상세한 정보이므로 etcPurps만 사용
                        if main_usage and other_usage:
                            # main_usage가 건물 전체 용도이거나 제외 키워드가 포함되어 있으면 제외
                            if is_building_wide_main or main_has_excluded:
                                # etcPurps만 추가 (etcPurps에 실제 층 용도가 있을 수 있음, 단
                                # 제외 키워드가 없어야 함)
                                if other_usage and not other_has_excluded and other_usage not in floor_etc_usage_list:
                                    floor_etc_usage_list.append(other_usage)
                            else:
                                # etcPurps에 mainPurpsCdNm이 포함되어 있으면 mainPurpsCdNm은 생략
                                # "사무소"가 "제2종근린생활시설(사무소-사무소)" 안에 포함되어 있음
                                if main_usage in other_usage:
                                    # etcPurps가 더 상세한 정보이므로 etcPurps만 추가 (제외
                                    # 키워드 없어야 함)
                                    if not other_has_excluded and other_usage not in floor_etc_usage_list:
                                        floor_etc_usage_list.append(
                                            other_usage)
                                else:
                                    # 서로 다른 정보이면 둘 다 추가 (4층처럼 실제로 두 개가 있는 경우)
                                    # 단, 제외 키워드가 없어야 함
                                    if not main_has_excluded and main_usage not in floor_actual_usage_list:
                                        floor_actual_usage_list.append(
                                            main_usage)
                                    if not other_has_excluded and other_usage not in floor_etc_usage_list:
                                        floor_etc_usage_list.append(
                                            other_usage)
                        elif main_usage:
                            # main_usage만 있는 경우 - 건물 전체 용도가 아니고 제외 키워드가 없어야 추가
                            if not is_building_wide_main and not main_has_excluded:
                                if main_usage not in floor_actual_usage_list:
                                    floor_actual_usage_list.append(main_usage)
                        elif other_usage:
                            # other_usage만 있는 경우 - 제외 키워드가 없어야 추가
                            if not other_has_excluded and other_usage not in floor_etc_usage_list:
                                floor_etc_usage_list.append(other_usage)

            # 모든 용도를 하나의 리스트로 합치기 (중복 제거)
            all_floor_usages = []
            for usage in floor_actual_usage_list:
                if usage and usage not in all_floor_usages:
                    all_floor_usages.append(usage)
            for usage in floor_etc_usage_list:
                if usage and usage not in all_floor_usages:
                    all_floor_usages.append(usage)

            # usage_judgment의 judged_usage를 우선 사용 (면적 기준 분류 적용)
            # judged_usage가 있으면 그것을 사용하고, 없으면 all_floor_usages 사용
            judged_usage = usage_judgment.get(
                'judged_usage') if usage_judgment else None

            debug_usage_decision.append(f"층별개요에서 추출한 용도 목록:")
            debug_usage_decision.append(
                f"  floor_actual_usage_list: {floor_actual_usage_list}")
            debug_usage_decision.append(
                f"  floor_etc_usage_list: {floor_etc_usage_list}")
            debug_usage_decision.append(
                f"  all_floor_usages: {all_floor_usages}")
            debug_usage_decision.append(
                f"usage_judgment에서 가져온 judged_usage: {judged_usage}")

            # Case B: API에서 해당층 용도를 먼저 확인하고, 소분류는 면적 기준으로 대분류로 변환
            # 주택 관련 용도 우선 판정은 제거 (API 용도를 먼저 확인해야 함)
            if not final_usage:
                # judged_usage가 있고 "확인요망"이 아니면 면적 기준으로 분류된 용도 사용
                if judged_usage and judged_usage != "확인요망":
                    final_usage = judged_usage
                    # usage_judgment에서 show_usage_warning 플래그 가져오기
                    show_usage_warning = usage_judgment.get(
                        'show_usage_warning', False) if usage_judgment else False
                    debug_usage_decision.append(
                        f"→ final_usage = judged_usage: {final_usage}, show_usage_warning: {show_usage_warning}")
                elif all_floor_usages:
                    # judged_usage가 없거나 "확인요망"이면 건축물대장에 해당 층에 실제로 나와있는 용도 사용
                    # 단, 면적이 있으면 면적 기준 판정 시도 (사무소의 경우)
                    first_usage = all_floor_usages[0] if all_floor_usages else None
                    # 면적 정보 확인 (여러 소스에서 시도)
                    area_for_judgment = None
                    if area_comparison and area_comparison.get(
                            'registry_area'):
                        area_for_judgment = area_comparison['registry_area']
                    elif usage_judgment and usage_judgment.get('area_m2'):
                        area_for_judgment = usage_judgment['area_m2']
                    elif registry_area:
                        area_for_judgment = registry_area

                    # all_floor_usages의 용도 문자열을 면적 기준 판정을 통해 대분류로 변환
                    # Case A의 로직과 동일하게 적용
                    usage_str_for_judgment = ', '.join(
                        all_floor_usages) if all_floor_usages else None

                    if usage_str_for_judgment and area_for_judgment:
                        judged_usage_from_floor = None
                        usage_str_for_judgment_lower = usage_str_for_judgment
                        first_usage = all_floor_usages[0] if all_floor_usages else None

                        # "점포 및 주택" 같은 복합 용도 감지 (판정 불가 - 원본 그대로 표시)
                        if first_usage and ('점포 및 주택' in str(first_usage) or '주택 및 점포' in str(first_usage) or (
                                '점포' in str(first_usage) and '주택' in str(first_usage) and '및' in str(first_usage))):
                            # 복합 용도는 판정하지 않고 원본 그대로 사용 (나중에 빨간색 굵은 글씨로 표시)
                            judged_usage_from_floor = None  # 판정하지 않음
                            debug_usage_decision.append(
                                f"→ 복합 용도 감지 (점포 및 주택 등): {first_usage}, 원본 그대로 표시")
                        else:
                            # 1. 판매시설 판정 (면적에 관계없이 무조건 "판매시설")
                            if not judged_usage_from_floor:
                                sales_facility_keywords = ['판매시설', '기타판매시설']
                                is_sales_facility = any(
                                    keyword in usage_str_for_judgment_lower for keyword in sales_facility_keywords)
                                if is_sales_facility:
                                    judged_usage_from_floor = '판매시설'

                            # 2. 소매점, 점포, 상가 판정 (1000㎡ 기준)
                            # 단, "점포 및 주택"은 이미 복합 용도로 감지되었으므로 제외
                            if not judged_usage_from_floor:
                                retail_keywords = [
                                    '소매점', '슈퍼마켓', '마트', '편의점', '상점', '매장', '일용품', '점포', '상가']
                                is_retail = any(
                                    keyword in usage_str_for_judgment_lower for keyword in retail_keywords)
                                if is_retail:
                                    # "점포"만 있는 경우 (면적 1000㎡ 미만)
                                    if '점포' in usage_str_for_judgment_lower and area_for_judgment < 1000 and '및' not in usage_str_for_judgment_lower and '주택' not in usage_str_for_judgment_lower:
                                        judged_usage_from_floor = '제1종 근린생활시설__점포__'  # 마커 추가
                                    elif area_for_judgment < 1000:
                                        judged_usage_from_floor = '제1종 근린생활시설'
                                    else:
                                        judged_usage_from_floor = '판매시설'

                        # 3. 휴게음식점, 커피숍, 제과점 판정
                        if not judged_usage_from_floor:
                            cafe_keywords = [
                                '휴게음식점', '커피숍', '제과점', '카페', '음식점']
                            is_cafe = any(
                                keyword in usage_str_for_judgment_lower for keyword in cafe_keywords)
                            if is_cafe:
                                if area_for_judgment < 300:
                                    judged_usage_from_floor = '제1종 근린생활시설'
                                else:
                                    judged_usage_from_floor = '제2종 근린생활시설'

                        # 4. 일반음식점, 안마시술소, 노래연습장 판정
                        if not judged_usage_from_floor:
                            general_food_keywords = [
                                '일반음식점', '안마시술소', '노래연습장', '노래방']
                            is_general_food = any(
                                keyword in usage_str_for_judgment_lower for keyword in general_food_keywords)
                            if is_general_food:
                                judged_usage_from_floor = '제2종 근린생활시설'

                        # 5. 이용원, 미용원, 목욕장, 세탁소 판정
                        if not judged_usage_from_floor:
                            service_keywords = [
                                '이용원', '미용원', '목욕장', '세탁소', '미용실', '이발소']
                            is_service = any(
                                keyword in usage_str_for_judgment_lower for keyword in service_keywords)
                            if is_service:
                                judged_usage_from_floor = '제1종 근린생활시설'

                        # 6. 의원, 치과의원, 한의원, 안마원, 산후조리원 판정
                        if not judged_usage_from_floor:
                            medical_keywords = [
                                '의원', '치과의원', '한의원', '안마원', '산후조리원', '병원', '의료원']
                            is_medical = any(
                                keyword in usage_str_for_judgment_lower for keyword in medical_keywords)
                            if is_medical:
                                judged_usage_from_floor = '제1종 근린생활시설'

                        # 7. 사무소, 사무실, 부동산중개소, 금융업소 판정
                        if not judged_usage_from_floor:
                            office_keywords = [
                                '사무소', '사무실', '부동산중개소', '금융업소', '중개소', '은행', '금융']
                            is_office = any(
                                keyword in usage_str_for_judgment_lower for keyword in office_keywords)
                            if is_office:
                                if area_for_judgment < 30:
                                    judged_usage_from_floor = '제1종 근린생활시설'
                                elif area_for_judgment < 500:
                                    judged_usage_from_floor = '제2종 근린생활시설'
                                else:
                                    judged_usage_from_floor = '업무시설'

                        # 8. 학원, 교습소, 직업훈련소 판정
                        if not judged_usage_from_floor:
                            academy_keywords = ['학원', '교습소', '직업훈련소', '학원시설']
                            is_academy = any(
                                keyword in usage_str_for_judgment_lower for keyword in academy_keywords)
                            if is_academy:
                                if area_for_judgment < 500:
                                    judged_usage_from_floor = '제2종 근린생활시설'
                                else:
                                    judged_usage_from_floor = '업무시설'

                        # 9. 제1종/제2종 근린생활시설이 명시된 경우 그대로 사용
                        if not judged_usage_from_floor:
                            if '제1종 근린생활시설' in usage_str_for_judgment_lower or '제1종근린생활시설' in usage_str_for_judgment_lower:
                                judged_usage_from_floor = '제1종 근린생활시설'
                            elif '제2종 근린생활시설' in usage_str_for_judgment_lower or '제2종근린생활시설' in usage_str_for_judgment_lower:
                                judged_usage_from_floor = '제2종 근린생활시설'

                        if judged_usage_from_floor:
                            final_usage = judged_usage_from_floor
                            debug_usage_decision.append(
                                f"→ final_usage = 면적 기준 판정 ({usage_str_for_judgment} + {area_for_judgment}㎡): {final_usage}")
                        else:
                            # 판정 실패 시 원본 사용 (하지만 "제2종 근린생활시설" 같은 법정 분류가 포함되어
                            # 있으면 그대로 사용)
                            if '제1종' in usage_str_for_judgment_lower or '제2종' in usage_str_for_judgment_lower or '근린생활시설' in usage_str_for_judgment_lower:
                                final_usage = usage_str_for_judgment
                                debug_usage_decision.append(
                                    f"→ final_usage = usage_str_for_judgment (제1종/제2종 포함): {final_usage}")
                            else:
                                # 상세 용도인 경우 실제 용도 + (확인요망)으로 표시
                                final_usage = f"{usage_str_for_judgment}(확인요망)"
                                debug_usage_decision.append(
                                    f"→ final_usage = {usage_str_for_judgment}(확인요망) (상세 용도로 판정 실패)")
                    elif usage_str_for_judgment:
                        # 면적 정보가 없으면 원본 사용 (하지만 "제2종 근린생활시설" 같은 법정 분류가 포함되어 있으면
                        # 그대로 사용)
                        if '제1종' in usage_str_for_judgment or '제2종' in usage_str_for_judgment or '근린생활시설' in usage_str_for_judgment:
                            final_usage = usage_str_for_judgment
                            debug_usage_decision.append(
                                f"→ final_usage = usage_str_for_judgment (제1종/제2종 포함, 면적 없음): {final_usage}")
                        else:
                            # 상세 용도로 판정 실패: 원본 용도 그대로 표시하되 확인 메시지 추가
                            final_usage = usage_str_for_judgment
                            show_usage_warning = True  # 확인 메시지 표시
                            debug_usage_decision.append(
                                f"→ final_usage = usage_str_for_judgment (상세 용도, 확인 필요, 면적 없음): {final_usage}")
                    else:
                        final_usage = "확인요망"
                        debug_usage_decision.append(
                            f"→ final_usage = 확인요망 (용도 정보 없음)")
                else:
                    # 해당 층 용도 정보가 없으면 area_result (전유공용면적 API)에서 확인
                    debug_usage_decision.append(
                        f"[층별개요에서 용도 못 찾음] area_result에서 용도 확인 시도...")

                    usage_from_area_result = None
                    try:
                        if area_result and area_result.get(
                                'success') and area_result.get('data'):
                            ho_normalized = str(ho).replace(
                                '호', '').strip() if ho else None
                            for area_info in area_result['data']:
                                # 층 매칭
                                floor_num_str = str(
                                    area_info.get(
                                        'flrNoNm', '') or area_info.get(
                                        'flrNo', '')).strip()
                                is_floor_match = False

                                # 층 정보가 있을 때만 매칭
                                if floor is not None:
                                    # 지하층 처리
                                    if floor < 0:
                                        if f"지{
                                                abs(floor)}" in floor_num_str or f"B{
                                                abs(floor)}" in floor_num_str:
                                            is_floor_match = True
                                    elif str(floor) in floor_num_str or f"{floor}층" in floor_num_str:
                                        is_floor_match = True
                                else:
                                    # 층 정보가 없으면 모든 층 허용
                                    is_floor_match = True

                                if is_floor_match:
                                    # 호수 매칭 (호수가 있으면)
                                    if ho_normalized:
                                        area_ho_nm = str(
                                            area_info.get(
                                                'hoNm', '')).replace(
                                            '호', '').strip()
                                        if area_ho_nm != ho_normalized:
                                            continue  # 호수 불일치

                                    # 용도 추출
                                    etc_purps = area_info.get('etcPurps', '')
                                    main_purps = area_info.get(
                                        'mainPurpsCdNm', '')

                                    if etc_purps:
                                        usage_from_area_result = etc_purps
                                        debug_usage_decision.append(
                                            f"  ✅ area_result에서 etcPurps 발견: {etc_purps}")
                                        break
                                    elif main_purps:
                                        usage_from_area_result = main_purps
                                        debug_usage_decision.append(
                                            f"  ✅ area_result에서 mainPurpsCdNm 발견: {main_purps}")
                                        break

                        if usage_from_area_result:
                            # 면적 정보 확인
                            area_for_judgment = None
                            if area_comparison and area_comparison.get(
                                    'registry_area'):
                                area_for_judgment = area_comparison['registry_area']
                            elif usage_judgment and usage_judgment.get('area_m2'):
                                area_for_judgment = usage_judgment['area_m2']
                            elif registry_area:
                                area_for_judgment = registry_area

                            # 용도 판정 시도
                            if area_for_judgment:
                                usage_lower = usage_from_area_result.lower()

                                # 음식점 계열 판정
                                if '대중음식점' in usage_lower or '일반음식점' in usage_lower:
                                    if area_for_judgment < 300:
                                        final_usage = '제1종 근린생활시설'
                                    else:
                                        final_usage = '제2종 근린생활시설'
                                    debug_usage_decision.append(
                                        f"  → 음식점 판정: {final_usage} (면적: {area_for_judgment}㎡)")
                                elif '휴게음식점' in usage_lower:
                                    if area_for_judgment < 300:
                                        final_usage = '제1종 근린생활시설'
                                    else:
                                        final_usage = '제2종 근린생활시설'
                                    debug_usage_decision.append(
                                        f"  → 휴게음식점 판정: {final_usage} (면적: {area_for_judgment}㎡)")
                                elif '제1종' in usage_from_area_result or '제2종' in usage_from_area_result:
                                    final_usage = usage_from_area_result
                                    debug_usage_decision.append(
                                        f"  → 제1종/제2종 포함: {final_usage}")
                                else:
                                    # 판정 실패: 실제 용도 + (확인요망)
                                    final_usage = f"{usage_from_area_result}(확인요망)"
                                    debug_usage_decision.append(
                                        f"  → 판정 실패: {final_usage}")
                            else:
                                # 면적 없음: 실제 용도 + (확인요망)
                                final_usage = f"{usage_from_area_result}(확인요망)"
                                debug_usage_decision.append(
                                    f"  → 면적 정보 없음: {final_usage}")
                        else:
                            # area_result에서도 못 찾음
                            final_usage = "확인요망"
                            debug_usage_decision.append(
                                f"→ final_usage = 확인요망 (area_result에서도 용도 못 찾음)")
                    except Exception as e:
                        # area_result 처리 중 에러 발생 시 확인요망으로 처리
                        final_usage = "확인요망"
                        debug_usage_decision.append(
                            f"⚠️ area_result 처리 중 에러 발생: {str(e)}")
                        debug_usage_decision.append(
                            f"→ final_usage = 확인요망 (에러 발생)")

        if not final_usage:
            final_usage = "확인요망"
            debug_usage_decision.append(
                f"→ final_usage = 확인요망 (최종 체크에서 None 발견)")

        debug_usage_decision.append(f"\n최종 final_usage: {final_usage}")

        # 디버깅 파일 저장
        try:
            with open('usage_decision_debug.txt', 'w', encoding='utf-8') as f:
                f.write('\n'.join(debug_usage_decision))
        except BaseException:
            pass

        # 입력 용도와 결과 용도 비교 (빨간색 굵은 글씨로 표시 및 경고 메시지 표시)
        input_usage = parsed.get('usage', '')
        # 파싱된 용도가 없으면 원본 텍스트에서 직접 추출 시도
        if not input_usage:
            try:
                # kakao_text가 있으면 사용, 없으면 parsed의 raw_text 사용
                if hasattr(self, 'kakao_text') and self.kakao_text:
                    try:
                        kakao_text = self.kakao_text.get(1.0, tk.END).strip()
                    except BaseException:
                        kakao_text = parsed.get('raw_text', '')
                else:
                    kakao_text = parsed.get('raw_text', '')
                # 원본 텍스트에서 용도 키워드 직접 검색
                usage_keywords = [
                    '판매시설',
                    '기타판매시설',
                    '제1종',
                    '제2종',
                    '1종',
                    '2종',
                    '근생',
                    '근린',
                    '사무소',
                    '사무실',
                    '상가',
                    '점포',
                    '소매점',
                    '휴게음식점',
                    '일반음식점',
                    '학원']
                for keyword in usage_keywords:
                    if keyword in kakao_text:
                        input_usage = keyword
                        break
            except BaseException:
                pass

        input_usage_normalized = self._normalize_usage(input_usage)
        final_usage_normalized = self._normalize_usage(final_usage)

        # 용도 비교: 입력 용도와 결과 용도가 다르면 빨간색 굵은 글씨로 표시 및 경고 메시지 표시
        if input_usage_normalized and final_usage_normalized and input_usage_normalized != final_usage_normalized:
            # 입력 용도와 결과 용도가 다른 경우 빨간색 굵은 글씨로 표시
            lines.append(f"• 중개대상물 종류: {final_usage}")
            lines.append("__USAGE_MISMATCH__")  # 불일치 마커 추가 (다음 줄에서 처리)
            # 경고 메시지 표시 플래그 설정
            show_usage_mismatch_warning = True
        elif show_usage_warning:  # 용도 판정 경고가 있는 경우 (예: 점포 및 주택)
            lines.append(f"• 중개대상물 종류: {final_usage} (건축물 용도를 한번 더 확인해주세요!)")
            lines.append("__USAGE_NEEDS_CHECK__")  # 확인 필요 마커 추가
        else:
            lines.append(f"• 중개대상물 종류: {final_usage}")
            show_usage_mismatch_warning = False

        # 5. 거래형태: 고정값
        lines.append("• 거래형태: 임대차계약(월세)")

        # 6. 총층수: 공통 메서드 사용
        total_floors = self.get_total_floors(building)
        if total_floors and total_floors > 0:
            lines.append(f"• 총층수: {total_floors}층")
        else:
            lines.append("• 총층수: 확인요망")

        # 7. 해당 층: 카톡에서 층수 추출, 없으면 "확인요망"
        if floor:
            lines.append(f"• 해당 층: {floor}층")
        else:
            lines.append("• 해당 층: 확인요망")

        # 8. 입주 가능일: 고정값
        lines.append("• 입주 가능일: 즉시 입주")

        # 9. 사용승인일: 공통 메서드 사용
        approval_date = self.get_approval_date(building)
        if approval_date:
            lines.append(f"• 사용승인일: {approval_date}")
        else:
            lines.append("• 사용승인일: 확인요망")

        # 10. 화장실 수: 카톡에서 추출 (새로운 로직)
        bathroom_count = parsed.get('bathroom_count')
        raw_text = parsed.get('raw_text', '')

        # 화장실 표기 로직:
        # 1. 특수 표현 유지: "남녀별도 각 1개씩", "각 1개" 등은 그대로 표시
        # 2. 명확한 숫자: "화장실 2개" -> "2개"
        # 3. 개수 없음: "1개 (화장실 개수 확인 필요)" 빨간색 표시
        # 4. "내부/외부" 구분은 생략

        bathroom_display = None
        needs_confirmation = False

        if bathroom_count is not None:
            # 숫자인 경우: "X개" 형식
            if isinstance(bathroom_count, int):
                bathroom_display = f"{bathroom_count}개"
            else:
                # 문자열인 경우
                bathroom_str = str(bathroom_count)

                # 특수 표현 확인: "남녀", "각", "별도" 등이 포함된 경우 그대로 사용
                if any(
                    keyword in bathroom_str for keyword in [
                        '남녀',
                        '각',
                        '별도',
                        '씩']):
                    # 특수 표현은 그대로 사용 (내부/외부 제거)
                    # "내부" 또는 "외부" 키워드 제거
                    cleaned = bathroom_str.replace(
                        '내부', '').replace(
                        '외부', '').strip()
                    # 연속된 공백 정리
                    cleaned = re.sub(r'\s+', ' ', cleaned)
                    bathroom_display = cleaned
                else:
                    # 일반 숫자 추출 시도
                    number_match = re.search(r'(\d+)', bathroom_str)
                    if number_match:
                        num = int(number_match.group(1))
                        bathroom_display = f"{num}개"
                    else:
                        # 숫자가 없으면 기본값 1개 + 확인 필요
                        bathroom_display = "1개"
                        needs_confirmation = True
        else:
            # bathroom_count가 None인 경우 - 번호 리스트에서 재추출 시도
            # 번호 리스트 영역만 찾아서 화장실 수 추출 (하단 설명란 무시)
            lines_list = str(raw_text).split('\n')
            numbered_bathroom_line = None

            # 번호 리스트 영역 찾기 (1., 2., 3. 등으로 시작하는 행들)
            in_numbered_list = False
            for line in lines_list[1:]:  # 첫 줄(주소) 제외
                line = line.strip()
                if re.match(r'^\d+\.\s*', line):
                    in_numbered_list = True
                    # 화장실 관련 키워드 확인 (화장실, 욕실, W.C 등)
                    if any(
                        keyword in line for keyword in [
                            '화장실',
                            '욕실',
                            'W.C',
                            'wc',
                            'WC']):
                        numbered_bathroom_line = line
                        break  # 첫 번째 매칭된 행만 사용
                elif in_numbered_list:
                    # 이미 번호 리스트 영역에 진입했다가 번호가 아닌 행이 나오면 종료
                    break

            if numbered_bathroom_line:
                # 번호 리스트 영역에서 화장실 수 추출 (모든 특수기호 지원: :, -, =, _)
                # "3개 옆에 3개" 같은 경우 첫 번째 숫자만 추출

                # 1. "상가화장실 [특수기호] 숫자개" 형식
                sanga_match = re.search(
                    r'상가\s*화장실\s*[:=,\-–_\s]+\s*(\d+)\s*개',
                    numbered_bathroom_line,
                    re.IGNORECASE)
                if sanga_match:
                    num = int(sanga_match.group(1))
                    bathroom_display = f"{num}개"
                else:
                    # 2. "화장실 [특수기호] 숫자개" 형식 (모든 특수기호 허용)
                    match_with_count = re.search(
                        r'화장실\s*[:=,\-–_\s]+\s*(\d+)\s*개', numbered_bathroom_line)
                    if match_with_count:
                        num = int(match_with_count.group(1))
                        bathroom_display = f"{num}개"
                    else:
                        # 3. "화장실 숫자개" 형식 (공백만)
                        match_direct = re.search(
                            r'화장실\s+(\d+)\s*개', numbered_bathroom_line)
                        if match_direct:
                            num = int(match_direct.group(1))
                            bathroom_display = f"{num}개"
                        else:
                            # 4. 화장실 키워드 뒤 첫 번째 숫자만 추출
                            idx = numbered_bathroom_line.find('화장실')
                            if idx >= 0:
                                after_bathroom = numbered_bathroom_line[idx + len(
                                    '화장실'):idx + len('화장실') + 30]
                                number_match = re.search(
                                    r'[:=,\-–_\s]*\s*(\d+)', after_bathroom)
                                if number_match:
                                    num = int(number_match.group(1))
                                    bathroom_display = f"{num}개"
                                else:
                                    bathroom_display = "1개"
                                    needs_confirmation = True
                            else:
                                bathroom_display = "1개"
                                needs_confirmation = True
            else:
                # 번호 리스트에서 화장실 정보를 찾지 못한 경우
                bathroom_display = "1개"
                needs_confirmation = True

        # 결과 출력 (확인 필요 문구는 빨간색으로 표시)
        if needs_confirmation:
            # 접두사와 기본값을 함께 추가하고, 경고 마커를 별도로 추가
            lines.append(f"• 화장실 수: {bathroom_display}")
            lines.append("__BATHROOM_WARNING__")  # 경고 표시 마커 (다음 줄에서 처리)
        else:
            lines.append(f"• 화장실 수: {bathroom_display}")

        # 11. 주차: 건축물대장 주차대수 (공통 메서드 사용)
        parking_spaces = self.get_parking_count(building)
        lines.append(f"• 주차: {parking_spaces}대")

        # 12. 방향: 카톡에서 추출
        direction = parsed.get('direction', '')
        if direction:
            lines.append(f"• 방향: {direction} (주출입문 기준)")
        else:
            lines.append("• 방향: 확인요망")

        # 13. 건축물대장상 위반 건축물: 4~n번 항목 + 소재지 위쪽 체크
        # 위반건축물 판정 로직:
        # 1. 불법건축물 체크 (최우선)
        #    - 4~n번에 "대장 위반", "위반건축물", "불법건축물" 등
        #    - 소재지 위쪽에 "**불법건축물**" 표시
        # 2. 정상 키워드 체크 (4~n번)
        # 3. 둘 다 없으면 "확인요망"

        # 카카오톡 원본 텍스트
        raw_text = parsed.get('raw_text', '')
        lines_raw = raw_text.split('\n')

        # 4~n번 항목 텍스트 수집 (번호가 끝나는 시점까지만)
        numbered_items_text = []
        in_numbered_section = False

        for line in lines_raw:
            line_stripped = line.strip()

            # 번호 패턴: "4.", "5.", "6." 등 (1~3번은 제외)
            if re.match(r'^([4-9]|[1-9]\d+)[.)\s]', line_stripped):
                in_numbered_section = True
                # 번호 뒤의 내용 추출 (예: "4. 내용" → "내용")
                content = re.sub(
                    r'^([4-9]|[1-9]\d+)[.)\s]+', '', line_stripped)
                numbered_items_text.append(content)
            elif in_numbered_section:
                # 번호가 끝난 후 나오는 텍스트는 무시
                # 빈 줄이나 번호가 아닌 줄이 나오면 종료
                if not line_stripped or not line_stripped[0].isdigit():
                    # 단, 이전 항목의 연속인 경우는 포함 (들여쓰기 등)
                    # 새로운 섹션이 시작되면 종료
                    if line_stripped and not any(
                        char in line_stripped for char in [
                            '※', '★', '▶', '■', '□', '◆', '◇']):
                        # 줄이 비어있지 않고, 특수 기호로 시작하지 않으면 계속 수집
                        continue
                    break

        # 4~n번 항목을 하나의 문자열로 합침
        items_text = ' '.join(numbered_items_text)
        items_lower = items_text.lower()

        # 띄어쓰기와 특수기호 제거한 버전 (더 정확한 검색)
        items_text_cleaned = re.sub(r'[\s\-_*#~=]', '', items_text)
        items_lower_cleaned = items_text_cleaned.lower()

        # 소재지(주소) 찾기 - 첫 번째 줄 또는 주소로 보이는 줄
        address_line_idx = 0
        for idx, line in enumerate(lines_raw):
            line_stripped = line.strip()
            # 번호로 시작하지 않고, 주소처럼 보이는 줄 (동, 로, 길 등 포함)
            if line_stripped and not line_stripped[0].isdigit():
                # 주소 키워드가 있으면
                if any(
                    keyword in line_stripped for keyword in [
                        '동',
                        '로',
                        '길',
                        '구',
                        '시',
                        '읍',
                        '면']):
                    address_line_idx = idx
                    break

        # 소재지 위쪽 텍스트 (소재지 이전 모든 줄)
        above_address_text = ''
        if address_line_idx > 0:
            above_address_text = '\n'.join(lines_raw[:address_line_idx])

        above_address_lower = above_address_text.lower()

        # === 1단계: 불법건축물 체크 (최우선) ===
        # 띄어쓰기와 특수기호를 무시하고 키워드 검색
        illegal_keywords = [
            '대장위반건축물', '대장위반건축', '대장불법건축물', '대장불법건축',
            '위반건축물', '위반건축', '불법건축물', '불법건축',
            '대장위반', '대장불법',
        ]

        is_illegal = False

        # 4~n번 항목에서 불법 키워드 검색 (띄어쓰기 무시)
        if items_text:
            for keyword in illegal_keywords:
                if keyword in items_lower_cleaned:
                    is_illegal = True
                    print(f"✅ [위반건축물] 키워드 '{keyword}' 발견 (4~n번 항목)")
                    break

        # 소재지 위쪽에서 "불법건축물" 검색 (특수기호 무시)
        if not is_illegal and above_address_text:
            # 특수기호 제거 후 검색
            above_cleaned = re.sub(r'[\s*#\-_=~]', '', above_address_text)
            above_cleaned_lower = above_cleaned.lower()

            for keyword in illegal_keywords:
                if keyword in above_cleaned_lower:
                    is_illegal = True
                    print(f"✅ [위반건축물] 키워드 '{keyword}' 발견 (소재지 위쪽)")
                    break

        # 불법건축물이면 바로 판정
        if is_illegal:
            lines.append("• 건축물대장상 위반 건축물: 불법건축물")
        else:
            # === 2단계: 정상 키워드 체크 (4~n번만) ===
            normal_keywords = [
                '대장이상무', '대장이상없음',
                '등기이상무', '등기이상없음',
                '대장등기이상무', '대장등기이상없음',
                '위반x', '위반없음',
                '대장상위반사항x', '대장상위반사항없음',
                '불법x', '불법없음',
                '대장위반x',
                '위반사항없음',
                '이상무', '이상없음',
                '등기o', '등기완료',
            ]

            # 4~n번 항목에서 정상 키워드 검색 (띄어쓰기 무시)
            is_normal = False
            if items_text:
                for keyword in normal_keywords:
                    if keyword in items_lower_cleaned:
                        is_normal = True
                        print(f"✅ [위반건축물] 정상 키워드 '{keyword}' 발견")
                        break

            # 최종 판정: 정상 키워드가 있으면 "해당없음", 없으면 "확인요망"
            if is_normal:
                lines.append("• 건축물대장상 위반 건축물: 해당없음")
            else:
                lines.append("• 건축물대장상 위반 건축물: 확인요망")

        # 14. 미등기 건물 판정: 4~n번 항목 체크
        # 4~n번 항목에 "미등기", "등기 없음", "등기 x" 등이 있으면 "미등기 건물" 표시

        # 미등기 키워드 목록 (띄어쓰기 무시)
        unregistered_keywords = [
            '미등기', '등기없음', '등기안됨',
            '등기x',
        ]

        # 4~n번 항목에서 미등기 키워드 검색 (띄어쓰기 무시)
        is_unregistered = False
        if items_text:
            for keyword in unregistered_keywords:
                if keyword in items_lower_cleaned:
                    is_unregistered = True
                    print(f"✅ [미등기] 키워드 '{keyword}' 발견")
                    break

        # 미등기 건물이면 결과 리스트 가장 하단에 별도 표시
        if is_unregistered:
            lines.append("• 미등기 건물")

        # 빈 줄 추가
        lines.append("")

        # 맨 마지막에 고정 문구 추가
        lines.append("총 층수는 지하층은 제외")

        # show_usage_warning, show_usage_mismatch_warning 값도 함께 반환 (경고 다이얼로그
        # 표시용)
        return lines, show_usage_warning, show_usage_mismatch_warning

    def _insert_clickable_area_line(
            self,
            line,
            actual_area,
            kakao_area,
            registry_area):
        """클릭 가능한 면적 라인 삽입 - 실면적(계약면적), 전용면적, 건축물대장 면적을 표시"""
        # "• 전용면적: " 부분은 이미 삽입되어 있음

        # 면적 값 검증 및 변환
        actual_area_float = None  # 실면적(계약면적)
        kakao_area_float = None  # 전용면적
        registry_area_float = None

        if actual_area is not None:
            try:
                if isinstance(actual_area, (int, float)):
                    actual_area_float = float(actual_area)
                elif isinstance(actual_area, str) and actual_area.strip():
                    actual_area_float = float(actual_area.strip())
            except (ValueError, TypeError):
                actual_area_float = None

        if kakao_area is not None:
            try:
                if isinstance(kakao_area, (int, float)):
                    kakao_area_float = float(kakao_area)
                elif isinstance(kakao_area, str) and kakao_area.strip():
                    kakao_area_float = float(kakao_area.strip())
            except (ValueError, TypeError):
                kakao_area_float = None

        if registry_area is not None:
            try:
                if isinstance(registry_area, (int, float)):
                    registry_area_float = float(registry_area)
                elif isinstance(registry_area, str) and registry_area.strip():
                    registry_area_float = float(registry_area.strip())
            except (ValueError, TypeError):
                registry_area_float = None

        # 면적 값이 하나도 없으면 확인요망 표시 (빨간색 굵은 글씨)
        if actual_area_float is None and kakao_area_float is None and registry_area_float is None:
            start_pos = self.result_text.index(tk.END + "-1c")
            self.result_text.insert(tk.END, "확인요망\n")
            end_pos = self.result_text.index(tk.END + "-2c")
            self.result_text.tag_add("violation_warning", start_pos, end_pos)
            return

        # 실면적(계약면적) 표시 (파란색, 굵게, 클릭 가능) - 우선 표시
        if actual_area_float is not None and actual_area_float > 0:
            actual_pyeong = int(round(actual_area_float / 3.3058, 0))
            actual_text = f"{actual_area_float}㎡ ({actual_pyeong}평) 실면적"
            start_pos = self.result_text.index(tk.END + "-1c")
            self.result_text.insert(tk.END, actual_text)
            end_pos = self.result_text.index(tk.END + "-1c")

            # 고유 태그 생성
            actual_tag = f"actual_area_{actual_area_float}"
            self.result_text.tag_add(actual_tag, start_pos, end_pos)
            self.result_text.tag_config(
                actual_tag, foreground="blue", font=(
                    '맑은 고딕', 10, 'bold'), underline=True)

            # 클릭 이벤트 바인딩
            self.result_text.tag_bind(
                actual_tag,
                "<Button-1>",
                lambda e,
                area=actual_area_float,
                source='actual': self._on_area_click(
                    area,
                    source,
                    actual_area_float,
                    kakao_area_float,
                    registry_area_float))
            self.result_text.tag_bind(
                actual_tag,
                "<Enter>",
                lambda e: self.result_text.config(
                    cursor="hand2"))
            self.result_text.tag_bind(
                actual_tag,
                "<Leave>",
                lambda e: self.result_text.config(
                    cursor=""))

        # 전용면적 표시 (파란색, 굵게, 클릭 가능) - 실면적 다음
        if kakao_area_float is not None and kakao_area_float > 0:
            # 구분자 추가 (실면적이나 다른 면적이 있으면)
            if actual_area_float is not None and actual_area_float > 0:
                self.result_text.insert(tk.END, " / ")

            kakao_pyeong = int(round(kakao_area_float / 3.3058, 0))
            kakao_text = f"{kakao_area_float}㎡ ({kakao_pyeong}평) 전용면적"
            start_pos = self.result_text.index(tk.END + "-1c")
            self.result_text.insert(tk.END, kakao_text)
            end_pos = self.result_text.index(tk.END + "-1c")

            # 고유 태그 생성
            kakao_tag = f"kakao_area_{kakao_area_float}"
            self.result_text.tag_add(kakao_tag, start_pos, end_pos)
            self.result_text.tag_config(
                kakao_tag, foreground="blue", font=(
                    '맑은 고딕', 10, 'bold'), underline=True)

            # 클릭 이벤트 바인딩
            self.result_text.tag_bind(
                kakao_tag,
                "<Button-1>",
                lambda e,
                area=kakao_area_float,
                source='kakao': self._on_area_click(
                    area,
                    source,
                    actual_area_float,
                    kakao_area_float,
                    registry_area_float))
            self.result_text.tag_bind(
                kakao_tag,
                "<Enter>",
                lambda e: self.result_text.config(
                    cursor="hand2"))
            self.result_text.tag_bind(
                kakao_tag,
                "<Leave>",
                lambda e: self.result_text.config(
                    cursor=""))

        # 건축물대장 면적 (빨간색, 굵게, 클릭 가능) - 마지막 표시
        if registry_area_float is not None and registry_area_float > 0:
            # 구분자 추가 (실면적이나 전용면적이 있으면)
            if (actual_area_float is not None and actual_area_float > 0) or (
                    kakao_area_float is not None and kakao_area_float > 0):
                self.result_text.insert(tk.END, " / ")

            registry_pyeong = int(round(registry_area_float / 3.3058, 0))
            registry_text = f"{registry_area_float}㎡ ({registry_pyeong}평) 건축물대장 면적"
            start_pos = self.result_text.index(tk.END + "-1c")
            self.result_text.insert(tk.END, registry_text)
            end_pos = self.result_text.index(tk.END + "-1c")

            # 고유 태그 생성
            registry_tag = f"registry_area_{registry_area_float}"
            self.result_text.tag_add(registry_tag, start_pos, end_pos)
            self.result_text.tag_config(
                registry_tag, foreground="red", font=(
                    '맑은 고딕', 10, 'bold'), underline=True)

            # 클릭 이벤트 바인딩
            self.result_text.tag_bind(
                registry_tag,
                "<Button-1>",
                lambda e,
                area=registry_area_float,
                source='registry': self._on_area_click(
                    area,
                    source,
                    actual_area_float,
                    kakao_area_float,
                    registry_area_float))
            self.result_text.tag_bind(
                registry_tag,
                "<Enter>",
                lambda e: self.result_text.config(
                    cursor="hand2"))
            self.result_text.tag_bind(
                registry_tag,
                "<Leave>",
                lambda e: self.result_text.config(
                    cursor=""))

            # 실면적과 건축물대장 면적이 동일한지 확인 (소수점 2자리까지 비교)
            compare_area = actual_area_float if actual_area_float is not None else kakao_area_float
            if (compare_area is not None and compare_area > 0 and
                    registry_area_float is not None and registry_area_float > 0):
                # 소수점 2자리까지 비교
                if abs(compare_area - registry_area_float) < 0.01:
                    # 동일하면 노란색 안내 문구 추가
                    self.result_text.insert(tk.END, " ")
                    same_text = "실면적과 대장면적이 동일합니다!"
                    start_pos_same = self.result_text.index(tk.END + "-1c")
                    self.result_text.insert(tk.END, same_text)
                    end_pos_same = self.result_text.index(tk.END + "-1c")

                    # 노란색 태그 생성
                    same_tag = "area_same_warning"
                    self.result_text.tag_add(
                        same_tag, start_pos_same, end_pos_same)
                    self.result_text.tag_config(
                        same_tag, foreground="orange", font=(
                            '맑은 고딕', 10, 'bold'))

        self.result_text.insert(tk.END, "\n")

    def _on_area_click(
            self,
            area,
            source,
            actual_area,
            kakao_area,
            registry_area):
        """면적 클릭 이벤트 - 클릭한 면적만 남기고 다른 면적은 제거"""
        if not area:
            return

        # 선택된 면적 정보 저장 (결과 재생성 시 사용)
        self.selected_area = {
            'area': area,
            'source': source
        }

        # 클릭한 면적만 남기고 결과 텍스트 업데이트
        result_content = self.result_text.get(1.0, tk.END)
        lines = result_content.split('\n')

        # "전용면적:" 라인 찾기
        for i, line in enumerate(lines):
            if "전용면적:" in line:
                # 클릭한 면적만 표시 (검은색으로 변경, "실면적" 또는 "건축물대장 면적" 텍스트 제거)
                pyeong = int(round(area / 3.3058, 0))
                new_line = f"• 전용면적: {area}㎡ ({pyeong}평)"

                lines[i] = new_line
                break

        # 결과 텍스트 전체 교체
        new_content = '\n'.join(lines)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, new_content)

        # 화장실 경고 문구가 있으면 다시 빨간색으로 표시 (면적 선택과 무관하게 유지)
        # 결과 텍스트에서 "화장실 개수 확인 필요" 부분 찾아서 빨간색 태그 재적용
        content_after = self.result_text.get(1.0, tk.END)
        if "(화장실 개수 확인 필요)" in content_after:
            # 모든 "화장실 개수 확인 필요" 부분 찾아서 빨간색 태그 적용
            start_idx = "1.0"
            while True:
                pos = self.result_text.search(
                    "(화장실 개수 확인 필요)", start_idx, tk.END)
                if not pos:
                    break
                # 경고 문구의 끝 위치 계산
                line_num = pos.split('.')[0]
                col_num = int(pos.split('.')[1])
                warning_end_col = col_num + len("(화장실 개수 확인 필요)")
                warning_end_idx = f"{line_num}.{warning_end_col}"
                # 빨간색 태그 적용
                self.result_text.tag_add(
                    "bathroom_warning", pos, warning_end_idx)
                # 다음 검색을 위해 시작 위치 업데이트
                start_idx = warning_end_idx + "+1c"

        # 카톡 입력 텍스트는 고정 (변경하지 않음)

    def _on_kakao_area_click(self, area):
        """카카오톡 면적 클릭 이벤트 (레거시 - 호환성 유지)"""
        if not area:
            return

        confirm = messagebox.askyesno("면적 적용",
                                      f"카카오톡 매물 면적 {area}㎡를 전용면적로 적용하시겠습니까?")

        if confirm:
            self._apply_selected_area(area, 'kakao')

    def _on_registry_area_click(self, area):
        """건축물대장 면적 클릭 이벤트 (레거시 - 호환성 유지)"""
        if not area:
            return

        confirm = messagebox.askyesno("면적 적용",
                                      f"건축물대장 전용면적 {area}㎡를 전용면적로 적용하시겠습니까?")

        if confirm:
            self._apply_selected_area(area, 'registry')

    def _apply_selected_area(self, area, source):
        """선택한 면적 적용"""
        # 카톡 입력 텍스트는 고정 (변경하지 않음)
        # 결과 재생성 (selected_area가 유지되므로 선택된 면적만 표시됨)
        self.generate_blog_ad()

    def _normalize_usage(self, usage_str):
        """용도 문자열을 정규화 (예: "2종", "제2종", "2종근생" -> "제2종 근린생활시설")"""
        if not usage_str:
            return None

        usage_str = str(usage_str).strip()

        # 판매시설은 그대로 반환
        if '판매시설' in usage_str or '기타판매시설' in usage_str:
            return '판매시설'

        # 제2종 근린생활시설 패턴 (여러 형식 지원, 우선순위: 긴 것부터)
        # "제2종근린생활시설", "2종근린생활시설", "제2종근생", "2종근생", "제2종", "2종"
        if re.search(
                r'제?2종\s*(?:근린생활시설|근생)?',
                usage_str) and not re.search(
                r'[3-9]종|1[0-9]종|2[1-9]종',
                usage_str):
            return '제2종 근린생활시설'

        # 제1종 근린생활시설 패턴 (여러 형식 지원, 우선순위: 긴 것부터)
        # "제1종근린생활시설", "1종근린생활시설", "제1종근생", "1종근생", "제1종", "1종"
        if re.search(
                r'제?1종\s*(?:근린생활시설|근생)?',
                usage_str) and not re.search(
                r'[2-9]종|1[1-9]종|2[0-9]종',
                usage_str):
            return '제1종 근린생활시설'

        return usage_str  # 정규화되지 않으면 원본 반환

    def _format_date(self, date_str):
        """날짜 형식 변환"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    def verify_naver_ad(self):
        """모드 B: 네이버부동산 교차 검수 (수동 입력 방식)"""
        try:
            # 결과 초기화
            self.result_text.delete(1.0, tk.END)
            self.status_var.set("파싱 중...")

            # 네이버 텍스트 가져오기 (placeholder 제외)
            naver_text = self.naver_text.get(1.0, tk.END).strip()

            # placeholder 텍스트인지 확인
            if naver_text == self.naver_placeholder_text.strip() or not naver_text:
                messagebox.showwarning("입력 오류", "네이버 부동산 정보를 입력해주세요.")
                self.status_var.set("준비")
                return

            # 네이버 부동산 정보 파싱
            naver_parsed = self.naver_parser.parse(naver_text)

            # 카톡 정보도 필요 (비교를 위해)
            kakao_text = self.kakao_text.get(1.0, tk.END).strip()
            kakao_parsed = None

            if kakao_text and kakao_text != self.placeholder_text.strip():
                kakao_parsed = self.kakao_parser.parse(kakao_text)

            # 결과 표시
            self.result_text.insert(tk.END, "=== 네이버 부동산 정보 ===\n\n")

            if naver_parsed.get('address'):
                self.result_text.insert(
                    tk.END, f"소재지: {
                        naver_parsed['address']}\n")
            if naver_parsed.get('deposit'):
                self.result_text.insert(
                    tk.END, f"보증금: {
                        naver_parsed['deposit']}만 원\n")
            if naver_parsed.get('monthly_rent'):
                self.result_text.insert(
                    tk.END, f"월세: {
                        naver_parsed['monthly_rent']}만 원\n")
            if naver_parsed.get('area_m2'):
                area_text = f"면적: {naver_parsed['area_m2']}㎡"
                if naver_parsed.get('area_pyeong'):
                    area_text += f" ({naver_parsed['area_pyeong']}평)"
                self.result_text.insert(tk.END, f"{area_text}\n")
            if naver_parsed.get('floor'):
                floor_text = f"해당 층: {naver_parsed['floor']}층"
                if naver_parsed.get('total_floors'):
                    floor_text += f" / 총 {naver_parsed['total_floors']}층"
                self.result_text.insert(tk.END, f"{floor_text}\n")
            if naver_parsed.get('usage'):
                self.result_text.insert(
                    tk.END, f"용도: {
                        naver_parsed['usage']}\n")
            if naver_parsed.get('bathroom_count'):
                self.result_text.insert(
                    tk.END, f"화장실 수: {
                        naver_parsed['bathroom_count']}개\n")
            if naver_parsed.get('parking'):
                self.result_text.insert(
                    tk.END, f"주차: {
                        naver_parsed['parking']}\n")
            if naver_parsed.get('direction'):
                self.result_text.insert(
                    tk.END, f"방향: {
                        naver_parsed['direction']}\n")
            if naver_parsed.get('approval_date'):
                self.result_text.insert(
                    tk.END, f"사용승인일: {
                        naver_parsed['approval_date']}\n")

            # 파싱된 정보가 없으면 안내 메시지
            if not any([naver_parsed.get('address'),
                        naver_parsed.get('deposit'),
                        naver_parsed.get('area_m2')]):
                self.result_text.insert(
                    tk.END, "\n⚠️ 주의: 네이버 부동산 정보를 파싱할 수 없습니다.\n")
                self.result_text.insert(tk.END, "입력 형식을 확인해주세요.\n\n")
                self.result_text.insert(tk.END, "예시 형식:\n")
                self.result_text.insert(tk.END, "소재지: 대구 중구 삼덕동2가 122\n")
                self.result_text.insert(tk.END, "보증금: 2,000만원\n")
                self.result_text.insert(tk.END, "월세: 150만원\n")
                self.result_text.insert(tk.END, "전용면적: 44.43㎡ (13.4평)\n")

            # 카톡 정보와 비교 (카톡 정보가 있는 경우)
            if kakao_parsed:
                self.result_text.insert(tk.END, "\n\n=== 카톡 정보와 비교 ===\n\n")
                self._compare_properties(kakao_parsed, naver_parsed)

            self.status_var.set("완료")
            messagebox.showinfo("파싱 완료", "네이버 부동산 정보를 파싱했습니다.")

        except Exception as e:
            error_msg = f"파싱 중 오류가 발생했습니다: {str(e)}"
            self.result_text.insert(tk.END, f"오류: {error_msg}\n")
            messagebox.showerror("오류", error_msg)
            self.status_var.set("오류")

    def _compare_properties(self, kakao_parsed: Dict, naver_parsed: Dict):
        """카톡 정보와 네이버 정보 비교"""
        comparisons = [
            ('소재지', 'address', 'address'),
            ('보증금', 'deposit', 'deposit'),
            ('월세', 'monthly_rent', 'monthly_rent'),
            ('면적(㎡)', 'area_m2', 'area_m2'),
            ('해당 층', 'floor', 'floor'),
            ('용도', 'usage', 'usage'),
        ]

        for label, kakao_key, naver_key in comparisons:
            kakao_value = kakao_parsed.get(kakao_key)
            naver_value = naver_parsed.get(naver_key)

            if kakao_value is not None and naver_value is not None:
                if kakao_value == naver_value:
                    self.result_text.insert(
                        tk.END, f"✓ {label}: 일치 ({kakao_value})\n")
                else:
                    self.result_text.insert(tk.END, f"⚠ {label}: 불일치\n")
                    self.result_text.insert(tk.END, f"  카톡: {kakao_value}\n")
                    self.result_text.insert(tk.END, f"  네이버: {naver_value}\n")
            elif kakao_value is not None:
                self.result_text.insert(
                    tk.END, f"ℹ {label}: 카톡만 있음 ({kakao_value})\n")
            elif naver_value is not None:
                self.result_text.insert(
                    tk.END, f"ℹ {label}: 네이버만 있음 ({naver_value})\n")

    def open_building_registry(self):
        """건축물대장 조회 사이트 열기"""
        import webbrowser
        import urllib.parse

        if not self.current_address_info or not self.current_building_info:
            messagebox.showwarning("알림", "먼저 건축물대장 정보를 조회해주세요.")
            return

        # 건축물대장 조회 사이트 URL (건축HUB)
        # 주소 정보를 기반으로 검색 URL 생성
        address = self.current_parsed.get(
            'address', '') if self.current_parsed else ''

        if address:
            # 건축HUB 검색 URL
            base_url = "https://www.eais.go.kr/"
            # 주소를 URL 인코딩하여 검색
            encoded_address = urllib.parse.quote(address)
            search_url = f"{base_url}search?q={encoded_address}"

            try:
                webbrowser.open(search_url)
                messagebox.showinfo("알림", "건축물대장 조회 사이트를 열었습니다.\n주소로 검색해주세요.")
            except Exception as e:
                messagebox.showerror("오류", f"브라우저를 열 수 없습니다:\n{str(e)}")
        else:
            # 주소가 없으면 기본 사이트만 열기
            try:
                webbrowser.open("https://www.eais.go.kr/")
                messagebox.showinfo(
                    "알림", "건축물대장 조회 사이트를 열었습니다.\n주소를 입력하여 검색해주세요.")
            except Exception as e:
                messagebox.showerror("오류", f"브라우저를 열 수 없습니다:\n{str(e)}")

    def copy_result_to_clipboard(self):
        """결과 텍스트를 클립보드에 복사 (소재지에서 번지수 제거)"""
        try:
            import re
            result_content = self.result_text.get(1.0, tk.END).strip()
            if result_content:
                # 전용면적 선택 여부 확인
                area_line_found = False
                area_selected = False

                # 결과 텍스트에서 전용면적 라인 확인
                for line in result_content.split('\n'):
                    if "전용면적:" in line or "전용면적 :" in line:
                        area_line_found = True
                        # "확인요망"이 있으면 선택되지 않은 상태
                        if "확인요망" in line:
                            area_selected = False
                        # "실면적"과 "건축물대장 면적"이 둘 다 있으면 선택되지 않은 상태
                        elif "실면적" in line and "건축물대장 면적" in line:
                            area_selected = False
                        else:
                            # 면적 값이 있고, "실면적" 또는 "건축물대장 면적" 텍스트가 없으면 선택된 상태
                            # (선택된 면적은 텍스트가 제거되어 숫자와 평수만 표시됨)
                            if re.search(
                                    r'\d+\.?\d*\s*(m2|㎡|평)', line, re.IGNORECASE):
                                # "실면적"이나 "건축물대장 면적" 텍스트가 없으면 선택 완료
                                if "실면적" not in line and "건축물대장 면적" not in line:
                                    area_selected = True
                                else:
                                    # 둘 중 하나만 있거나 둘 다 있으면 선택 전 상태
                                    area_selected = False
                        break

                # 전용면적 라인이 있는데 선택되지 않았으면 경고
                if area_line_found and not area_selected:
                    messagebox.showwarning("전용면적 선택 필요", "전용면적을 선택해주세요!")
                    return
                lines = result_content.split('\n')

                # 소재지 줄에서 번지수 제거
                for i, line in enumerate(lines):
                    if "소재지:" in line or "소재지 :" in line:
                        # 번지수 패턴 제거 (예: 137-4, 122, 122번지 등)
                        # 번지수 패턴: 숫자-숫자, 숫자번지, 숫자(쉼표/마침표/띄어쓰기 포함)
                        bunji_patterns = [
                            r'\s*\d+\s*-\s*\d+',  # 137-4 형식
                            r'\s*\d+\s*번지',     # 122번지 형식
                            r'\s+\d+\s*[,.\s]',
                            # 122, 122. 122 (쉼표/마침표/띄어쓰기 포함)
                            r'\s+\d+\s*$',        # 끝에 오는 숫자 (122)
                        ]

                        for pattern in bunji_patterns:
                            line = re.sub(pattern, '', line).strip()

                        # 동 이름까지만 유지
                        dong_patterns = [
                            r'([가-힣]+동\d+가)',  # 삼덕동3가, 동인동4가 등
                            r'([가-힣]+동)',       # 범어동, 봉산동 등
                        ]

                        dong_match = None
                        dong_end = 0
                        for pattern in dong_patterns:
                            dong_match = re.search(pattern, line)
                            if dong_match:
                                dong_end = dong_match.end()
                                break

                        if dong_match:
                            # 동 이름까지만 유지
                            line = line[:dong_end].strip()
                            # "소재지:" 또는 "소재지 :" 부분 유지
                            if "소재지:" in line:
                                prefix = "• 소재지:"
                            elif "소재지 :" in line:
                                prefix = "• 소재지 :"
                            else:
                                prefix = "• 소재지:"
                            # 동 이름만 추출
                            dong_name = dong_match.group(1)
                            # 앞부분에서 구 이름 찾기
                            gu_match = re.search(r'(대구\s*)?([가-힣]+구)', line)
                            if gu_match:
                                gu_part = gu_match.group(0).strip()
                                line = f"{prefix} {gu_part} {dong_name}"
                            else:
                                line = f"{prefix} {dong_name}"

                        lines[i] = line
                        break

                # 수정된 내용을 클립보드에 복사
                modified_content = '\n'.join(lines)
                self.root.clipboard_clear()
                self.root.clipboard_append(modified_content)
                # 버튼 텍스트를 "복사 완료 ✓"로 변경
                self.copy_btn.config(text="복사 완료 ✓")
            else:
                messagebox.showwarning("복사 실패", "복사할 내용이 없습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"복사 중 오류가 발생했습니다:\n{str(e)}")

    def clear_all(self):
        """모든 입력 및 결과 초기화"""
        # 복사 버튼 텍스트 초기화
        if hasattr(self, 'copy_btn'):
            self.copy_btn.config(text="악보가완성됐다 이기러가자!!")

        self.kakao_text.delete(1.0, tk.END)
        # placeholder 텍스트 다시 삽입
        self.kakao_text.insert(1.0, self.placeholder_text)
        self.kakao_text.tag_add("placeholder", 1.0, tk.END)
        self.is_placeholder = True
        self.naver_text.delete(1.0, tk.END)
        # placeholder 텍스트 다시 삽입
        self.naver_text.insert(1.0, self.naver_placeholder_text)
        self.naver_text.tag_add("placeholder", 1.0, tk.END)
        self.is_naver_placeholder = True
        self.result_text.delete(1.0, tk.END)
        self.status_var.set("준비")

    # ========================================
    # 🔧 모드B를 위한 유틸리티 메서드
    # ========================================

    def parse_floor_string(self, floor_str: str) -> Optional[int]:
        """
        층 문자열을 정수로 파싱

        Args:
            floor_str: 층 문자열 (예: "지하1층", "1층", "B1", "4층")

        Returns:
            int: 층수 (지하는 음수, 지상은 양수)
                 예: "지하1층" -> -1, "1층" -> 1, "4층" -> 4
            None: 파싱 실패 시

        예시:
            "지하1층" -> -1
            "지하2층" -> -2
            "1층" -> 1
            "4층" -> 4
            "B1" -> -1
            "지상1층" -> 1
        """
        if not floor_str:
            return None

        floor_str = str(floor_str).strip()

        # 지하층 패턴
        basement_patterns = [
            r'지하\s*(\d+)',  # 지하1층, 지하 1층
            r'B\s*(\d+)',     # B1, B 1
            r'b\s*(\d+)',     # b1, b 1
        ]

        for pattern in basement_patterns:
            match = re.search(pattern, floor_str, re.IGNORECASE)
            if match:
                floor_num = int(match.group(1))
                return -floor_num  # 지하는 음수

        # 지상층 패턴 (지하가 아닌 경우)
        ground_patterns = [
            r'지상\s*(\d+)',  # 지상1층, 지상 1층
            r'(\d+)\s*층',   # 1층, 4층
            r'(\d+)\s*F',    # 1F, 4F
            r'^(\d+)$',      # 1, 4 (숫자만)
        ]

        for pattern in ground_patterns:
            match = re.search(pattern, floor_str, re.IGNORECASE)
            if match:
                floor_num = int(match.group(1))
                return floor_num  # 지상은 양수

        return None

    def match_floor(self, search_floor: int, registry_floor_str: str) -> bool:
        """
        입력된 층수와 건축물대장 API의 층 문자열이 일치하는지 확인
        (모드A의 _compare_areas 메서드의 층 매칭 로직 재사용)

        Args:
            search_floor: 찾으려는 층수 (음수: 지하, 양수: 지상)
            registry_floor_str: 건축물대장 API의 층 문자열 (예: "지하1층", "1층", "지상1")

        Returns:
            bool: 일치 여부

        예시:
            match_floor(1, "1층") -> True
            match_floor(1, "지상1") -> True
            match_floor(-1, "지하1층") -> True
            match_floor(-1, "1층") -> False
            match_floor(1, "지하1층") -> False
        """
        if not registry_floor_str:
            return False

        floor_num_str = str(registry_floor_str).strip()
        search_floor_str = str(search_floor)

        # 정확한 층 매칭 (모드A 로직 100% 재사용)
        is_match = False

        # 숫자만 추출 (예: "지상1" → "1", "1층" → "1")
        floor_num_only = re.sub(r'[^0-9]', '', floor_num_str)
        search_floor_only = str(abs(search_floor))  # 절댓값으로 비교

        # 지하층 처리
        if search_floor < 0:
            # 지하층을 찾는 경우: "지하"가 반드시 포함되어야 함
            if '지하' in floor_num_str or 'B' in floor_num_str or 'b' in floor_num_str:
                if floor_num_only == search_floor_only:
                    is_match = True
        else:
            # 지상층을 찾는 경우: "지하"가 없어야 함
            if '지하' not in floor_num_str and 'B' not in floor_num_str and 'b' not in floor_num_str:
                # 정확한 문자열 일치
                if floor_num_str == search_floor_str:
                    is_match = True
                # 층 단위 포함 (우선 체크)
                elif floor_num_str == f"{search_floor_str}층":
                    is_match = True
                elif floor_num_str == f"지상{search_floor_str}" or floor_num_str == f"지상{search_floor_str}층":
                    is_match = True
                elif floor_num_str == f"{search_floor_str}F":
                    is_match = True
                # 숫자만 일치
                elif floor_num_only == search_floor_only:
                    if search_floor == 1:
                        # 1층인 경우: "지상1" 또는 "1"만 매칭 (11층, 21층 제외)
                        if '지상' in floor_num_str or floor_num_str == '1':
                            is_match = True
                    else:
                        # 1층이 아닌 경우: 숫자만 일치하면 매칭
                        is_match = True
                # "1층 일부" 같은 형식 처리
                elif floor_num_str.startswith(f"{search_floor_str}층"):
                    if len(floor_num_str) == len(f"{search_floor_str}층") or (
                        len(floor_num_str) > len(f"{search_floor_str}층") and
                        not floor_num_str[len(f"{search_floor_str}층")].isdigit()
                    ):
                        is_match = True
                # 1층 특수 처리
                elif search_floor == 1:
                    if ('지상1' in floor_num_str or '1층' in floor_num_str):
                        if '11층' not in floor_num_str and '21층' not in floor_num_str:
                            is_match = True
                    elif floor_num_str == '1':
                        is_match = True

        return is_match


if __name__ == "__main__":
    root = tk.Tk()
    app = PropertyAdSystem(root)
    root.mainloop()
