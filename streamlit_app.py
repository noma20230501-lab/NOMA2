"""
부동산 매물 광고 생성 및 교차 검증 통합 시스템 (Streamlit 웹 버전)
PropertyAdSystem의 모든 기능을 웹에서 사용 가능
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
import os
import re
import importlib.util
import json
from datetime import datetime
import base64

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ==================== 인증 및 피드백 관련 함수 ====================

def save_auth_token(token_data, nickname):
    """토큰을 로컬 파일에 저장"""
    try:
        token_file = '.auth_token.json'
        data = {
            'token_data': token_data,
            'nickname': nickname
        }
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except BaseException:
        pass


def load_auth_token():
    """로컬 파일에서 토큰 로드"""
    try:
        token_file = '.auth_token.json'
        if os.path.exists(token_file):
            with open(token_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except BaseException:
        pass
    return None


def clear_auth_token():
    """토큰 파일 삭제"""
    try:
        token_file = '.auth_token.json'
        if os.path.exists(token_file):
            os.remove(token_file)
    except BaseException:
        pass


def check_authentication():
    """인증 상태 확인"""
    # 🔓 로그인 비활성화: 항상 인증된 것으로 처리
    return True
    
    # ⬇️ 아래 코드는 로그인을 다시 활성화하려면 위의 'return True'를 주석처리하고 사용하세요
    # try:
    #     from auth_config import verify_password, is_token_valid, generate_token, create_token_data

    #     # 세션 상태 초기화
    #     if 'authenticated' not in st.session_state:
    #         st.session_state.authenticated = False
    #     if 'auth_token' not in st.session_state:
    #         st.session_state.auth_token = None
    #     if 'user_nickname' not in st.session_state:
    #         st.session_state.user_nickname = None

    #     # 파일에서 토큰 로드 시도 (한 번만)
    #     if not st.session_state.authenticated and 'token_loaded' not in st.session_state:
    #         st.session_state.token_loaded = True
    #         saved_data = load_auth_token()

    #         if saved_data:
    #             try:
    #                 token_data = saved_data['token_data']
    #                 nickname = saved_data['nickname']

    #                 # 토큰 유효성 검증
    #                 if is_token_valid(token_data):
    #                     st.session_state.auth_token = token_data
    #                     st.session_state.user_nickname = nickname
    #                     st.session_state.authenticated = True
    #                     return True
    #                 else:
    #                     # 토큰 만료 시 파일 삭제
    #                     clear_auth_token()
    #             except BaseException:
    #                 pass

    #     # 세션에서 토큰 확인
    #     if st.session_state.auth_token:
    #         if is_token_valid(st.session_state.auth_token):
    #             st.session_state.authenticated = True
    #             return True
    #         else:
    #             # 토큰 만료
    #             st.session_state.auth_token = None
    #             st.session_state.authenticated = False
    #             clear_auth_token()

    #     return st.session_state.authenticated

    # except Exception as e:
    #     st.error(f"인증 시스템 오류: {str(e)}")
    #     return False


def show_login_page():
    """로그인 페이지 표시"""
    st.set_page_config(
        page_title="부동산 매물 광고 시스템 - 로그인",
        page_icon="🔐",
        layout="wide"
    )

    st.markdown("""
        <div style="text-align: center; padding: 50px 0;">
            <h1>🏢 부동산 매물 광고 시스템</h1>
            <p style="font-size: 1.2rem; color: #666;">접속하려면 비밀번호와 이름을 입력하세요</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 로그인")

        # 로그인 폼으로 감싸서 엔터키 지원
        with st.form(key="login_form"):
            nickname = st.text_input(
                "이름 (닉네임)",
                placeholder="사용할 이름을 입력하세요 (예: 홍길동, 매물왕)",
                key="login_nickname"
            )

            password = st.text_input(
                "비밀번호",
                type="password",
                placeholder="비밀번호를 입력하세요",
                key="login_password"
            )

            # 폼 내부의 버튼 (엔터키로 제출 가능)
            login_btn = st.form_submit_button(
                "로그인", type="primary", use_container_width=True)

        if login_btn:
            if not nickname:
                st.warning("⚠️ 이름을 입력하세요.")
            elif not password:
                st.warning("⚠️ 비밀번호를 입력하세요.")
            else:
                try:
                    from auth_config import verify_password, generate_token, create_token_data

                    if verify_password(password):
                        # 토큰 생성
                        token = generate_token()
                        token_data = create_token_data(token)

                        # 세션에 저장
                        st.session_state.auth_token = token_data
                        st.session_state.authenticated = True
                        st.session_state.user_nickname = nickname

                        # 쿠키에 저장 (7일간 유지)
                        save_auth_token(token_data, nickname)

                        st.success(
                            f"✅ {nickname}님, 로그인 성공! 잠시 후 시스템으로 이동합니다...")
                        st.rerun()
                    else:
                        st.error("❌ 비밀번호가 올바르지 않습니다.")
                except Exception as e:
                    st.error(f"❌ 인증 처리 중 오류 발생: {str(e)}")

        st.markdown("---")
        st.info("""
            💡 **기본 비밀번호**: `noma`

            비밀번호를 변경하려면 `auth_config.py` 파일을 수정하세요.
        """)


def save_feedback(feedback_data):
    """피드백 저장"""
    feedback_file = 'feedbacks.json'

    try:
        # 기존 피드백 로드
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
        else:
            feedbacks = []

        # 새 피드백 추가
        feedbacks.append(feedback_data)

        # 저장
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedbacks, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        st.error(f"피드백 저장 중 오류: {str(e)}")
        return False


def show_feedback_sidebar():
    """사이드바에 피드백 버튼 및 로그아웃 표시"""
    with st.sidebar:
        st.markdown("---")

        # 사용자 정보 표시
        st.markdown("### 👤 계정")
        user_nickname = st.session_state.get('user_nickname', '사용자')
        st.caption(f"👋 {user_nickname}님")

        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.auth_token = None
            st.session_state.user_nickname = None
            clear_auth_token()  # 쿠키에서도 삭제
            st.success("로그아웃되었습니다.")
            st.rerun()

        # 토큰 만료 정보 표시
        if st.session_state.get('auth_token'):
            try:
                expiry = datetime.fromisoformat(
                    st.session_state.auth_token['expiry'])
                remaining_days = (expiry - datetime.now()).days
                st.caption(f"🕐 토큰 만료: {remaining_days}일 후")
            except BaseException:
                pass

        st.markdown("---")
        st.markdown("### 📝 오류 제보")

        if st.button("🐛 오류 제보하기", use_container_width=True):
            st.session_state.show_feedback_form = True

        # 피드백 폼 표시
        if st.session_state.get('show_feedback_form', False):
            with st.form("feedback_form"):
                st.markdown("#### 오류 제보 양식")

                # 제보자 이름 (자동)
                reporter_name = st.session_state.get('user_nickname', '익명')
                st.info(f"제보자: **{reporter_name}**")

                # 오류 유형 (필수)
                col1, col2 = st.columns(2)
                with col1:
                    mode_type = st.selectbox(
                        "모드 선택 *",
                        ["모드 A", "모드 B"],
                        key="feedback_mode"
                    )
                with col2:
                    feedback_type = st.selectbox(
                        "오류 유형 *",
                        ["버그/오류", "기능 개선 제안", "UI/UX 개선", "기타"],
                        key="feedback_type"
                    )

                # 상세 내용 (제목 삭제, 바로 내용 작성)
                description = st.text_area(
                    "오류 내용 *",
                    placeholder="오류 상황, 재현 방법, 기대했던 동작 등을 자세히 적어주세요",
                    height=200,
                    key="feedback_description"
                )

                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button(
                        "제출", type="primary", use_container_width=True)
                with col2:
                    cancel = st.form_submit_button(
                        "취소", use_container_width=True)

                if submit:
                    if description:
                        feedback_data = {
                            'id': datetime.now().strftime("%Y%m%d%H%M%S"),
                            'timestamp': datetime.now().isoformat(),
                            'reporter': reporter_name,
                            'mode': mode_type,
                            'type': feedback_type,
                            'description': description,
                            'status': 'pending'
                        }

                        if save_feedback(feedback_data):
                            st.success("✅ 제보가 완료되었습니다! 감사합니다.")
                            st.session_state.show_feedback_form = False
                            st.rerun()
                    else:
                        st.error("❌ 오류 내용을 입력해주세요.")

                if cancel:
                    st.session_state.show_feedback_form = False
                    st.rerun()


# ==================== 기존 코드 ====================

class MockTk:
    def __init__(self):
        pass

    def title(self, *args):
        pass

    def geometry(self, *args):
        pass

    def resizable(self, *args):
        pass


class MockStringVar:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class MockText:
    def __init__(self):
        self._content = ""

    def get(self, start, end):
        return self._content

    def delete(self, start, end):
        self._content = ""

    def insert(self, pos, text, *args):
        self._content += text


class MockMessageBox:
    @staticmethod
    def showwarning(*args, **kwargs):
        pass

    @staticmethod
    def showerror(*args, **kwargs):
        pass

    @staticmethod
    def showinfo(*args, **kwargs):
        pass


# Mock Widget 클래스
class MockWidget:
    def __init__(self, *args, **kwargs):
        pass

    def pack(self, *args, **kwargs):
        return self

    def grid(self, *args, **kwargs):
        return self

    def place(self, *args, **kwargs):
        return self

    def pack_forget(self, *args, **kwargs):
        pass

    def config(self, *args, **kwargs):
        pass

    def configure(self, *args, **kwargs):
        pass

    def bind(self, *args, **kwargs):
        pass

    def tag_config(self, *args, **kwargs):
        pass

    def tag_bind(self, *args, **kwargs):
        pass

    def tag_add(self, *args, **kwargs):
        pass


class MockScrolledText(MockWidget):
    def __init__(self, *args, **kwargs):
        self._content = ""

    def get(self, start, end):
        return self._content

    def delete(self, start, end):
        self._content = ""

    def insert(self, pos, text, *args):
        self._content += str(text)


# Mock ttk 모듈
class MockTtk:
    LabelFrame = MockWidget
    Frame = MockWidget
    Label = MockWidget
    Button = MockWidget
    Radiobutton = MockWidget
    Entry = MockWidget
    Combobox = MockWidget
    Notebook = MockWidget
    Treeview = MockWidget
    Scrollbar = MockWidget
    Style = MockWidget


# Mock scrolledtext 모듈
class MockScrolledTextModule:
    ScrolledText = MockScrolledText


# Tkinter 모듈 Mock
class MockTkModule:
    END = "end"
    X = "x"
    Y = "y"
    W = "w"
    BOTH = "both"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    WORD = "word"
    NORMAL = "normal"
    DISABLED = "disabled"
    SUNKEN = "sunken"
    StringVar = MockStringVar
    Text = MockText
    Tk = MockTk
    Frame = MockWidget
    Button = MockWidget
    Label = MockWidget

    # ttk, scrolledtext, messagebox를 속성으로 추가
    ttk = MockTtk
    scrolledtext = MockScrolledTextModule
    messagebox = MockMessageBox


# tkinter를 mock으로 교체
mock_tk = MockTkModule()
sys.modules["tkinter"] = mock_tk
sys.modules["tkinter.ttk"] = MockTtk
sys.modules["tkinter.scrolledtext"] = MockScrolledTextModule
sys.modules["tkinter.messagebox"] = MockMessageBox

# PropertyAdSystem import
try:
    from property_ad_system import PropertyAdSystem
    from kakao_parser import KakaoPropertyParser
    from building_registry_api import BuildingRegistryAPI
    from address_code_helper import parse_address

    PROPERTY_SYSTEM_AVAILABLE = True
except Exception as e:
    PROPERTY_SYSTEM_AVAILABLE = False
    IMPORT_ERROR = str(e)

# 페이지 설정
st.set_page_config(
    page_title="부동산 매물 광고 생성 및 검수 시스템",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="auto",
)


# 시스템 초기화
def init_system():
    """PropertyAdSystem 초기화"""
    if "system" not in st.session_state:
        if PROPERTY_SYSTEM_AVAILABLE:
            try:
                mock_root = MockTk()
                st.session_state.system = PropertyAdSystem(
                    mock_root, skip_gui=True)
                st.session_state.system_ready = True
            except Exception as e:
                st.session_state.system_ready = False
                st.session_state.system_error = str(e)
        else:
            st.session_state.system_ready = False
            st.session_state.system_error = (
                IMPORT_ERROR
                if "IMPORT_ERROR" in dir()
                else "PropertyAdSystem을 불러올 수 없습니다."
            )


if "selected_area" not in st.session_state:
    st.session_state.selected_area = None
    if "result_text" not in st.session_state:
        st.session_state.result_text = ""
    if "area_options" not in st.session_state:
        st.session_state.area_options = {}


def generate_blog_ad_web(kakao_text):
    """웹버전 블로그 광고 생성"""
    if not st.session_state.system_ready:
        return (
            None,
            f"시스템 오류: {st.session_state.get('system_error', '알 수 없는 오류')}",
        )

    system = st.session_state.system

    try:
        # 위반건축물 감지 (특수기호 포함)
        import re

        violation_detected = False
        violation_keywords = ["위반건축물", "불법건축물", "위반있음"]

        # 첫 줄에서 위반건축물 관련 텍스트 확인
        first_line = kakao_text.split("\n")[0] if kakao_text else ""
        for keyword in violation_keywords:
            # 특수기호를 제거한 버전과 비교
            cleaned_first_line = re.sub(r"[^\w\s가-힣]", "", first_line)
            if keyword in cleaned_first_line:
                violation_detected = True
                # 해당 라인을 제거하고 나머지 텍스트로 파싱
                kakao_text = "\n".join(kakao_text.split("\n")[1:])
                break

        # 파싱
        parsed = system.kakao_parser.parse(kakao_text)

        # 위반건축물 정보를 parsed에 추가
        if violation_detected:
            parsed["violation_building"] = True

        if not parsed.get("address"):
            return None, "주소를 찾을 수 없습니다."

        address = parsed["address"]
        floor = parsed.get("floor")
        ho = parsed.get("ho")
        dong = parsed.get("dong")  # 동 정보 추출

        # 주소 파싱
        address_info = parse_address(address)

        if not address_info.get(
                "sigungu_code") or not address_info.get("bjdong_code"):
            return None, f"주소를 파싱할 수 없습니다: {address}"

        # 건축물대장 조회
        title_result = system.api.get_title_info(
            sigungu_cd=address_info["sigungu_code"],
            bjdong_cd=address_info["bjdong_code"],
            bun=address_info["bun"],
            ji=address_info["ji"],
            num_of_rows=10,
        )

        if not title_result.get("success") or not title_result.get("data"):
            error_msg = title_result.get("error", "") or title_result.get(
                "resultMsg", "알 수 없는 오류"
            )
            # 디버그 정보 추가
            debug_msg = f"\n\n[디버그 정보]\n"
            debug_msg += f"주소: {address}\n"
            debug_msg += f"시군구코드: {address_info.get('sigungu_code')}\n"
            debug_msg += f"법정동코드: {address_info.get('bjdong_code')}\n"
            debug_msg += f"번: {address_info.get('bun')}\n"
            debug_msg += f"지: {address_info.get('ji')}\n"
            debug_msg += f"동: {dong}\n"
            debug_msg += f"층: {floor}\n"
            debug_msg += f"호: {ho}\n"
            return (
                None,
                f"건축물대장 정보를 조회할 수 없습니다.\n오류: {error_msg}{debug_msg}",
            )

        # 건축물 선택
        buildings = title_result["data"]

        # 동 정보로 건축물 필터링 (아파트 상가 등)
        # 디버그: 동 정보 출력
        print(f"🔍 [디버그] 파싱된 동 정보: '{dong}'")
        print(f"🔍 [디버그] 건축물 개수: {len(buildings)}")

        if dong and len(buildings) > 1:
            print(
                f"🔍 [디버그] 동 필터링 시작: dong='{dong}', buildings={len(buildings)}개"
            )
            filtered_buildings = []
            for bld in buildings:
                # API 응답에서 동 정보 추출 (다양한 필드명 시도)
                bld_dong = None
                dong_fields = [
                    "dongNm",
                    "dongNo",
                    "dong",
                    "dongNmNm",
                    "bldDongNm"]
                for field in dong_fields:
                    if field in bld and bld[field]:
                        bld_dong = str(bld[field]).strip()
                        print(f"   🔍 [디버그] 건축물 동 발견: {field}='{bld_dong}'")
                        break

                if not bld_dong:
                    print(
                        f"   ⚠️ [디버그] 동 정보 없음: 모든 필드 확인 - {list(bld.keys())}"
                    )

                # 동 번호 매칭 (입력: "111" or "111동", API: "111동" or "111")
                if bld_dong:
                    # 동 번호 정규화 (숫자만 추출)
                    import re

                    input_dong_num = re.sub(r"[^\d]", "", str(dong))
                    api_dong_num = re.sub(r"[^\d]", "", bld_dong)

                    print(
                        f"   🔍 [디버그] 동 매칭: 입력='{input_dong_num}' vs API='{api_dong_num}'")

                    if (
                        input_dong_num
                        and api_dong_num
                        and input_dong_num == api_dong_num
                    ):
                        print(f"      ✅ [디버그] 동 일치! 필터링 목록에 추가")
                        filtered_buildings.append(bld)
                    else:
                        print(f"      ❌ [디버그] 동 불일치, 필터링 제외")

            # 필터링된 건축물이 있으면 사용
            if filtered_buildings:
                print(
                    f"✅ [디버그] 필터링 완료: {len(filtered_buildings)}개 건축물 선택됨"
                )
                buildings = filtered_buildings
            else:
                print(f"⚠️ [디버그] 필터링 결과 없음, 원래 건축물 목록 사용")
        else:
            if not dong:
                print(f"⚠️ [디버그] 동 정보 없음, 필터링 건너뜀")
            elif len(buildings) <= 1:
                print(f"ℹ️ [디버그] 건축물 1개 이하, 필터링 불필요")

        # API 응답을 세션에 저장 (디버깅용)
        st.session_state.api_buildings_raw = title_result["data"]  # 원본 저장
        st.session_state.api_buildings_filtered = buildings  # 필터링된 결과 저장
        st.session_state.api_buildings_count = len(buildings)
        st.session_state.api_full_response = {
            "success": title_result.get("success"),
            "resultCode": title_result.get("resultCode"),
            "resultMsg": title_result.get("resultMsg"),
            "totalCount": (
                title_result.get("pagination", {}).get("totalCount", 0)
                if title_result.get("pagination")
                else len(buildings)
            ),
            "numOfRows": (
                title_result.get("pagination", {}).get("numOfRows", 10)
                if title_result.get("pagination")
                else 10
            ),
            "data_count": len(buildings),
            "buildings": buildings,
        }

        # 건축물이 여러 개인 경우 선택하도록 함
        if len(buildings) > 1:
            # 선택된 건축물이 있는지 확인
            selected_building_idx = st.session_state.get(
                "selected_building_idx")

            if selected_building_idx is None:
                # 건축물 목록을 저장하고 선택 UI를 표시하도록 반환
                return {
                    "buildings": buildings,
                    "parsed": parsed,
                    "address_info": address_info,
                    "need_building_selection": True,
                    "building_count": len(buildings),
                    "debug_info": f"건축물 {len(buildings)}개 발견 - 선택 필요",
                }, None
            else:
                building = buildings[selected_building_idx]
        else:
            # 건축물이 1개만 있으면 자동 선택
            building = buildings[0]

        # 층별 현황 조회
        floor_result = None
        if building and building.get("mgmBldrgstPk"):
            floor_result = system.api.get_floor_info(
                sigungu_cd=address_info["sigungu_code"],
                bjdong_cd=address_info["bjdong_code"],
                bun=address_info["bun"],
                ji=address_info["ji"],
                mgm_bldrgst_pk=building["mgmBldrgstPk"],
                num_of_rows=50,
            )

        # 전유공용면적 조회
        area_result = None
        if building and building.get("mgmBldrgstPk"):
            area_result = system.api.get_unit_area_info(
                sigungu_cd=address_info["sigungu_code"],
                bjdong_cd=address_info["bjdong_code"],
                bun=address_info["bun"],
                ji=address_info["ji"],
                mgm_bldrgst_pk=building["mgmBldrgstPk"],
                num_of_rows=100,
            )

        # 전유부 조회 (호수가 있을 때만) - 층/호수 검색용
        unit_result = None
        if ho and building and building.get("mgmBldrgstPk"):
            unit_result = system.api.get_unit_info(
                sigungu_cd=address_info["sigungu_code"],
                bjdong_cd=address_info["bjdong_code"],
                bun=address_info["bun"],
                ji=address_info["ji"],
                mgm_bldrgst_pk=building["mgmBldrgstPk"],
                num_of_rows=100,
            )

        # 같은 층의 모든 전유부분 확인 (통임대/분할임대 판단)
        selected_units_info = None  # 선택된 전유부분 정보
        if floor:
            # area_result 또는 floor_result가 있으면 전유부분 확인
            all_units = system._get_all_units_on_floor(
                area_result, floor, floor_result)

            # 전유부분이 여러 개인 경우
            if len(all_units) > 1:
                # 선택된 전유부분이 있는지 확인
                selected_unit_idx = st.session_state.get("selected_unit_idx")

                if selected_unit_idx is None:
                    # 카톡에서 파싱된 호수 정보 확인
                    input_ho = parsed.get("ho")
                    auto_matched_idx = None

                    if input_ho:
                        # 입력된 호수와 매치되는 전유부분 찾기
                        input_ho_normalized = str(
                            input_ho).replace('호', '').strip()
                        matched_units = []

                        print(f"\n[호수 매칭 디버그]")
                        print(
                            f"입력된 호수: '{input_ho}' (정규화: '{input_ho_normalized}')")
                        print(f"전유부분 목록:")

                        for idx, unit in enumerate(all_units):
                            unit_ho = unit.get('ho', '')
                            unit_ho_normalized = str(
                                unit_ho).replace('호', '').strip()

                            print(
                                f"  [{idx}] 대장 호수: '{unit_ho}' (정규화: '{unit_ho_normalized}')")

                            # 호수 매칭 (정규화된 값으로 비교)
                            if (input_ho == unit_ho or
                                input_ho_normalized == unit_ho_normalized or
                                    unit_ho_normalized.lower() == input_ho_normalized.lower()):
                                matched_units.append(idx)
                                print(
                                    f"   ✅ 호수 매칭 성공! 입력={input_ho} → 대장={unit_ho} (idx={idx})")

                        # 정확히 1개 매치되면 자동 선택
                        if len(matched_units) == 1:
                            auto_matched_idx = matched_units[0]
                            print(
                                f"\n🎯 호수 자동 선택! idx={auto_matched_idx}, 호수={
                                    all_units[auto_matched_idx].get('ho')}")
                        elif len(matched_units) > 1:
                            print(
                                f"\n⚠️ 여러 호수가 매칭됨: {matched_units} - 수동 선택 필요")
                        else:
                            print(f"\n❌ 매칭되는 호수 없음 - 수동 선택 필요")

                    # 자동 매칭된 호수가 있으면 바로 선택
                    if auto_matched_idx is not None:
                        selected_unit_idx = auto_matched_idx
                        # session_state에 저장 (재생성 시 사용)
                        st.session_state.selected_unit_idx = auto_matched_idx
                    else:
                        # 자동 매칭 실패: 선택 UI 표시
                        # 카톡 면적 가져오기
                        kakao_area = parsed.get(
                            "area_m2") or parsed.get("actual_area_m2")

                        # 면적 비교 및 추천
                        unit_comparison = system._compare_unit_areas(
                            kakao_area, all_units)

                        # 전유부분 목록을 저장하고 선택 UI를 표시하도록 반환
                        return {
                            "units": all_units,
                            "unit_comparison": unit_comparison,
                            "parsed": parsed,
                            "address_info": address_info,
                            "building": building,
                            "floor": floor,
                            "need_unit_selection": True,
                            "unit_count": len(all_units),
                            "debug_info": f"같은 층에 {len(all_units)}개의 전유부분 발견 - 선택 필요",
                        }, None
                else:
                    # 선택된 전유부분 정보 저장
                    if selected_unit_idx == "total":
                        # 통임대: 모든 전유부분
                        total_area = sum(u["area"] for u in all_units)
                        # 용도는 첫 번째 호수의 용도 사용 (또는 통합)
                        main_usage = all_units[0].get("main_usage")
                        selected_units_info = {
                            "type": "total",
                            "area": total_area,
                            "usage": main_usage,
                            "units": all_units,
                        }
                        print(
                            f"\n[통임대 선택] 전체 {
                                len(all_units)}개 호수, 총 면적: {total_area}㎡")
                    else:
                        # 분할임대: 특정 호수
                        selected_unit = all_units[selected_unit_idx]
                        print(f"\n[분할임대 선택]")
                        print(f"  selected_unit_idx: {selected_unit_idx}")
                        print(f"  선택된 호수: {selected_unit.get('ho')}")
                        print(f"  면적: {selected_unit['area']}㎡")
                        print(f"  용도: {selected_unit.get('main_usage')}")
                        selected_units_info = {
                            "type": "single",
                            "area": selected_unit["area"],
                            "usage": selected_unit.get("main_usage"),
                            "ho": selected_unit.get("ho"),
                            "unit": selected_unit,
                        }

        # 용도 판정
        usage_judgment = system._judge_usage(
            building, parsed, floor_result, floor, area_result
        )

        # 점포 용도 선택 필요 여부 확인
        if usage_judgment.get("judged_usage") == "__NEED_USAGE_SELECTION__":
            return {
                "need_usage_selection": True,
                "usage_options": ["제1종 근린생활시설", "제2종 근린생활시설", "근린생활시설"],
                "parsed": parsed,
                "building": building,
                "floor_result": floor_result,
                "area_result": area_result,
                "unit_result": unit_result,
                "floor": floor,
                "address_info": address_info,
                "selected_units_info": selected_units_info,
            }, None

        # 선택된 전유부분의 용도를 반영
        if selected_units_info and selected_units_info.get("usage"):
            # 선택된 전유부분의 용도를 우선 사용
            usage_judgment["selected_unit_usage"] = selected_units_info["usage"]
            # 기존 judged_usage가 없거나 다르면 선택된 용도 사용
            if not usage_judgment.get("judged_usage"):
                usage_judgment["judged_usage"] = selected_units_info["usage"]

        # 선택된 용도 반영 (점포 → 1종/2종/근린생활시설)
        selected_usage = st.session_state.get("selected_usage", None)
        if selected_usage:
            usage_judgment["judged_usage"] = selected_usage
            # 선택된 용도 사용 후 초기화
            if "selected_usage" in st.session_state:
                del st.session_state["selected_usage"]

        # 면적 비교 (unit_result 전달하여 층/호수 검색 강화)
        # 🔥 선택된 전유부분 정보도 함께 전달
        area_comparison = system._compare_areas(
            parsed, building, floor_result, area_result, floor, unit_result, selected_units_info
        )

        # area_comparison이 None이면 빈 딕셔너리로 초기화
        if area_comparison is None:
            area_comparison = {}

        # 선택된 전유부분 정보를 area_comparison에 추가
        if selected_units_info:
            if (
                "registry_area" not in area_comparison
                or area_comparison.get("registry_area") is None
            ):
                area_comparison["registry_area"] = selected_units_info["area"]
            # 선택된 전유부분의 면적을 우선 사용
            area_comparison["selected_unit_area"] = selected_units_info["area"]
            area_comparison["selected_unit_type"] = selected_units_info["type"]

            # 통임대인 경우 여러 호수의 면적 정보도 포함
            if selected_units_info["type"] == "total":
                area_comparison["unit_breakdown"] = [
                    {"ho": u.get("ho"), "area": u["area"], "usage": u.get("main_usage")}
                    for u in selected_units_info["units"]
                ]

        # 블로그 텍스트 생성
        blog_result = system._generate_blog_text(
            parsed,
            building,
            floor_result,
            floor,
            usage_judgment,
            area_comparison,
            area_result,
            None,
        )

        # 반환값 처리
        if isinstance(blog_result, tuple):
            result_lines = blog_result[0]
        else:
            result_lines = blog_result

        # result_lines가 문자열인 경우 리스트로 변환
        if isinstance(result_lines, str):
            result_lines = result_lines.split("\n")
        elif not isinstance(result_lines, (list, tuple)):
            result_lines = [str(result_lines)]

        # 디버깅: 원본 결과 저장 (문제 진단용)
        debug_lines = []
        if not result_lines:
            debug_lines.append("result_lines가 비어있습니다.")
        else:
            debug_lines.append(f"원본 라인 수: {len(result_lines)}")
            debug_lines.append(f"\n전체 라인:")
            for i, line in enumerate(result_lines, 1):
                debug_lines.append(f"  {i}. {repr(str(line))}")
        st.session_state.debug_info = "\n".join(debug_lines)

        # 결과 텍스트 처리 - 모든 라인을 포함하고 특수 마커만 처리
        result_text = ""
        area_options = {}
        pending_area_line = None  # "• 전용면적: " 라인 임시 저장
        area_selection_found = False  # 면적 선택 마커 발견 여부

        for line in result_lines:
            line_str = str(line).strip()

            # 빈 라인은 그대로 추가
            if not line_str:
                result_text += "\n"
                continue

            # 특수 마커 처리
            if line_str == "__AREA_SELECTION__":
                area_selection_found = True
                # 이전에 저장된 "• 전용면적: " 라인 처리
                if pending_area_line:
                    result_text += pending_area_line + "\n"
                    pending_area_line = None
                continue
            elif line_str.startswith("__ACTUAL_AREA__"):
                area_val = (
                    line_str.replace(
                        "__ACTUAL_AREA__",
                        "").replace(
                        "__",
                        "").strip())
                if area_val:
                    try:
                        area_options["actual"] = float(area_val)
                    except BaseException:
                        pass
                continue
            elif line_str.startswith("__KAKAO_AREA__"):
                area_val = (
                    line_str.replace(
                        "__KAKAO_AREA__",
                        "").replace(
                        "__",
                        "").strip())
                if area_val:
                    try:
                        area_options["kakao"] = float(area_val)
                    except BaseException:
                        pass
                continue
            elif line_str.startswith("__REGISTRY_AREA__"):
                area_val = (
                    line_str.replace(
                        "__REGISTRY_AREA__",
                        "").replace(
                        "__",
                        "").strip())
                if area_val:
                    try:
                        area_options["registry"] = float(area_val)
                    except BaseException:
                        pass
                continue
            elif line_str.startswith("__USAGE_") or line_str.startswith("__"):
                # 기타 특수 마커는 건너뛰기
                continue
            elif "전용면적:" in line_str:
                # "• 전용면적: " 또는 " 전용면적: " 라인은 임시 저장 (면적 마커 처리 후 추가)
                if area_selection_found:
                    # 면적 선택 마커가 있으면 임시 저장
                    pending_area_line = (
                        line_str if line_str.startswith("•") else "• " + line_str)
                    continue
                else:
                    # 면적 선택 마커가 없으면 바로 추가 (bullet point 추가)
                    result_text += (line_str if line_str.startswith("•")
                                    else "• " + line_str) + "\n"
                    continue
            else:
                # 일반 텍스트 라인은 bullet point 추가해서 추가
                if line_str.startswith("•"):
                    result_text += line_str + "\n"
                else:
                    result_text += "• " + line_str + "\n"

        # 마지막에 남은 pending_area_line 처리
        if pending_area_line:
            result_text += pending_area_line + "\n"

        # 면적 선택 옵션이 있으면 저장
        st.session_state.area_options = area_options

        # result_text가 비어있으면 원본 결과를 확인
        if not result_text or not result_text.strip():
            # 원본 result_lines에서 특수 마커가 아닌 모든 라인을 포함
            result_text = ""
            for line in result_lines:
                line_str = str(line).strip()
                if (
                    line_str
                    and not line_str.startswith("__")
                    and line_str != "__AREA_SELECTION__"
                ):
                    result_text += "• " + line_str + "\n"

        # 여전히 비어있으면 디버깅 정보 포함 (강제 표시)
        if not result_text or not result_text.strip():
            # 디버깅: 원본 result_lines를 모두 표시
            result_text = ""
            if result_lines:
                for line in result_lines:
                    line_str = str(line).strip()
                    if line_str and not line_str.startswith("__"):
                        # bullet point가 없으면 추가
                        if not line_str.startswith("•"):
                            result_text += "• " + line_str + "\n"
                        else:
                            result_text += line_str + "\n"

            # 여전히 비어있으면 에러 메시지
            if not result_text or not result_text.strip():
                result_text = "⚠️ 결과 텍스트가 생성되지 않았습니다.\n\n"
                result_text += "입력 정보를 확인하고 다시 시도해주세요.\n"
                if result_lines:
                    result_text += f"\n원본 라인 수: {len(result_lines)}\n"

        # 면적 정보 추가
        if area_options and "• 전용면적: \n" in result_text:
            area_parts = []
            if "actual" in area_options:
                pyeong = int(round(area_options["actual"] / 3.3058, 0))
                area_parts.append(f"실면적: {area_options['actual']}㎡({pyeong}평)")
            if "kakao" in area_options:
                pyeong = int(round(area_options["kakao"] / 3.3058, 0))
                area_parts.append(f"전용: {area_options['kakao']}㎡({pyeong}평)")
            if "registry" in area_options:
                pyeong = int(round(area_options["registry"] / 3.3058, 0))
                area_parts.append(
                    f"대장: {
                        area_options['registry']}㎡({pyeong}평)")

            area_text = " / ".join(area_parts) if area_parts else "확인요망"
            result_text = result_text.replace(
                "• 전용면적: \n", f"• 전용면적: {area_text}\n"
            )

        return {
            "text": result_text.strip(),
            "parsed": parsed,
            "area_comparison": area_comparison,
            "building": building,
            "address_info": address_info,
            "usage_judgment": usage_judgment,
            "area_comparison": area_comparison,
            "area_options": area_options,
            "debug_info": st.session_state.get("debug_info", ""),
            "floor_result": floor_result,
            "area_result": area_result,
        }, None

    except Exception as e:
        import traceback

        return None, f"오류 발생: {str(e)}\n\n{traceback.format_exc()}"


def main():
    # ==================== 인증 체크 ====================
    if not check_authentication():
        show_login_page()
        return

    # ==================== 피드백 사이드바 ====================
    show_feedback_sidebar()

    # ==================== 기존 시스템 로직 ====================
    # 시스템 초기화
    init_system()

    # 외부 CSS 파일 불러오기 (style.css에서 레이아웃 수정 가능!)
    try:
        with open('style.css', encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("⚠️ style.css 파일을 찾을 수 없습니다. 기본 스타일을 사용합니다.")
        # 기본 CSS (파일이 없을 때 대비)
        st.markdown(
            """
        <style>
            .block-container {padding-top: 1.5rem; padding-bottom: 0.5rem; max-width: 100%;}
            .stButton button[kind="primary"] {background-color: #1976d2; color: white;}
            .stButton button[kind="secondary"] {background-color: #d32f2f; color: white;}
        </style>
        """,
            unsafe_allow_html=True,
        )

    # 시스템 상태 확인
    if not st.session_state.get("system_ready", False):
        st.error(
            f"⚠️ 시스템 초기화 실패: {
                st.session_state.get(
                    'system_error',
                    '알 수 없는 오류')}")
        return

    # 모드 선택 UI
    st.markdown(
        '<h3 style="margin-top: 0.2rem; margin-bottom: 0.3rem; font-size: 0.95rem;">🔧 작업 모드 선택</h3>',
        unsafe_allow_html=True)
    mode_col1, mode_col2 = st.columns(2)

    with mode_col1:
        if st.button(
            "📋 모드 A: 블로그 광고 생성",
            use_container_width=True,
            type="primary" if st.session_state.get(
                "mode",
                "A") == "A" else "secondary",
        ):
            st.session_state.mode = "A"
            st.rerun()

    with mode_col2:
        if st.button(
            "🔍 모드 B: 필수표시사항 검증",
            use_container_width=True,
            type="primary" if st.session_state.get(
                "mode",
                "A") == "B" else "secondary",
        ):
            st.session_state.mode = "B"
            st.rerun()

    st.markdown("---")

    # 현재 선택된 모드 표시
    current_mode = st.session_state.get("mode", "A")
    mode_name = (
        "📋 모드 A: 블로그 광고 생성" if current_mode == "A" else "🔍 모드 B: 필수표시사항 검증"
    )
    st.markdown(f"### {mode_name}")

    # 모드 B: 필수표시사항 파싱 & 검증
    if current_mode == "B":
        from naver_bank_parser import NaverBankParser

        # 2열 레이아웃
        input_col1, input_col2 = st.columns([1, 1], gap="medium")

        with input_col1:
            st.markdown(
                '<h4 style="color: #1976d2; margin-bottom: 5px; margin-top: 0; padding-top: 0; font-size: 0.85rem;">📋 네이버 부동산뱅크</h4>',
                unsafe_allow_html=True)
            st.caption("매물 등록 페이지 또는 상세보기 페이지에서 Ctrl+A → Ctrl+C")

            # 초기화를 위한 key 변경
            bank_input_key = f"bank_input_{
                st.session_state.get(
                    'bank_input_reset_count', 0)}"

            # 부동산뱅크 텍스트 입력
            bank_text = st.text_area(
                "부동산뱅크 페이지:",
                height=320,
                key=bank_input_key,
                placeholder="필수건물종류\t일반상가\n필수건축물용도\t제1종 근린생활시설\n필수소재지\t대구\t중구\t대봉동\n...",
                label_visibility="collapsed")

        with input_col2:
            st.markdown(
                '<h4 style="color: #2e7d32; margin-bottom: 5px; margin-top: 0; padding-top: 0; font-size: 0.85rem;">💬 카카오톡 매물정보 (중요!)</h4>',
                unsafe_allow_html=True)

            # 카톡 정보 상태 표시 (파싱 완료 시만 표시)
            kakao_parsed_status = st.session_state.get('parsed_kakao_data_b')
            if kakao_parsed_status:
                st.success(
                    f"✅ 파싱 완료: {
                        kakao_parsed_status.get(
                            'address',
                            '주소 없음')}")

            # 카톡 입력란 key
            kakao_bank_input_key = f"kakao_bank_input_{
                st.session_state.get(
                    'bank_input_reset_count', 0)}"

            # 카톡 텍스트 입력
            kakao_text_b = st.text_area(
                "카톡 매물 정보:",
                height=280,
                key=kakao_bank_input_key,
                placeholder="중구 대안동 70-1 4층\n1. 500/35 부가세없음\n2. 관리비 실비정산\n3. 무권리\n4. 제1종근생 사무소 / 24.36m2 / 약 7평\n5. 주차장있음 / 내부화장실1개\n6. 동향\n7. 등기o 위반x\n8. 임대인 010-1234-5678",
                label_visibility="collapsed"
            )

        st.info("💡 **사용방법**: 네이버 뱅크 + 카카오톡 정보 입력 후 '파싱하기' 버튼 클릭")

        col1, col2, col3 = st.columns([0.3, 0.3, 0.4])
        with col1:
            parse_btn = st.button(
                "🔍 파싱하기 (양쪽 입력 후 클릭)",
                type="primary",
                use_container_width=True)
        with col2:
            if st.button("🔄 초기화", use_container_width=True):
                # 세션 상태 초기화
                keys_to_delete = [
                    'parsed_bank_result',
                    'parsed_bank_data',
                    'validation_result',
                    'parsed_kakao_data_b']
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]

                # 입력란 초기화를 위해 카운터 증가
                st.session_state.bank_input_reset_count = (
                    st.session_state.get('bank_input_reset_count', 0) + 1
                )

                st.rerun()
        with col3:
            if st.session_state.get('parsed_bank_result'):
                if st.button("📋 파싱 결과 복사", use_container_width=True):
                    # 🔥 JavaScript를 사용한 복사 (웹 환경에서도 작동)
                    copy_text_b = st.session_state.get('parsed_bank_result', '')
                    import html
                    escaped_text_b = html.escape(copy_text_b).replace('\n', '\\n').replace("'", "\\'")
                    
                    copy_js_b = f"""
                    <script>
                    function copyToClipboardBank() {{
                        const text = '{escaped_text_b}';
                        
                        // Clipboard API 사용 (최신 브라우저)
                        if (navigator.clipboard && window.isSecureContext) {{
                            navigator.clipboard.writeText(text).then(function() {{
                                console.log('복사 성공!');
                            }}).catch(function(err) {{
                                console.error('복사 실패:', err);
                                fallbackCopyBank(text);
                            }});
                        }} else {{
                            fallbackCopyBank(text);
                        }}
                        
                        function fallbackCopyBank(text) {{
                            const textArea = document.createElement('textarea');
                            textArea.value = text;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-999999px';
                            document.body.appendChild(textArea);
                            textArea.focus();
                            textArea.select();
                            try {{
                                document.execCommand('copy');
                                console.log('Fallback 복사 성공!');
                            }} catch (err) {{
                                console.error('Fallback 복사 실패:', err);
                            }}
                            document.body.removeChild(textArea);
                        }}
                    }}
                    
                    // 즉시 실행
                    copyToClipboardBank();
                    </script>
                    """
                    
                    components.html(copy_js_b, height=0)
                    st.toast("✅ 복사 완료!", icon="✅")

        if parse_btn and bank_text:
            from kakao_parser import KakaoPropertyParser
            from bank_info_validator import BankInfoValidator

            # 1. 네이버 뱅크 파싱
            parser = NaverBankParser()
            parsed_bank = parser.parse(bank_text)
            formatted_bank = parser.format_result(parsed_bank)

            # 주소 파싱 실패 시 디버그 정보 추가
            if not parsed_bank.get('address'):
                debug_info = []
                debug_info.append("⚠️ 주소 파싱 실패 - 입력 텍스트 확인:")
                debug_info.append(
                    f"  - '필수소재지' 포함: {'예' if '필수소재지' in bank_text else '아니오'}")
                debug_info.append(
                    f"  - '소재지' 포함: {'예' if '소재지' in bank_text else '아니오'}")
                debug_info.append(
                    f"  - '대구' 포함: {'예' if '대구' in bank_text else '아니오'}")
                debug_info.append(
                    f"  - '필수주소' 포함: {'예' if '필수주소' in bank_text else '아니오'}")

                # 번지 패턴 확인 (전화번호 제외)
                import re
                # 3~4자리 숫자만 (전화번호 010-XXXX 제외)
                bunji_pattern = re.search(
                    r'(\d{3,4})\s*-\s*(\d+)\s*번지', bank_text)
                if bunji_pattern:
                    debug_info.append(
                        f"  - 번지 발견: {bunji_pattern.group(1)}-{bunji_pattern.group(2)}")
                else:
                    # 지번 없는 형식 확인
                    bunji_simple = re.search(r'(\d{3,4})\s*번지', bank_text)
                    if bunji_simple:
                        debug_info.append(
                            f"  - 번지 발견: {bunji_simple.group(1)} (지번 없음)")
                    else:
                        debug_info.append(f"  - 번지 없음 (XXX-XX 또는 XXX 형식)")

                st.session_state['address_parse_debug'] = '\n'.join(debug_info)
            else:
                if 'address_parse_debug' in st.session_state:
                    del st.session_state['address_parse_debug']

            st.session_state['parsed_bank_result'] = formatted_bank
            st.session_state['parsed_bank_data'] = parsed_bank

            # 2. 카톡 파싱 (있으면)
            parsed_kakao = None
            if kakao_text_b and kakao_text_b.strip():
                kakao_parser = KakaoPropertyParser()
                parsed_kakao = kakao_parser.parse(kakao_text_b)
                st.session_state['parsed_kakao_data_b'] = parsed_kakao
            else:
                if 'parsed_kakao_data_b' in st.session_state:
                    del st.session_state['parsed_kakao_data_b']

            # 3. 건축물대장 API 호출 (주소 기반)
            building_data = None
            floor_result = None
            area_result = None
            api_error = None
            api_debug_info = []

            if parsed_bank.get('address'):
                try:
                    from address_code_helper import parse_address

                    system = st.session_state.get('system')
                    api_debug_info.append(
                        f"🔍 System 상태: {
                            '있음' if system else '없음'}")

                    if system and hasattr(system, 'api'):
                        addr = parsed_bank['address']
                        api_debug_info.append(f"📍 파싱된 주소: {addr}")

                        # ✅ 모드 A와 동일하게 parse_address() 사용!
                        address_info = parse_address(addr)

                        if not address_info.get(
                                "sigungu_code") or not address_info.get("bjdong_code"):
                            api_error = f"⚠️ 주소 코드 변환 실패: {addr}"
                            api_debug_info.append(api_error)
                            api_debug_info.append(
                                f"   시군구코드: {
                                    address_info.get(
                                        'sigungu_code',
                                        '없음')}")
                            api_debug_info.append(
                                f"   법정동코드: {
                                    address_info.get(
                                        'bjdong_code',
                                        '없음')}")
                        else:
                            sigungu_cd = address_info['sigungu_code']
                            bjdong_cd = address_info['bjdong_code']
                            bun = address_info['bun']
                            ji = address_info['ji']

                            api_debug_info.append(f"🏘️ 코드 변환 성공:")
                            api_debug_info.append(
                                f"   시군구: {sigungu_cd} ({
                                    address_info.get(
                                        'sigungu_name', '')})")
                            api_debug_info.append(
                                f"   법정동: {bjdong_cd} ({
                                    address_info.get(
                                        'bjdong_name', '')})")
                            api_debug_info.append(f"   번-지: {bun}-{ji}")

                            # 표제부 API 호출 (모드 A와 동일)
                            api_debug_info.append(f"📡 표제부 API 호출 중...")
                            title_result = system.api.get_title_info(
                                sigungu_cd=sigungu_cd,
                                bjdong_cd=bjdong_cd,
                                bun=bun,
                                ji=ji,
                                num_of_rows=10
                            )
                            api_debug_info.append(
                                f"📊 표제부 결과: success={
                                    title_result.get('success')}, 건물 수={
                                    len(
                                        title_result.get(
                                            'data', []))}")

                            # 데이터가 없으면 API 전체 응답 표시
                            if not title_result.get('data'):
                                api_debug_info.append(
                                    f"   ⚠️ 건물을 찾을 수 없습니다. API 응답: {
                                        title_result.get(
                                            'resultMsg', 'N/A')}")

                            if title_result.get(
                                    'success') and title_result.get('data'):
                                building_data = title_result['data'][0]
                                mgm_bldrgst_pk = building_data.get(
                                    'mgmBldrgstPk')
                                api_debug_info.append(
                                    f"🔑 mgmBldrgstPk: {mgm_bldrgst_pk}")

                                # 주차대수 필드 디버깅
                                parking_fields = {
                                    'totPkngCnt': building_data.get(
                                        'totPkngCnt',
                                        'N/A'),
                                    'indrMechUtcnt': building_data.get(
                                        'indrMechUtcnt',
                                        'N/A'),
                                    'indrAutoUtcnt': building_data.get(
                                        'indrAutoUtcnt',
                                        'N/A'),
                                    'oudrMechUtcnt': building_data.get(
                                        'oudrMechUtcnt',
                                        'N/A'),
                                    'oudrAutoUtcnt': building_data.get(
                                        'oudrAutoUtcnt',
                                        'N/A'),
                                }
                                api_debug_info.append(
                                    f"🚗 주차대수 필드: {parking_fields}")
                                api_debug_info.append(
                                    f"📋 표제부 전체 키: {list(building_data.keys())}")

                                # 층별개요 API 호출 (모드 A와 동일하게 모든 파라미터 전달)
                                api_debug_info.append("📡 층별개요 API 호출 중...")
                                floor_result = system.api.get_floor_info(
                                    sigungu_cd=sigungu_cd,
                                    bjdong_cd=bjdong_cd,
                                    bun=bun,
                                    ji=ji,
                                    mgm_bldrgst_pk=mgm_bldrgst_pk
                                )
                                api_debug_info.append(
                                    f"📊 층별개요: 층 수={len(floor_result.get('data', []))}")

                                # 층별 용도 디버깅
                                if floor_result.get('data'):
                                    for floor_info in floor_result.get(
                                            'data', []):
                                        floor_nm = floor_info.get(
                                            'flrNoNm', '?')
                                        floor_usage = floor_info.get(
                                            'mainPurpsCdNm', '?')
                                        floor_etc = floor_info.get(
                                            'etcPurps', '')
                                        api_debug_info.append(
                                            f"   {floor_nm}: {floor_usage} ({floor_etc})" if floor_etc else f"   {floor_nm}: {floor_usage}")

                                # 전유공용면적 API 호출 (모드 A와 동일하게 모든 파라미터 전달)
                                api_debug_info.append("📡 전유공용면적 API 호출 중...")
                                area_result = system.api.get_unit_area_info(
                                    sigungu_cd=sigungu_cd,
                                    bjdong_cd=bjdong_cd,
                                    bun=bun,
                                    ji=ji,
                                    mgm_bldrgst_pk=mgm_bldrgst_pk
                                )
                                api_debug_info.append(
                                    f"📊 전유공용면적: 면적 수={len(area_result.get('data', []))}")

                                # ✅ 모드 A와 동일한 용도 판정 로직 사용
                                api_debug_info.append(
                                    "🔍 모드 A 용도 판정 로직 호출 중...")

                                # parsed_kakao에서 층수 추출
                                # ✅ 층수는 뱅크 기준 (카톡 아님!)
                                floor_num = None
                                if parsed_bank.get('floor'):
                                    # 뱅크 층수를 숫자로 파싱
                                    floor_num = system.parse_floor_string(
                                        parsed_bank.get('floor'))
                                    api_debug_info.append(
                                        f"🔍 [용도 판정] 뱅크 층수: '{
                                            parsed_bank.get('floor')}' → parsed: {floor_num}")

                                # ✅ 뱅크 키를 카톡 키로 변환하여 _judge_usage에 전달
                                parsed_for_usage = {
                                    'ho': parsed_bank.get('ho'),
                                    # 전용면적 (뱅크에서는 exclusive_area)
                                    'area_m2': None,
                                    # 계약면적 (뱅크에서는 contract_area)
                                    'actual_area_m2': None
                                }

                                # 계약면적 추출 (숫자만)
                                if parsed_bank.get('contract_area'):
                                    import re
                                    contract_match = re.search(
                                        r'([0-9.]+)', parsed_bank.get('contract_area'))
                                    if contract_match:
                                        parsed_for_usage['actual_area_m2'] = float(
                                            contract_match.group(1))
                                        api_debug_info.append(
                                            f"🔍 [용도 판정] 계약면적: {
                                                parsed_for_usage['actual_area_m2']}㎡")

                                # 전용면적 추출 (숫자만)
                                if parsed_bank.get('exclusive_area'):
                                    exclusive_match = re.search(
                                        r'([0-9.]+)', parsed_bank.get('exclusive_area'))
                                    if exclusive_match:
                                        parsed_for_usage['area_m2'] = float(
                                            exclusive_match.group(1))

                                # _judge_usage 호출 (✅ 뱅크 기준으로 호출, 키 변환됨)
                                usage_judgment = system._judge_usage(
                                    building=building_data,
                                    parsed=parsed_for_usage,  # ✅ 키 변환된 뱅크 정보
                                    floor_result=floor_result,
                                    floor=floor_num,  # ✅ 뱅크 층수 사용
                                    area_result=area_result
                                )

                                api_debug_info.append(
                                    f"✅ 용도 판정 완료: {
                                        usage_judgment.get(
                                            'judged_usage',
                                            'N/A')}")

                                # ✅ 용도 판정 상세 정보
                                if usage_judgment.get(
                                        'judged_usage') == '__NEED_USAGE_SELECTION__':
                                    api_debug_info.append(
                                        "⚠️ 용도 판정 결과: 사용자 선택 필요 (점포)")
                                elif not usage_judgment.get('judged_usage'):
                                    api_debug_info.append("⚠️ 용도 판정 실패: 결과 없음")

                                # usage_judgment를 세션에 저장
                                st.session_state['usage_judgment_b'] = usage_judgment
                            else:
                                api_error = f"⚠️ 건축물대장 조회 실패: {
                                    title_result.get(
                                        'resultMsg', '알 수 없는 오류')}"
                                api_debug_info.append(api_error)
                    else:
                        api_error = "⚠️ API 시스템 초기화 필요"
                        api_debug_info.append(api_error)
                        api_debug_info.append(
                            f"   system={system}, hasattr(api)={
                                hasattr(
                                    system,
                                    'api') if system else 'N/A'}")
                except Exception as e:
                    api_error = f"⚠️ API 호출 오류: {str(e)}"
                    api_debug_info.append(api_error)
                    import traceback
                    api_debug_info.append(
                        f"   Traceback: {
                            traceback.format_exc()}")
            else:
                api_error = "⚠️ 주소 정보 없음"
                api_debug_info.append(api_error)

            # 디버그 정보 저장
            st.session_state['api_debug_info'] = api_debug_info

            # 4. 자동으로 3-way 비교 검증 수행 (BankInfoValidator 사용)
            if building_data and not api_error:
                # BankInfoValidator를 사용한 3-way 검증
                validator = BankInfoValidator(system)

                # ✅ 모드 A의 usage_judgment 전달
                usage_judgment = st.session_state.get('usage_judgment_b', {})

                validation_result = validator.validate(
                    parsed_bank,
                    building_data,
                    floor_result or {},
                    area_result or {},
                    parsed_kakao,
                    usage_judgment  # ✅ 추가
                )
                st.session_state['validation_result'] = validation_result
            elif api_error:
                # API 오류 시 간단한 뱅크 vs 카톡 비교만 수행
                validation_items = []

                def extract_number(text):
                    """텍스트에서 숫자만 추출"""
                    if not text:
                        return None
                    import re
                    nums = re.findall(r'\d+', str(text))
                    return int(nums[0]) if nums else None

                # 소재지 비교
                bank_addr = parsed_bank.get('address') or ''
                kakao_addr = parsed_kakao.get(
                    'address') if parsed_kakao else ''
                kakao_addr = kakao_addr or ''  # None → ''

                # "대구" 생략 허용 (None 안전 처리)
                bank_addr_normalized = bank_addr.replace(
                    '대구 ', '').strip() if bank_addr else ''
                kakao_addr_normalized = kakao_addr.replace(
                    '대구 ', '').strip() if kakao_addr else ''

                addr_match = bank_addr_normalized and kakao_addr_normalized and (
                    bank_addr_normalized in kakao_addr_normalized or kakao_addr_normalized in bank_addr_normalized)

                validation_items.append({
                    'name': '📍 소재지',
                    'status': 'correct' if addr_match else 'warning' if not kakao_addr else 'error',
                    'parsed_value': bank_addr or '-',
                    'kakao_value': kakao_addr or '(없음)',
                    'message': '✅ 일치' if addr_match else '⚠️ 카톡 필요' if not kakao_addr else '❌ 불일치'
                })

                # 보증금/월세 비교 (숫자만 비교)
                bank_deposit = extract_number(parsed_bank.get('deposit', ''))
                bank_rent = extract_number(parsed_bank.get('rent', ''))
                kakao_deposit = parsed_kakao.get(
                    'deposit', 0) if parsed_kakao else None
                kakao_rent = parsed_kakao.get(
                    'monthly_rent', 0) if parsed_kakao else None

                if kakao_deposit is not None and kakao_rent is not None:
                    price_match = (
                        bank_deposit == kakao_deposit and bank_rent == kakao_rent)
                    validation_items.append({
                        'name': '💰 보증금/월세',
                        'status': 'correct' if price_match else 'error',
                        'parsed_value': f"{bank_deposit}/{bank_rent}",
                        'kakao_value': f"{kakao_deposit}/{kakao_rent}",
                        'message': '✅ 일치' if price_match else '❌ 불일치'
                    })
                else:
                    validation_items.append({
                        'name': '💰 보증금/월세',
                        'status': 'warning',
                        'parsed_value': f"{parsed_bank.get('deposit', '-')}/{parsed_bank.get('rent', '-')}",
                        'kakao_value': '(없음)',
                        'message': '⚠️ 카톡 필요'
                    })

                # 전용면적
                bank_exclusive = parsed_bank.get('exclusive_area', '')
                kakao_exclusive = f"{
                    parsed_kakao.get(
                        'actual_area_m2',
                        '')}㎡" if parsed_kakao else ''

                validation_items.append({
                    'name': '📏 전용면적',
                    'status': 'info',
                    'parsed_value': bank_exclusive or '-',
                    'kakao_value': kakao_exclusive or '(없음)',
                    'message': 'ℹ️ 참고'
                })

                # 층수
                bank_floor = parsed_bank.get('floor', '')
                kakao_floor = f"{
                    parsed_kakao.get(
                        'floor',
                        '')}층" if parsed_kakao else ''

                validation_items.append({
                    'name': '🏢 해당층',
                    'status': 'info',
                    'parsed_value': bank_floor or '-',
                    'kakao_value': kakao_floor or '(없음)',
                    'message': 'ℹ️ 참고'
                })

                # 화장실 수 (숫자만 비교)
                bank_bathroom = extract_number(
                    parsed_bank.get('bathroom_count', ''))
                kakao_bathroom = parsed_kakao.get(
                    'bathroom_count', None) if parsed_kakao else None

                if kakao_bathroom is not None:
                    bathroom_match = (bank_bathroom == int(kakao_bathroom))
                    validation_items.append({
                        'name': '🚽 화장실',
                        'status': 'correct' if bathroom_match else 'error',
                        'parsed_value': f"{bank_bathroom}개",
                        'kakao_value': f"{kakao_bathroom}개",
                        'message': '✅ 일치' if bathroom_match else '❌ 불일치'
                    })
                else:
                    validation_items.append({
                        'name': '🚽 화장실',
                        'status': 'warning',
                        'parsed_value': parsed_bank.get('bathroom_count', '-'),
                        'kakao_value': '(없음)',
                        'message': '⚠️ 카톡 필요'
                    })

                # 방향
                bank_direction = parsed_bank.get(
                    'direction', '').replace('향', '')
                kakao_direction = parsed_kakao.get(
                    'direction', '').replace(
                    '향', '') if parsed_kakao else ''

                if kakao_direction:
                    dir_match = (bank_direction == kakao_direction)
                    validation_items.append({
                        'name': '🧭 방향',
                        'status': 'correct' if dir_match else 'error',
                        'parsed_value': bank_direction or '-',
                        'kakao_value': kakao_direction,
                        'message': '✅ 일치' if dir_match else '❌ 불일치'
                    })
                else:
                    validation_items.append({
                        'name': '🧭 방향',
                        'status': 'warning',
                        'parsed_value': bank_direction or '-',
                        'kakao_value': '(없음)',
                        'message': '⚠️ 카톡 필요'
                    })

                # API 오류 시: 간단 비교 결과 저장
                st.session_state['validation_result'] = {
                    'items': validation_items,
                    'summary': {
                        'correct': sum(
                            1 for item in validation_items if item['status'] == 'correct'),
                        'warning': sum(
                            1 for item in validation_items if item['status'] == 'warning'),
                        'error': sum(
                            1 for item in validation_items if item['status'] == 'error'),
                        'info': sum(
                            1 for item in validation_items if item['status'] == 'info'),
                        'total': len(validation_items)},
                    'api_error': api_error}

            st.rerun()

        # 파싱 결과 표시
        if st.session_state.get('parsed_bank_result'):
            st.markdown("---")

            # 주소 파싱 실패 경고 표시
            if st.session_state.get('address_parse_debug'):
                st.error("❌ 주소 파싱 실패")
                with st.expander("🔍 주소 파싱 디버그 정보 (클릭하여 확인)", expanded=True):
                    st.code(
                        st.session_state['address_parse_debug'],
                        language="text")
                    st.info(
                        "💡 **해결 방법**: 네이버 뱅크 텍스트에 '필수소재지', '대구', '필수주소', 'XXX-XX 번지' 형식이 포함되어 있는지 확인해주세요.")

            # 2열로 파싱 결과 표시
            col_bank, col_kakao = st.columns(2)

            with col_bank:
                st.markdown("#### 🏦 네이버 뱅크 파싱 결과")
                # ✅ 디버그: 파싱된 층 정보 확인
                parsed_bank_data = st.session_state.get('parsed_bank_data')
                if parsed_bank_data:
                    floor_debug = f"\n🔍 **디버그**: 파싱된 층 = '{
                        parsed_bank_data.get(
                            'floor', 'None')}'"
                    st.code(
                        st.session_state['parsed_bank_result'] + floor_debug,
                        language="markdown")
                else:
                    st.code(
                        st.session_state['parsed_bank_result'],
                        language="markdown")

            with col_kakao:
                st.markdown("#### 💬 카톡 파싱 결과")
                kakao_parsed = st.session_state.get('parsed_kakao_data_b')
                if kakao_parsed:
                    # ✅ None 값 처리 함수
                    def format_value(value, unit=''):
                        """None이면 빨간색으로 표시, 아니면 정상 표시"""
                        if value is None or value == '' or value == '-':
                            return ':red[**None**]'
                        return f"{value}{unit}"

                    # ✅ 순서대로 표시 + 번호 붙이기
                    address = kakao_parsed.get('address')
                    address_str = format_value(address) if (
                        address is None or address == '' or address == '-') else address

                    deposit = kakao_parsed.get('deposit')
                    rent = kakao_parsed.get('monthly_rent')
                    deposit_str = format_value(deposit) if (
                        deposit is None or deposit == '' or deposit == '-') else str(deposit)
                    rent_str = format_value(rent) if (
                        rent is None or rent == '' or rent == '-') else str(rent)

                    usage = kakao_parsed.get('usage')
                    usage_str = format_value(usage) if (
                        usage is None or usage == '' or usage == '-') else usage

                    exclusive_area = kakao_parsed.get('area_m2')
                    contract_area = kakao_parsed.get('actual_area_m2')
                    exclusive_area_str = format_value(exclusive_area) if (
                        exclusive_area is None or exclusive_area == '' or exclusive_area == '-') else f"{exclusive_area}㎡"
                    contract_area_str = format_value(contract_area) if (
                        contract_area is None or contract_area == '' or contract_area == '-') else f"{contract_area}㎡"

                    floor_val = kakao_parsed.get('floor')
                    if floor_val is not None:
                        floor_str = f"지하{
                            abs(floor_val)}층" if floor_val < 0 else f"{floor_val}층"
                    else:
                        floor_str = ':red[**None**]'

                    bathroom = kakao_parsed.get('bathroom_count')
                    bathroom_str = format_value(bathroom) if (
                        bathroom is None or bathroom == '' or bathroom == '-') else f"{bathroom}개"

                    direction = kakao_parsed.get('direction')
                    direction_str = format_value(direction) if (
                        direction is None or direction == '' or direction == '-') else direction

                    # 위반건축물 여부
                    violation = kakao_parsed.get('illegal')
                    if violation is True:
                        violation_str = "⚠️ 위반건축물 O"
                    elif violation is False:
                        violation_str = "✅ 해당없음"
                    else:
                        violation_str = ':red[**None**]'

                    # Markdown으로 표시 (streamlit의 colored text 지원)
                    st.markdown(f"""
**1. 주소:** {address_str}

**2. 보증금/월세:** {deposit_str}/{rent_str}

**3. 건축물 용도:** {usage_str}

**4. 계약면적/전용면적:** {contract_area_str} / {exclusive_area_str}

**5. 층수:** {floor_str}

**6. 화장실 수:** {bathroom_str}

**7. 방향:** {direction_str}

**8. 위반건축물:** {violation_str}
""")
                else:
                    st.warning("⚠️ 카톡 정보 미입력")

        elif parse_btn and not bank_text:
            st.warning("⚠️ 부동산뱅크 페이지 텍스트를 입력해주세요")

        # 검증 결과 표시
        if st.session_state.get('validation_result'):
            st.markdown("---")

            validation = st.session_state['validation_result']
            summary = validation['summary']

            # 상단 한줄 요약
            kakao_exists = st.session_state.get(
                'parsed_kakao_data_b') is not None
            if kakao_exists:
                st.success(
                    f"✅ 비교 완료 | 일치: {
                        summary['correct']} | 주의: {
                        summary['warning']} | 불일치: {
                        summary['error']}")
            else:
                st.warning(
                    f"⚠️ 카톡 미입력 | 일치: {
                        summary['correct']} | 주의: {
                        summary['warning']} | 불일치: {
                        summary['error']}")

            # ✅ 디버그: 계약면적/전용면적 대장 정보 확인
            debug_messages = []
            for item in validation['items']:
                if item['name'] in ['계약면적', '전용면적']:
                    if '대장 정보 없음' in item.get('registry_value', '') or \
                       '층 파싱 실패' in item.get('registry_value', ''):
                        message = item.get('message', '')
                        # 디버그 정보 포함 여부 확인
                        if '\n\n디버그:\n' in message:
                            title, debug = message.split('\n\n디버그:\n', 1)
                            debug_messages.append({
                                'name': item['name'],
                                'title': title,
                                'debug': debug
                            })
                        else:
                            debug_messages.append({
                                'name': item['name'],
                                'title': message,
                                'debug': None
                            })

            if debug_messages:
                with st.expander("🔍 대장 정보 디버그 (클릭하여 확인)", expanded=True):
                    for msg in debug_messages:
                        st.warning(f"⚠️ {msg['name']}: {msg['title']}")
                        if msg['debug']:
                            st.code(msg['debug'], language="text")
                    st.info(
                        "💡 **해결 방법**: 네이버 뱅크에서 '해당층' 정보가 제대로 파싱되었는지 확인하고, 건축물대장 API 결과에 해당 층의 면적 데이터가 있는지 확인해주세요.")

            # 상세 결과 - Pandas DataFrame으로 간단하게
            import pandas as pd

            # 데이터 준비 (3-way 비교: 뱅크 vs 건축물대장 vs 카톡)
            table_data = []
            for item in validation['items']:
                status = item['status']

                # 상태 아이콘
                if status == 'correct':
                    status_icon = '✅ 일치'
                elif status == 'warning':
                    status_icon = '⚠️ 주의'
                elif status == 'error':
                    status_icon = '❌ 불일치'
                else:
                    status_icon = 'ℹ️ 참고'

                table_data.append({
                    '항목': item['name'],
                    '🏦 뱅크': item['parsed_value'],
                    '🏢 대장': item.get('registry_value', '-'),
                    '💬 카톡': item.get('kakao_value', '-'),
                    '상태': status_icon
                })

            # DataFrame 생성 및 표시
            df = pd.DataFrame(table_data)

            # 스타일 적용 - 상태에 따라 행 색상 변경
            def highlight_status(row):
                if '❌' in row['상태']:
                    return ['background-color: #ffe6e6'] * len(row)
                elif '⚠️' in row['상태']:
                    return ['background-color: #fff8e6'] * len(row)
                elif '✅' in row['상태']:
                    return ['background-color: #e6f7e6'] * len(row)
                else:
                    return [''] * len(row)

            styled_df = df.style.apply(highlight_status, axis=1)

            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
                height=min(len(table_data) * 40 + 38, 500)
            )

            # 하단 간단 요약
            error_items = [item for item in validation['items']
                           if item['status'] == 'error']
            warning_items = [
                item for item in validation['items'] if item['status'] == 'warning']

            if error_items:
                st.error(
                    f"❌ 불일치: {', '.join([item['name'] for item in error_items])}")
            elif warning_items:
                st.info(
                    f"💡 카톡 필요: {', '.join([item['name'] for item in warning_items])}")

            # 🔍 API 디버그 정보 표시 (맨 아래, 기본 닫힘)
            api_debug_info = st.session_state.get('api_debug_info', [])
            if api_debug_info:
                with st.expander("🔍 건축물대장 API 호출 상세 로그", expanded=False):
                    for info in api_debug_info:
                        st.text(info)

        return

    # ===== 모드 A: 카카오톡 매물 정보 입력 =====

    # 좌우 2열 레이아웃 (균등 분할, 높이 맞춤)
    left_col, right_col = st.columns([1, 1], gap="medium")

    with left_col:
        st.markdown(
            '<h4 style="color: #1976d2; margin-bottom: 5px; margin-top: 0; padding-top: 0; font-size: 0.85rem;">📝 입력: 카카오톡 매물정보</h4>',
            unsafe_allow_html=True)

        placeholder_text = """중구 대안동 70-1 4층
1. 500/35 부가세없음
2. 관리비 실비정산
3. 무권리
4. 제1종근생 사무소 / 24.36m2 / 약 7평
5. 주차장있음 / 내부화장실1개
6. 동향
7. 등기o 위반x
8. 임대인 010-1234-5678"""

        # 초기화를 위한 key 변경
        input_key = f"kakao_input_{
            st.session_state.get(
                'input_reset_count', 0)}"

        kakao_text = st.text_area(
            "카카오톡 매물 정보:",
            height=350,
            key=input_key,
            placeholder=placeholder_text,
            label_visibility="collapsed",
        )

        btn_col1, btn_col2, debug_col = st.columns([0.4, 0.4, 0.2])
        with btn_col1:
            generate_btn = st.button(
                "🔍 생성", type="primary", use_container_width=True
            )
        with btn_col2:
            if st.button("🔄 초기화", use_container_width=True):
                # 사용자 입력 및 결과만 초기화 (시스템 상태는 유지)
                keys_to_delete = [
                    "result_text",
                    "area_options",
                    "selected_area",
                    "selected_building_idx",
                    "need_building_selection",
                    "buildings",
                    "parsed",
                    "address_info",
                    "error_message",
                    "success_message",
                    "api_buildings_raw",
                    "api_buildings_count",
                    "building_count",
                    "current_kakao_text",
                    "api_full_response",
                    "usage_judgment",
                    "parsed_info",
                    "selected_unit_idx",
                    "need_unit_selection",
                    "units",
                    "unit_comparison",
                    "unit_count",
                    "area_comparison",  # 경고 메시지 초기화
                    "floor_result",
                    "area_result",
                    "need_usage_selection",  # 용도 선택 필요 플래그 초기화
                    "usage_options",  # 용도 옵션 초기화
                    "selected_usage",  # 선택된 용도 초기화
                ]
                for key in keys_to_delete:
                    if key in st.session_state:
                        del st.session_state[key]

                # 입력란 초기화를 위해 카운터 증가
                st.session_state.input_reset_count = (
                    st.session_state.get("input_reset_count", 0) + 1
                )

                st.rerun()

        with debug_col:
            show_debug = st.checkbox("🔧 디버그", value=False, key="debug_toggle")

        # 디버그 정보 표시 (생성 버튼 아래)
        if show_debug:
            with st.expander("🔍 디버그 정보", expanded=True):
                debug_info = {
                    "need_building_selection": st.session_state.get(
                        "need_building_selection",
                        False),
                    "selected_building_idx": st.session_state.get("selected_building_idx"),
                    "buildings_count": len(
                        st.session_state.get(
                            "buildings",
                            [])),
                    "api_buildings_count": st.session_state.get(
                        "api_buildings_count",
                        "N/A"),
                    "has_result": bool(
                        st.session_state.get(
                            "result_text",
                            "")),
                    "session_keys": list(
                        st.session_state.keys()),
                }
                st.json(debug_info)

                # area_comparison 디버그 정보
                st.write("**🔍 area_comparison:**")
                if st.session_state.get("area_comparison"):
                    st.json(st.session_state.area_comparison)
                else:
                    st.warning("⚠️ area_comparison 없음")

                # API 응답들
                if st.session_state.get("api_full_response"):
                    with st.expander("🌐 API 전체 응답"):
                        st.json(st.session_state.api_full_response)

                if st.session_state.get("floor_result"):
                    with st.expander("🏢 층별개요 API (원본 데이터)"):
                        floor_data = st.session_state.floor_result
                        if floor_data.get(
                                'success') and floor_data.get('data'):
                            st.write(f"**총 {len(floor_data['data'])}개 층 정보**")
                            for idx, floor_info in enumerate(
                                    floor_data['data']):
                                floor_num = floor_info.get(
                                    'flrNoNm', '') or floor_info.get(
                                    'flrNo', '')
                                main_usage = floor_info.get(
                                    'mainPurpsCdNm', '') or floor_info.get(
                                    'mainPurps', '')
                                etc_usage = floor_info.get('etcPurps', '')
                                area = floor_info.get('area', '')

                                st.markdown(f"""
                                **{idx + 1}. 층: `{floor_num}`**
                                - mainPurpsCdNm: `{main_usage}`
                                - etcPurps: `{etc_usage}`
                                - area: `{area}㎡`
                                """)
                        st.write("**전체 JSON:**")
                        st.json(floor_data)

                if st.session_state.get("area_result"):
                    with st.expander("📐 전유공용면적 API"):
                        st.json(st.session_state.area_result)

                if st.session_state.get("parsed_info"):
                    with st.expander("📝 파싱 정보"):
                        st.json(st.session_state.parsed_info)

                if st.session_state.get("usage_judgment"):
                    with st.expander("🏷️ 용도 판정"):
                        st.json(st.session_state.usage_judgment)

        if generate_btn:
            if not kakao_text or kakao_text.strip() == "":
                st.warning("매물 정보를 입력하세요")
            else:
                # 입력 텍스트를 session_state에 저장 (건축물 선택 시 사용)
                st.session_state.current_kakao_text = kakao_text

                # 생성 버튼을 누르면 이전 선택 상태 및 결과 데이터 초기화
                keys_to_reset = [
                    "selected_building_idx",
                    "need_building_selection",
                    "selected_area",  # 면적 선택 상태도 초기화
                    "selected_unit_idx",  # 전유부분 선택 상태 초기화
                    "need_unit_selection",  # 전유부분 선택 필요 플래그 초기화
                    "units",  # 전유부분 목록 초기화
                    "unit_comparison",  # 전유부분 비교 정보 초기화
                    "unit_count",  # 전유부분 개수 초기화
                    "need_usage_selection",  # 용도 선택 필요 플래그 초기화
                    "usage_options",  # 용도 옵션 초기화
                    "selected_usage",  # 선택된 용도 초기화
                    "result_text",  # 이전 결과 텍스트 초기화
                    "usage_judgment",  # 이전 용도 판정 초기화
                    "parsed_info",  # 이전 파싱 정보 초기화
                    "area_options",  # 이전 면적 옵션 초기화
                    "area_comparison",  # 이전 면적 비교 정보 초기화
                    "floor_result",  # 이전 층별개요 초기화
                    "area_result",  # 이전 전유공용면적 초기화
                ]
                for key in keys_to_reset:
                    if key in st.session_state:
                        del st.session_state[key]

                with st.spinner("조회 중..."):
                    result, error = generate_blog_ad_web(kakao_text)
                    if error:
                        st.error(f"❌ {error}")
                        st.session_state.result_text = ""
                        st.session_state.area_options = {}
                    else:
                        # 건축물 선택이 필요한 경우
                        if result and result.get("need_building_selection"):
                            st.session_state.buildings = result.get(
                                "buildings", [])
                            st.session_state.building_count = result.get(
                                "building_count", 0
                            )
                            st.session_state.parsed = result.get("parsed", {})
                            st.session_state.address_info = result.get(
                                "address_info", {}
                            )
                            st.session_state.need_building_selection = True
                            st.info(
                                f"🔍 건축물 {result.get('building_count', 0)}개 발견!"
                            )
                            st.rerun()
                        # 전유부분 선택이 필요한 경우
                        elif result and result.get("need_unit_selection"):
                            st.session_state.units = result.get("units", [])
                            st.session_state.unit_comparison = result.get(
                                "unit_comparison", {})
                            st.session_state.unit_count = result.get(
                                "unit_count", 0)
                            st.session_state.parsed = result.get("parsed", {})
                            st.session_state.address_info = result.get(
                                "address_info", {})
                            st.session_state.building = result.get(
                                "building", {})
                            st.session_state.floor = result.get("floor", None)
                            st.session_state.need_unit_selection = True
                            st.info(
                                f"🔍 같은 층에 {
                                    result.get(
                                        'unit_count',
                                        0)}개의 전유부분 발견!")
                            st.rerun()
                        # 용도 선택이 필요한 경우 (점포)
                        elif result and result.get("need_usage_selection"):
                            st.session_state.usage_options = result.get(
                                "usage_options", [])
                            st.session_state.parsed = result.get("parsed", {})
                            st.session_state.building = result.get(
                                "building", {})
                            st.session_state.floor_result = result.get(
                                "floor_result", {})
                            st.session_state.area_result = result.get(
                                "area_result", {})
                            st.session_state.unit_result = result.get(
                                "unit_result", {})
                            st.session_state.floor = result.get("floor", None)
                            st.session_state.address_info = result.get(
                                "address_info", {})
                            st.session_state.selected_units_info = result.get(
                                "selected_units_info", None)
                            st.session_state.need_usage_selection = True
                            st.info("🔍 용도가 점포입니다. 1종, 2종, 근린생활시설 중 선택해주세요.")
                            st.rerun()
                        elif result and result.get("text"):
                            st.session_state.result_text = result["text"]
                            st.session_state.area_options = result.get(
                                "area_options", {}
                            )
                            st.session_state.usage_judgment = result.get(
                                "usage_judgment", {}
                            )
                            st.session_state.parsed_info = result.get(
                                "parsed", {})
                            st.session_state.floor_result = result.get(
                                "floor_result")
                            st.session_state.area_result = result.get(
                                "area_result")
                            st.session_state.area_comparison = result.get(
                                "area_comparison"
                            )  # 면적 비교 정보 저장
                            st.session_state.error_message = None
                            st.session_state.success_message = (
                                "✅ 블로그 양식이 생성되었습니다!"
                            )
                            st.rerun()
                        else:
                            st.session_state.error_message = "⚠️ 결과가 생성되었지만 텍스트가 비어있습니다. 입력 정보를 확인해주세요."
                            st.session_state.result_text = ""
                            st.session_state.area_options = {}
                            st.rerun()

    with right_col:
        st.markdown(
            '<h4 style="color: #1976d2; margin-bottom: 5px; margin-top: 0; padding-top: 0; font-size: 0.85rem;">📋 출력: 블로그 양식</h4>',
            unsafe_allow_html=True)

        # 건축물 선택이 필요한 경우
        if st.session_state.get("need_building_selection", False):
            buildings = st.session_state.get("buildings", [])
            building_count = st.session_state.get(
                "building_count", len(buildings))

            st.error(f"⚠️ 이 주소에 **{building_count}개의 건축물**이 있습니다!")
            st.info("👇 아래에서 원하는 건축물을 선택하세요:")
            st.markdown("---")

            for idx, bld in enumerate(buildings):
                bld_name = bld.get("bldNm", "건물명 없음") or "건물명 없음"
                bld_type = str(
                    bld.get("regstrKindCdNm", "")
                    or bld.get("bldrgstKindCdNm", "")
                    or "종류 불명"
                ).strip()
                main_purpose = (
                    bld.get("mainPurpsCdNm", "")
                    or bld.get("mainPurpsCd", "")
                    or "용도 불명"
                )
                etc_purpose = bld.get("etcPurps", "")

                # 표제부/전유부 구분 표시
                regstr_kind = bld.get("regstrKindCdNm", "")
                if regstr_kind == "표제부":
                    purpose_display = f"{main_purpose} (건물 전체 용도)"
                    if etc_purpose:
                        purpose_display += f" / {etc_purpose}"
                elif regstr_kind == "전유부":
                    purpose_display = f"{main_purpose} (전유부 용도)"
                    if etc_purpose:
                        purpose_display += f" / {etc_purpose}"
                else:
                    purpose_display = main_purpose
                    if etc_purpose:
                        purpose_display += f" / {etc_purpose}"

                total_area = bld.get("totArea", "") or "정보 없음"
                use_apr_day = bld.get("useAprDay", "") or "정보 없음"

                # 동 정보 추출
                bld_dong = None
                dong_fields = [
                    "dongNm",
                    "dongNo",
                    "dong",
                    "dongNmNm",
                    "bldDongNm"]
                for field in dong_fields:
                    if field in bld and bld[field]:
                        bld_dong = str(bld[field]).strip()
                        break
                bld_dong_display = bld_dong if bld_dong else "정보 없음"

                # 건축물 정보를 박스로 표시
                st.markdown(
                    f"""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 2px solid #1976d2; margin-bottom: 15px;">
                    <h4 style="color: #1976d2; margin-top: 0;">🏢 건축물 {idx + 1}</h4>
                    <p style="margin: 5px 0;"><strong>동:</strong> {bld_dong_display}</p>
                    <p style="margin: 5px 0;"><strong>종류:</strong> {bld_type}</p>
                    <p style="margin: 5px 0;"><strong>주용도:</strong> {purpose_display}</p>
                    <p style="margin: 5px 0;"><strong>건물명:</strong> {bld_name}</p>
                    <p style="margin: 5px 0;"><strong>연면적:</strong> {total_area}㎡</p>
                    <p style="margin: 5px 0;"><strong>사용승인일:</strong> {use_apr_day}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    f"✅ 건축물 {idx + 1} 선택하기",
                    key=f"select_building_{idx}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.selected_building_idx = idx
                    st.session_state.need_building_selection = False
                    # 다시 생성
                    with st.spinner("선택한 건축물 정보로 생성 중..."):
                        kakao_text = st.session_state.get(
                            "current_kakao_text", "")
                        result, error = generate_blog_ad_web(kakao_text)
                        if error:
                            st.error(f"❌ {error}")
                            st.session_state.result_text = ""
                            st.session_state.area_options = {}
                        else:
                            if result and result.get("text"):
                                st.session_state.result_text = result["text"]
                                st.session_state.area_options = result.get(
                                    "area_options", {}
                                )
                                st.session_state.usage_judgment = result.get(
                                    "usage_judgment", {}
                                )
                                st.session_state.parsed_info = result.get(
                                    "parsed", {})
                                st.session_state.floor_result = result.get(
                                    "floor_result"
                                )
                                st.session_state.area_result = result.get(
                                    "area_result")
                                st.session_state.area_comparison = result.get(
                                    "area_comparison"
                                )  # 면적 비교 정보 저장
                                st.session_state.success_message = (
                                    "✅ 블로그 양식이 생성되었습니다!"
                                )
                    st.rerun()

                st.markdown("")  # 간격

            st.stop()  # 건축물 선택 전까지는 아래 내용 표시 안 함

        # 전유부분 선택이 필요한 경우
        if st.session_state.get("need_unit_selection", False):
            units = st.session_state.get("units", [])
            unit_comparison = st.session_state.get("unit_comparison", {})
            unit_count = st.session_state.get("unit_count", len(units))

            # 입력된 호수 정보 표시
            parsed_info = st.session_state.get("parsed_info", {})
            input_ho = parsed_info.get("ho", "정보 없음")

            st.warning(f"⚠️ 같은 층에 **{unit_count}개의 전유부분**이 있습니다!")
            st.info(f"📝 입력하신 호수: **{input_ho}**")
            st.info("👇 통임대 또는 분할임대를 선택하세요:")

            # 통임대 옵션 (전체)
            if unit_comparison.get("type") == "multiple":
                total_area = unit_comparison.get("total_area", 0)
                is_recommended = unit_comparison.get("recommended") == "total"

                # 통임대 박스
                bg_color = "#e8f5e9" if is_recommended else "#f0f2f6"
                border_color = "#4caf50" if is_recommended else "#1976d2"

                st.markdown(
                    f"""
                <div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; border: 2px solid {border_color}; margin: 10px 0;">
                    <h4 style="color: {border_color}; margin: 0 0 8px 0;">🏢 전체 (통임대): {total_area:.2f}㎡</h4>
                    {'<p style="margin: 5px 0 5px 0; color: #4caf50; font-size: 14px;"><strong>✅ 카톡 면적과 일치합니다</strong></p>' if unit_comparison.get('match_total') else ''}
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # 각 호수 정보 표시
                for idx, unit in enumerate(units):
                    usage_str = unit.get("main_usage", "용도 불명")
                    if unit.get("etc_usage"):
                        usage_str = f"{usage_str} ({unit.get('etc_usage')})"

                    ho_text = unit.get('ho', '정보 없음')

                    st.markdown(
                        f"""
                        <div style="padding-left: 20px; margin-bottom: 5px;">
                            <p style="margin: 3px 0; font-size: 14px;">{ho_text} ├─ {unit['area']:.2f}㎡ - {usage_str}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                if st.button(
                    "✅ 전체 (통임대) 선택",
                    key="select_unit_total",
                    type="primary" if is_recommended else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.selected_unit_idx = "total"
                    st.session_state.need_unit_selection = False
                    # 다시 생성
                    with st.spinner("선택한 전유부분 정보로 생성 중..."):
                        kakao_text = st.session_state.get(
                            "current_kakao_text", "")
                        result, error = generate_blog_ad_web(kakao_text)
                        if error:
                            st.error(f"❌ {error}")
                            st.session_state.result_text = ""
                            st.session_state.area_options = {}
                        else:
                            if result and result.get("text"):
                                st.session_state.result_text = result["text"]
                                st.session_state.area_options = result.get(
                                    "area_options", {}
                                )
                                st.session_state.usage_judgment = result.get(
                                    "usage_judgment", {}
                                )
                                st.session_state.parsed_info = result.get(
                                    "parsed", {})
                                st.session_state.floor_result = result.get(
                                    "floor_result"
                                )
                                st.session_state.area_result = result.get(
                                    "area_result")
                                st.session_state.area_comparison = result.get(
                                    "area_comparison"
                                )  # 면적 비교 정보 저장
                                st.session_state.success_message = (
                                    "✅ 블로그 양식이 생성되었습니다!"
                                )
                    st.rerun()

                st.markdown(
                    '<hr style="margin: 15px 0;">',
                    unsafe_allow_html=True)

                # 개별 호수 옵션
                for idx, unit in enumerate(units):
                    is_unit_recommended = (
                        unit_comparison.get("recommended") == f"unit_{idx}"
                    )
                    bg_color = "#e8f5e9" if is_unit_recommended else "#f0f2f6"
                    border_color = "#4caf50" if is_unit_recommended else "#1976d2"

                    usage_str = unit.get("main_usage", "용도 불명")
                    if unit.get("etc_usage"):
                        usage_str = f"{usage_str} ({unit.get('etc_usage')})"

                    ho_text = unit.get('ho', '정보 없음')

                    st.markdown(
                        f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; border: 2px solid {border_color}; margin-bottom: 8px;">
                        <h4 style="color: {border_color}; margin: 0 0 5px 0; font-size: 16px;">🏠 {ho_text}</h4>
                        <p style="margin: 3px 0; font-size: 14px;">{unit['area']:.2f}㎡ - {usage_str}</p>
                        {'<p style="margin: 5px 0 0 0; color: #4caf50; font-size: 13px;"><strong>✅ 카톡 면적과 일치합니다</strong></p>' if is_unit_recommended else ''}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        f"✅ {ho_text} 선택",
                        key=f"select_unit_{idx}",
                        type="primary" if is_unit_recommended else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state.selected_unit_idx = idx
                        st.session_state.need_unit_selection = False
                        # 다시 생성
                        with st.spinner("선택한 전유부분 정보로 생성 중..."):
                            kakao_text = st.session_state.get(
                                "current_kakao_text", "")
                            result, error = generate_blog_ad_web(kakao_text)
                            if error:
                                st.error(f"❌ {error}")
                                st.session_state.result_text = ""
                                st.session_state.area_options = {}
                            else:
                                if result and result.get("text"):
                                    st.session_state.result_text = result["text"]
                                    st.session_state.area_options = result.get(
                                        "area_options", {}
                                    )
                                    st.session_state.usage_judgment = result.get(
                                        "usage_judgment", {})
                                    st.session_state.parsed_info = result.get(
                                        "parsed", {}
                                    )
                                    st.session_state.floor_result = result.get(
                                        "floor_result"
                                    )
                                    st.session_state.area_result = result.get(
                                        "area_result"
                                    )
                                    st.session_state.success_message = (
                                        "✅ 블로그 양식이 생성되었습니다!"
                                    )
                        st.rerun()

                    st.markdown("")  # 간격

            st.stop()  # 전유부분 선택 전까지는 아래 내용 표시 안 함

        # 용도 선택이 필요한 경우 (점포)
        if st.session_state.get("need_usage_selection", False):
            usage_options = st.session_state.get("usage_options", [])

            st.warning("⚠️ 용도가 **점포**입니다!")
            st.info("👇 1종, 2종, 근린생활시설 중 선택해주세요:")

            # 각 옵션을 버튼으로 표시
            for option in usage_options:
                if st.button(
                    f"✅ {option} 선택",
                    key=f"select_usage_{option}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state.selected_usage = option
                    st.session_state.need_usage_selection = False

                    # 다시 생성 (선택한 용도로)
                    with st.spinner(f"선택한 용도({option})로 생성 중..."):
                        kakao_text = st.session_state.get(
                            "current_kakao_text", "")
                        result, error = generate_blog_ad_web(kakao_text)
                        if error:
                            st.error(f"❌ {error}")
                            st.session_state.result_text = ""
                            st.session_state.area_options = {}
                        else:
                            if result and result.get("text"):
                                st.session_state.result_text = result["text"]
                                st.session_state.area_options = result.get(
                                    "area_options", {})
                                st.session_state.usage_judgment = result.get(
                                    "usage_judgment", {})
                                st.session_state.parsed_info = result.get(
                                    "parsed", {})
                                st.session_state.floor_result = result.get(
                                    "floor_result")
                                st.session_state.area_result = result.get(
                                    "area_result")
                                st.session_state.area_comparison = result.get(
                                    "area_comparison")
                                st.session_state.success_message = "✅ 블로그 양식이 생성되었습니다!"
                    st.rerun()

            st.stop()  # 용도 선택 전까지는 아래 내용 표시 안 함

        # 경고 메시지들 (나중에 표시하기 위해 HTML로 저장)
        usage_judgment = st.session_state.get("usage_judgment", {})
        parsed_info = st.session_state.get("parsed_info", {})
        result_text = st.session_state.get("result_text", "")

        warnings = []
        warning_htmls = []  # 경고 HTML을 저장할 리스트

        if usage_judgment and parsed_info and result_text:
            # 1. 용도 비교 경고
            kakao_usage = parsed_info.get("usage", "")
            judged_usage = usage_judgment.get("judged_usage", "")

            if kakao_usage and judged_usage and kakao_usage != judged_usage:
                # 약어를 정규화해서 비교
                kakao_usage_normalized = (
                    kakao_usage.replace("제1종근생", "제1종 근린생활시설")
                    .replace("제2종근생", "제2종 근린생활시설")
                    .replace("근생", "근린생활시설")
                )

                # 정규화 후에도 다르면 경고
                if kakao_usage_normalized != judged_usage:
                    warnings.append(f"**입력하신 용도**: {kakao_usage}")
                    warnings.append(f"**건축물대장 용도**: {judged_usage}")

            # 2. 층수 비교 경고 (입력 층수가 총 층수보다 큰 경우)
            input_floor = parsed_info.get("floor")
            total_floors = usage_judgment.get("grnd_flr_cnt")

            if input_floor and total_floors:
                try:
                    input_floor_num = int(input_floor)
                    total_floors_num = int(total_floors)

                    if input_floor_num > total_floors_num:
                        warnings.append(f"**입력하신 층수**: {input_floor_num}층")
                        warnings.append(f"**건물 총 층수**: {total_floors_num}층")
                        warnings.append("❗ 입력하신 층수가 건물 총 층수보다 큽니다!")
                except BaseException:
                    pass

            # 3. 위반건축물 경고 (입력란에서 감지된 경우)
            if parsed_info.get("violation_building"):
                warnings.append("🚨 **위반건축물**이 입력되었습니다!")
                warnings.append("⚠️ 해당 건축물은 건축법 위반 가능성이 있습니다!")

        # 경고가 있으면 HTML로 저장 (나중에 표시)
        if warnings:
            warning_html = """
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; border-left: 5px solid #ff9800; margin-bottom: 15px; margin-top: 15px;">
                <h4 style="color: #ff9800; margin: 0 0 10px 0;">⚠️ 용도 불일치 경고</h4>
            """
            for w in warnings:
                warning_html += f'<p style="margin: 5px 0; font-size: 14px;">• {w}</p>'
            warning_html += '<p style="margin: 10px 0 0 0; color: #666; font-size: 13px;">결과값은 건축물대장 기준으로 표시됩니다.</p></div>'
            warning_htmls.append(warning_html)

        # 면적 선택 옵션 (있을 경우)
        area_options = st.session_state.get("area_options", {})
        area_comparison = st.session_state.get("area_comparison")

        # 면적 선택 여부 확인
        selected_area = st.session_state.get("selected_area")

        # 🔥 분할임대/통임대 메시지 (면적 선택 옵션 바로 위에 표시!)
        # 디버깅: area_comparison 상태 확인
        if not area_comparison or not area_comparison.get("mismatch"):
            if (
                area_options
                and area_options.get("kakao")
                and area_options.get("registry")
            ):
                # area_options는 있는데 area_comparison이 없거나 mismatch가 없음
                # 수동으로 생성
                kakao = area_options["kakao"]
                registry = area_options["registry"]
                diff = abs(kakao - registry)
                diff_percent = (diff / registry * 100) if registry > 0 else 0

                if not area_comparison:
                    area_comparison = {}

                area_comparison.update(
                    {
                        "kakao_area": kakao,
                        "registry_area": registry,
                        "diff": diff,
                        "diff_percent": diff_percent,
                        "mismatch": diff > 0.1,
                        "rental_type": (
                            "분할임대"
                            if (kakao < registry and diff_percent >= 10)
                            else "통임대"
                        ),
                    }
                )

        # 입력 오류 검증: 계약면적이 건축물대장 해당 층 면적보다 큰 경우
        if area_comparison and area_comparison.get("input_error_detected"):
            actual_area = area_comparison.get("actual_area_m2", 0)
            registry_area = area_comparison.get("registry_area", 0)
            actual_pyeong = int(round(actual_area / 3.3058, 0))
            registry_pyeong = (
                int(round(registry_area / 3.3058, 0)) if registry_area > 0 else 0
            )

            # 더 직관적인 메시지 (HTML로 저장)
            warning_htmls.append(
                f"""
                <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; border-left: 5px solid #d32f2f; margin-bottom: 15px; margin-top: 15px;">
                    <h4 style="color: #d32f2f; margin: 0 0 10px 0;">🚨 입력 오류 감지!</h4>
                    <p style="margin: 5px 0; font-size: 16px;"><strong>입력한 계약면적이 대장면적보다 큽니다</strong></p>
                    <p style="margin: 10px 0; font-size: 15px;">
                        입력: <strong style="color: #d32f2f;">{actual_area}㎡ ({actual_pyeong}평)</strong>
                        &nbsp;🆚&nbsp;
                        대장: <strong style="color: #1976d2;">{registry_area}㎡ ({registry_pyeong}평)</strong>
                    </p>
                    <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">
                        💡 계약면적과 전용면적을 바꿔 입력하셨거나, 면적이 잘못 입력되었을 수 있습니다.
                    </p>
                </div>
                """
            )

        # 층/호수 찾기 실패 경고 (더 직관적으로)
        if area_comparison and area_comparison.get("not_found"):
            floor_search_info = area_comparison.get("floor_search_info")
            if floor_search_info:
                searched_floor = floor_search_info.get("searched_floor")
                searched_ho = floor_search_info.get("searched_ho")
                same_ho_other_floors = floor_search_info.get(
                    "same_ho_other_floors", [])
                available_floors = floor_search_info.get(
                    "available_floors", [])
                available_hos_by_floor = floor_search_info.get(
                    "available_hos_by_floor", {}
                )

                warning_html = f"""
                <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; border-left: 5px solid #d32f2f; margin-bottom: 15px; margin-top: 15px;">
                    <h4 style="color: #d32f2f; margin: 0 0 10px 0;">⚠️ 층/호수를 찾을 수 없습니다</h4>
                    <p style="margin: 5px 0; font-size: 15px;">
                        <strong>입력값:</strong> {searched_floor}층"""

                if searched_ho:
                    warning_html += f" {searched_ho}"
                warning_html += "</p>"

                # 같은 호수 번호의 다른 층 제안
                if same_ho_other_floors:
                    warning_html += '<p style="margin: 10px 0 5px 0; font-size: 14px; color: #555;"><strong>💡 혹시 이 층을 찾으시나요?</strong></p>'
                    for floor_ho in same_ho_other_floors:
                        warning_html += f'<p style="margin: 2px 0 2px 15px; font-size: 13px;">• {floor_ho}</p>'

                # 사용 가능한 층/호수 목록 표시
                if available_hos_by_floor:
                    warning_html += '<p style="margin: 10px 0 5px 0; font-size: 14px; color: #555;"><strong>📋 건축물대장에 있는 층/호수:</strong></p>'
                    for floor, hos in sorted(
                            available_hos_by_floor.items(), key=lambda x: x[0]):
                        hos_str = ", ".join(hos[:5])
                        if len(hos) > 5:
                            hos_str += f" 외 {len(hos) - 5}개"
                        warning_html += f'<p style="margin: 2px 0 2px 15px; font-size: 13px;">• {floor}: {hos_str}</p>'
                elif available_floors:
                    warning_html += f'<p style="margin: 10px 0 5px 0; font-size: 14px; color: #555;"><strong>📋 건축물대장에 있는 층:</strong> {
                        ", ".join(available_floors)}</p>'

                warning_html += "</div>"
                warning_htmls.append(warning_html)

        # 면적 비교 정보 표시 (더 직관적으로)
        if area_comparison and area_comparison.get("mismatch"):
            rental_type = area_comparison.get("rental_type", "확인필요")
            diff = area_comparison.get("diff", 0)
            diff_percent = area_comparison.get("diff_percent", 0)
            kakao_area_cmp = area_comparison.get("kakao_area", 0)
            registry_area_cmp = area_comparison.get("registry_area", 0)

            # 평수 계산
            kakao_pyeong = int(round(kakao_area_cmp / 3.3058, 0))
            registry_pyeong = int(round(registry_area_cmp / 3.3058, 0))

            if rental_type == "분할임대":
                warning_htmls.append(
                    f"""
                    <div style="background-color: #fff9c4; padding: 15px; border-radius: 8px; border-left: 5px solid #fbc02d; margin-bottom: 15px; margin-top: 15px;">
                        <h4 style="color: #f57f17; margin: 0 0 10px 0;">💭 분할임대로 추정됩니다</h4>
                        <p style="margin: 5px 0; font-size: 16px;">
                            <strong>계약면적:</strong> {registry_area_cmp}㎡ ({registry_pyeong}평) &nbsp;|&nbsp;
                            <strong>전용면적:</strong> {kakao_area_cmp}㎡ ({kakao_pyeong}평)
                        </p>
                        <p style="margin: 5px 0; font-size: 14px; color: #666;">차이: {diff:.1f}㎡ ({diff_percent:.0f}%)</p>
                        <p style="margin: 10px 0 0 0; font-size: 14px; color: #555;">
                            💡 카톡면적이 대장면적보다 작아요. 해당 층의 일부만 임대하는 것으로 보입니다.
                        </p>
                    </div>
                    """
                )
            else:
                warning_htmls.append(
                    f"""
                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; border-left: 5px solid #1976d2; margin-bottom: 15px; margin-top: 15px;">
                        <h4 style="color: #1976d2; margin: 0 0 10px 0;">💭 면적 차이가 있습니다</h4>
                        <p style="margin: 5px 0; font-size: 16px;">
                            <strong>계약면적:</strong> {registry_area_cmp}㎡ ({registry_pyeong}평) &nbsp;|&nbsp;
                            <strong>전용면적:</strong> {kakao_area_cmp}㎡ ({kakao_pyeong}평)
                        </p>
                        <p style="margin: 5px 0; font-size: 14px; color: #666;">차이: {diff:.1f}㎡ ({diff_percent:.0f}%)</p>
                        <p style="margin: 10px 0 0 0; font-size: 14px; color: #555;">
                            💡 통임대인지 분할임대인지 확인이 필요합니다. (측정 오차일 수도 있습니다)
                        </p>
                    </div>
                    """
                )
        elif area_comparison and not area_comparison.get("mismatch"):
            # 면적이 같은 경우
            kakao_area_cmp = area_comparison.get("kakao_area", 0)
            kakao_pyeong = int(round(kakao_area_cmp / 3.3058, 0))
            warning_htmls.append(
                f"""
                <div style="background-color: #e8f5e9; padding: 15px; border-radius: 8px; border-left: 5px solid #4caf50; margin-bottom: 15px; margin-top: 15px;">
                    <h4 style="color: #2e7d32; margin: 0 0 10px 0;">✅ 통임대</h4>
                    <p style="margin: 5px 0; font-size: 16px;">
                        <strong>전용면적:</strong> {kakao_area_cmp}㎡ ({kakao_pyeong}평)
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 14px; color: #555;">
                        카톡면적과 대장면적이 같습니다.
                    </p>
                </div>
                """
            )

        if area_options and not selected_area:
            # 면적이 동일한지 확인
            kakao_area = area_options.get("kakao")
            registry_area = area_options.get("registry")
            areas_are_same = (
                kakao_area and registry_area and abs(
                    kakao_area - registry_area) < 0.01)

            if areas_are_same:
                # 결과 텍스트에 면적 자동 설정
                if "• 전용면적:" in result_text:
                    pyeong = int(round(kakao_area / 3.3058, 0))
                    lines = result_text.split("\n")
                    new_lines = []
                    for line in lines:
                        if line.startswith("• 전용면적:"):
                            new_lines.append(
                                f"• 전용면적: {kakao_area}㎡ ({pyeong}평)")
                        else:
                            new_lines.append(line)
                    st.session_state.result_text = "\n".join(new_lines)
                    result_text = st.session_state.result_text
            else:
                # 면적이 다른 경우 선택 옵션 표시
                st.caption("**전용면적 선택:**")

                # 카톡, 대장 면적을 색상별로 표시
                cols = st.columns(2)

                # 카톡 면적 (파란색) - 클릭 가능한 큰 버튼
                if kakao_area:
                    with cols[0]:
                        pyeong_kakao = int(round(kakao_area / 3.3058, 0))
                        # 박스와 버튼을 하나로 합침
                        if st.button(
                            f"📱 카톡면적\n{kakao_area}㎡ ({pyeong_kakao}평)",
                            key="select_kakao",
                            use_container_width=True,
                            type="primary",
                        ):
                            st.session_state.selected_area = {
                                "area": kakao_area,
                                "source": "kakao",
                            }
                            lines = result_text.split("\n")
                            new_lines = []
                            for line in lines:
                                if line.startswith("• 전용면적:"):
                                    new_lines.append(
                                        f"• 전용면적: {kakao_area}㎡ ({pyeong_kakao}평)")
                                else:
                                    new_lines.append(line)
                            st.session_state.result_text = "\n".join(new_lines)
                            st.rerun()

                # 대장 면적 (빨간색) - 클릭 가능한 큰 버튼
                if registry_area:
                    with cols[1]:
                        pyeong_registry = int(round(registry_area / 3.3058, 0))
                        # 박스와 버튼을 하나로 합침
                        if st.button(
                            f"📋 대장면적\n{registry_area}㎡ ({pyeong_registry}평)",
                            key="select_registry",
                            use_container_width=True,
                            type="secondary",
                        ):
                            st.session_state.selected_area = {
                                "area": registry_area,
                                "source": "registry",
                            }
                            lines = result_text.split("\n")
                            new_lines = []
                            for line in lines:
                                if line.startswith("• 전용면적:"):
                                    new_lines.append(
                                        f"• 전용면적: {registry_area}㎡ ({pyeong_registry}평)")
                                else:
                                    new_lines.append(line)
                            st.session_state.result_text = "\n".join(new_lines)
                            st.rerun()
        elif selected_area:
            # 면적이 선택된 경우, 선택된 면적만 표시 (컴팩트하게)
            selected_value = selected_area["area"]
            selected_source = selected_area["source"]
            pyeong_selected = int(round(selected_value / 3.3058, 0))

            if selected_source == "kakao":
                st.markdown(
                    f'<div style="background-color: #2196F3; color: white; padding: 6px 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 14px;">'
                    f"✅ 📱 카톡면적 {selected_value}㎡ ({pyeong_selected}평)</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div style="background-color: #f44336; color: white; padding: 6px 10px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 14px;">'
                    f"✅ 📋 대장면적 {selected_value}㎡ ({pyeong_selected}평)</div>",
                    unsafe_allow_html=True,
                )

        # 결과 텍스트 처리
        display_text = result_text if result_text else ""
        display_text_html = display_text  # HTML 버전 (화면 표시용)
        copy_text = display_text  # 일반 텍스트 (복사용)

        if result_text:
            lines = display_text.split("\n")
            new_lines = []

            # 입력란에서 위반건축물이 감지된 경우
            violation_from_input = (
                parsed_info.get(
                    "violation_building",
                    False) if parsed_info else False)

            for line in lines:
                modified_line = line

                # 1. 층수 초과 확인하여 "해당 층"을 "확인요망"으로 변경
                if usage_judgment and parsed_info:
                    input_floor = parsed_info.get("floor")
                    total_floors = usage_judgment.get("grnd_flr_cnt")

                    if (
                        input_floor
                        and total_floors
                        and ("해당 층:" in line or "해당층:" in line)
                    ):
                        try:
                            input_floor_num = int(input_floor)
                            total_floors_num = int(total_floors)

                            if input_floor_num > total_floors_num:
                                modified_line = "• 해당 층: 확인요망"
                        except BaseException:
                            pass

                # 2. 위반건축물 감지된 경우 "건축물대장상 위반 건축물" 항목 변경
                if violation_from_input and (
                    "건축물대장상 위반 건축물" in line
                    or "건축물대장상 위반건축물" in line
                ):
                    modified_line = "• 건축물대장상 위반 건축물: 위반건축물(해당)"

                new_lines.append(modified_line)

            display_text = "\n".join(new_lines)
            copy_text = display_text

            # 특정 키워드를 빨간색 굵은 글씨로 변경 (HTML 버전)
            import re
            keywords_to_highlight = [
                "확인요망",
                "위반건축물",
                "불법건축물",
                "위반있음",
                "위반건축물(해당)",
            ]
            display_text_html = display_text

            # 기본 키워드 강조
            for keyword in keywords_to_highlight:
                display_text_html = display_text_html.replace(
                    keyword, f"<span style='color: red; font-weight: bold;'>{keyword}</span>", )

            # "(확인요망)" 패턴이 포함된 텍스트 강조 (예: "대중음식점(확인요망)")
            # 용도: 뒤에 나오는 텍스트를 찾아서 강조
            pattern = r'(용도:\s*)([^\n]+\(확인요망\))'

            def replace_usage(match):
                prefix = match.group(1)  # "용도: "
                usage_text = match.group(2)  # "대중음식점(확인요망)"
                return f"{prefix}<span style='color: red; font-weight: bold;'>{usage_text}</span>"
            display_text_html = re.sub(
                pattern, replace_usage, display_text_html)

        # 🎯 경고 메시지들을 결과 위에 표시
        for warning_html in warning_htmls:
            st.markdown(warning_html, unsafe_allow_html=True)

        # 결과 텍스트 표시
        if not result_text:
            st.info("👈 왼쪽에서 매물 정보를 입력하고 '생성' 버튼을 클릭하세요")
        else:
            # 초록색 복사 버튼 스타일
            st.markdown(
                """
                <style>
                .green-copy-button button {
                    background-color: #4caf50 !important;
                    border-color: #4caf50 !important;
                    color: white !important;
                    padding: 0.2rem 0.5rem !important;
                    font-size: 0.8rem !important;
                }
                .green-copy-button button:hover {
                    background-color: #45a049 !important;
                    border-color: #45a049 !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # 텍스트 영역
            st.markdown(
                f"""
                <div style="background-color: #f0f2f6; padding: 12px; border-radius: 8px; border: 1px solid #ddd; height: 350px; overflow-y: auto; white-space: pre-wrap; font-family: monospace; font-size: 13px;">
{display_text_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 결과 요약 정보와 복사 버튼을 한 줄에
            summary_col, copy_btn_col = st.columns([0.5, 0.5])

            with summary_col:
                st.caption(f"✅ 생성 완료 ({len(result_text)}자)")

            with copy_btn_col:
                st.markdown(
                    '<div class="green-copy-button">',
                    unsafe_allow_html=True)
                copy_clicked = st.button(
                    "📋 결과 복사하기", key="copy_button", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                if copy_clicked:
                    # 복사할 텍스트에서 소재지의 번지수 제거
                    def remove_address_numbers(text):
                        """소재지 라인에서 번지수를 제거하는 함수"""
                        lines = text.split('\n')
                        processed_lines = []

                        for line in lines:
                            # 소재지 라인 찾기
                            if '소재지:' in line or '소재지 :' in line:
                                # 소재지: 뒤의 내용 추출
                                if '소재지:' in line:
                                    prefix = line.split('소재지:')[0] + '소재지:'
                                    address = line.split('소재지:')[1].strip()
                                else:
                                    prefix = line.split('소재지 :')[0] + '소재지 :'
                                    address = line.split('소재지 :')[1].strip()

                                # 번지수 패턴 제거 (예: 123-45, 123번지, 123, 산123-45 등)
                                # 마지막 공백 이후의 숫자 패턴 제거
                                import re
                                # 패턴: 숫자-숫자, 숫자번지, 산숫자-숫자, 단순 숫자 등
                                address_cleaned = re.sub(
                                    r'\s+(산\s*)?\d+(-\d+)?(번지)?$', '', address)

                                # 재조립
                                processed_lines.append(
                                    f"{prefix} {address_cleaned}")
                            else:
                                processed_lines.append(line)

                        return '\n'.join(processed_lines)

                    # 번지수 제거된 텍스트
                    copy_text_cleaned = remove_address_numbers(copy_text)

                    # 🔥 JavaScript를 사용한 복사 (웹 환경에서도 작동)
                    import html
                    escaped_text = html.escape(copy_text_cleaned).replace('\n', '\\n').replace("'", "\\'")
                    
                    copy_js = f"""
                    <script>
                    function copyToClipboard() {{
                        const text = '{escaped_text}';
                        
                        // Clipboard API 사용 (최신 브라우저)
                        if (navigator.clipboard && window.isSecureContext) {{
                            navigator.clipboard.writeText(text).then(function() {{
                                console.log('복사 성공!');
                            }}).catch(function(err) {{
                                console.error('복사 실패:', err);
                                fallbackCopy(text);
                            }});
                        }} else {{
                            fallbackCopy(text);
                        }}
                        
                        function fallbackCopy(text) {{
                            // 구형 브라우저 대체 방법
                            const textArea = document.createElement('textarea');
                            textArea.value = text;
                            textArea.style.position = 'fixed';
                            textArea.style.left = '-999999px';
                            document.body.appendChild(textArea);
                            textArea.focus();
                            textArea.select();
                            try {{
                                document.execCommand('copy');
                                console.log('Fallback 복사 성공!');
                            }} catch (err) {{
                                console.error('Fallback 복사 실패:', err);
                            }}
                            document.body.removeChild(textArea);
                        }}
                    }}
                    
                    // 즉시 실행
                    copyToClipboard();
                    </script>
                    """
                    
                    components.html(copy_js, height=0)
                    st.success("✅ 복사 완료! (번지수 제외)")


if __name__ == "__main__":
    main()
