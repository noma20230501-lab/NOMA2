"""
네이버 부동산 크롤링 모듈
네이버 부동산 URL에서 매물 정보를 추출합니다.
Selenium을 사용하여 JavaScript로 렌더링되는 동적 콘텐츠를 처리합니다.
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import Dict, Optional, List
import time
import random
import json
import os

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    UNDETECTED_CHROMEDRIVER_AVAILABLE = True
    SELENIUM_AVAILABLE = True  # undetected_chromedriver도 selenium을 사용하므로
except ImportError:
    UNDETECTED_CHROMEDRIVER_AVAILABLE = False
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        SELENIUM_AVAILABLE = True
    except ImportError:
        SELENIUM_AVAILABLE = False


class NaverPropertyCrawler:
    """네이버 부동산 크롤러"""

    ACCOUNTS_FILE = "neonet_accounts.json"

    @staticmethod
    def load_accounts() -> List[Dict]:
        """계정 정보 로드"""
        try:
            if os.path.exists(NaverPropertyCrawler.ACCOUNTS_FILE):
                with open(NaverPropertyCrawler.ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('accounts', [])
        except Exception as e:
            print(f"계정 정보 로드 오류: {e}")
        return []

    @staticmethod
    def save_accounts(accounts: List[Dict]):
        """계정 정보 저장"""
        try:
            data = {'accounts': accounts}
            with open(NaverPropertyCrawler.ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"계정 정보 저장 오류: {e}")

    @staticmethod
    def get_default_account() -> Optional[Dict]:
        """기본 계정 가져오기"""
        accounts = NaverPropertyCrawler.load_accounts()
        for account in accounts:
            if account.get('is_default', False):
                return account
        # 기본 계정이 없으면 첫 번째 계정 반환
        if accounts:
            return accounts[0]
        return None

    @staticmethod
    def get_account_by_id(account_id: str) -> Optional[Dict]:
        """계정 ID로 계정 정보 가져오기"""
        accounts = NaverPropertyCrawler.load_accounts()
        for account in accounts:
            if account.get('id') == account_id:
                return account
        return None

    def __init__(
            self,
            use_selenium=True,
            neonet_id=None,
            neonet_pw=None,
            account_id=None):
        """
        Args:
            use_selenium: Selenium 사용 여부 (기본값: True)
            neonet_id: 부동산뱅크(neonet) 로그인 아이디 (선택사항)
            neonet_pw: 부동산뱅크(neonet) 로그인 비밀번호 (선택사항)
            account_id: 사용할 계정 ID (선택사항, 없으면 기본 계정 사용)
        """
        self.use_undetected = UNDETECTED_CHROMEDRIVER_AVAILABLE
        self.use_selenium = use_selenium and (
            UNDETECTED_CHROMEDRIVER_AVAILABLE or SELENIUM_AVAILABLE)

        # 계정 정보 설정
        if account_id:
            account = self.get_account_by_id(account_id)
            if account:
                self.neonet_id = account.get('login_id')
                self.neonet_pw = account.get('password')
            else:
                self.neonet_id = neonet_id
                self.neonet_pw = neonet_pw
        elif neonet_id and neonet_pw:
            self.neonet_id = neonet_id
            self.neonet_pw = neonet_pw
        else:
            # 기본 계정 사용
            default_account = self.get_default_account()
            if default_account:
                self.neonet_id = default_account.get('login_id')
                self.neonet_pw = default_account.get('password')
            else:
                self.neonet_id = None
                self.neonet_pw = None

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def extract_article_id(self, url: str) -> Optional[str]:
        """URL에서 article ID 추출"""
        # 네이버 부동산 URL 형식:
        # https://land.naver.com/article/detail/12345678
        # https://m.land.naver.com/article/detail/12345678
        # https://new.land.naver.com/article/detail/12345678
        # https://new.land.naver.com/offices?ms=...&articleNo=12345678
        match = re.search(r'/article/detail/(\d+)', url)
        if match:
            return match.group(1)

        # 새 URL 형식에서 articleNo 추출
        match = re.search(r'articleNo[=:](\d+)', url)
        if match:
            return match.group(1)

        # articleNc 형식도 시도
        match = re.search(r'articleNc[=:](\d+)', url)
        if match:
            return match.group(1)

        return None

    def crawl_property_info(self, url: str) -> Dict:
        """
        네이버 부동산 또는 부동산뱅크 URL에서 매물 정보 크롤링

        Args:
            url: 네이버 부동산 매물 URL 또는 부동산뱅크 URL

        Returns:
            매물 정보 딕셔너리
        """
        result = {
            'success': False,
            'url': url,
            'address': None,
            'deposit': None,
            'monthly_rent': None,
            'area_m2': None,
            'area_pyeong': None,
            'floor': None,
            'total_floors': None,
            'usage': None,
            'bathroom_count': None,
            'parking': None,
            'direction': None,
            'approval_date': None,
            'raw_html': None,
            'error': None
        }

        try:
            # URL 유효성 검사 (네이버 부동산 또는 부동산뱅크)
            if not url:
                result['error'] = 'URL이 입력되지 않았습니다.'
                return result

            # 부동산뱅크 URL인지 확인 (neonet.co.kr 도메인 포함)
            is_realestate_bank = 'realestatebank.co.kr' in url or 'reb.or.kr' in url or 'neonet.co.kr' in url or '부동산뱅크' in url

            # 네이버 부동산 URL인지 확인
            is_naver_land = 'land.naver.com' in url

            if not is_naver_land and not is_realestate_bank:
                result['error'] = '유효하지 않은 URL입니다. 네이버 부동산 또는 부동산뱅크 URL을 입력해주세요.'
                return result

            # 부동산뱅크인 경우 별도 처리 (자동 로그인 사용)
            if is_realestate_bank:
                return self._crawl_realestate_bank(
                    url, result, auto_login=True)

            # 네이버 부동산 크롤링
            # undetected_chromedriver 우선 사용, 없으면 일반 selenium 사용
            if self.use_selenium:
                if self.use_undetected:
                    result = self._crawl_with_undetected_chromedriver(
                        url, result)
                else:
                    result = self._crawl_with_selenium(url, result)
            else:
                # 기본 requests 방법 시도
                result = self._crawl_with_requests(url, result)

        except Exception as e:
            result['error'] = f'크롤링 오류: {str(e)}'
            result['success'] = False

        return result

    def _login_neonet(
            self,
            driver,
            login_id: str = None,
            login_pw: str = None,
            result: Dict = None) -> bool:
        """
        부동산뱅크(neonet) 자동 로그인

        Args:
            driver: Selenium WebDriver
            login_id: 로그인 아이디 (없으면 self.neonet_id 사용)
            login_pw: 로그인 비밀번호 (없으면 self.neonet_pw 사용)
            result: 결과 딕셔너리 (오류 메시지 저장용)

        Returns:
            로그인 성공 여부
        """
        if result is None:
            result = {}

        try:
            login_id = login_id or self.neonet_id
            login_pw = login_pw or self.neonet_pw

            if not login_id or not login_pw:
                result['error'] = '로그인 정보가 제공되지 않았습니다.'
                return False

            # 로그인 페이지로 이동
            login_url = "https://www.neonet.co.kr/novo-rebank/view/member/MemberLogin.neo?login_check=yes&return_url=/novo-rebank/index.neo"
            driver.get(login_url)
            time.sleep(3)

            # 아이디 입력
            try:
                id_input = WebDriverWait(
                    driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#input_id")))
                id_input.clear()
                id_input.send_keys(login_id)
                time.sleep(1)
            except Exception as e:
                result['error'] = f'아이디 입력 필드를 찾을 수 없습니다: {str(e)}'
                return False

            # 비밀번호 입력
            try:
                pw_input = driver.find_element(By.CSS_SELECTOR, "#input_pw")
                pw_input.clear()
                pw_input.send_keys(login_pw)
                time.sleep(1)
            except Exception as e:
                result['error'] = f'비밀번호 입력 필드를 찾을 수 없습니다: {str(e)}'
                return False

            # 로그인 버튼 클릭
            try:
                login_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "body > div.body_detail > div.subDetail > div.member_login > dl > dt > form > table:nth-child(4) > tbody > tr:nth-child(1) > td:nth-child(2) > input[type=image]")
                login_button.click()
                time.sleep(5)  # 로그인 처리 대기
            except Exception as e:
                # 다른 선택자로 시도
                try:
                    login_button = driver.find_element(
                        By.CSS_SELECTOR, "input[type=image]")
                    login_button.click()
                    time.sleep(5)
                except BaseException:
                    result['error'] = f'로그인 버튼을 찾을 수 없습니다: {str(e)}'
                    return False

            # 로그인 성공 확인 (로그인 페이지가 아닌 경우 성공으로 간주)
            time.sleep(2)
            current_url = driver.current_url
            if 'login' not in current_url.lower() and 'MemberLogin' not in current_url:
                return True

            # 중개업소관리자 클릭 (로그인 후 메뉴)
            try:
                admin_link = WebDriverWait(
                    driver,
                    10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR,
                         "body > div.Neonet_header > div.nthTop > div.t_right > div > a:nth-child(1)")))
                admin_link.click()
                time.sleep(3)
            except BaseException:
                # 이미 로그인되어 있을 수 있음
                pass

            return True

        except Exception as e:
            result['error'] = f'로그인 중 오류 발생: {str(e)}'
            return False

    def _navigate_to_property_list(self, driver, result: Dict = None) -> bool:
        """
        매물관리 페이지로 이동

        Args:
            driver: Selenium WebDriver
            result: 결과 딕셔너리 (오류 메시지 저장용)

        Returns:
            이동 성공 여부
        """
        if result is None:
            result = {}

        try:
            # 매물관리 클릭
            property_link = WebDriverWait(
                driver,
                10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR,
                     "body > div.Neo_header > div.div_header > div:nth-child(1) > div > ul > li:nth-child(2) > a")))
            property_link.click()
            time.sleep(3)
            return True
        except Exception as e:
            result['error'] = f'매물관리 페이지로 이동 실패: {str(e)}'
            return False

    def _find_and_click_property(
            self,
            driver,
            property_number: str,
            result: Dict = None) -> bool:
        """
        매물번호로 매물 찾기 및 클릭

        Args:
            driver: Selenium WebDriver
            property_number: 매물번호
            result: 결과 딕셔너리 (오류 메시지 저장용)

        Returns:
            찾기 및 클릭 성공 여부
        """
        if result is None:
            result = {}

        try:
            # 매물 목록 테이블 찾기
            table = WebDriverWait(
                driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#printArea > table > tbody")))

            # 모든 행 찾기
            rows = table.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                try:
                    # 매물번호가 있는 셀 찾기 (2번째 td)
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        property_link = cells[1].find_element(By.TAG_NAME, "a")
                        link_text = property_link.text.strip()

                        # 매물번호와 일치하는지 확인
                        if property_number in link_text or link_text == property_number:
                            # 매물 클릭
                            property_link.click()
                            time.sleep(3)
                            return True
                except BaseException:
                    continue

            result['error'] = f'매물번호 {property_number}를 찾을 수 없습니다.'
            return False

        except Exception as e:
            result['error'] = f'매물 찾기 중 오류 발생: {str(e)}'
            return False

    def crawl_neonet_property(
            self,
            property_number: str,
            login_id: str = None,
            login_pw: str = None) -> Dict:
        """
        부동산뱅크(neonet)에서 매물번호로 매물 정보 크롤링

        Args:
            property_number: 매물번호
            login_id: 로그인 아이디 (없으면 self.neonet_id 사용)
            login_pw: 로그인 비밀번호 (없으면 self.neonet_pw 사용)

        Returns:
            매물 정보 딕셔너리
        """
        result = {
            'success': False,
            'property_number': property_number,
            'address': None,
            'deposit': None,
            'monthly_rent': None,
            'area_m2': None,
            'area_pyeong': None,
            'floor': None,
            'total_floors': None,
            'usage': None,
            'bathroom_count': None,
            'parking': None,
            'direction': None,
            'approval_date': None,
            'raw_html': None,
            'error': None
        }

        driver = None
        try:
            if not self.use_selenium:
                result['error'] = '부동산뱅크 크롤링은 Selenium이 필요합니다.'
                return result

            login_id = login_id or self.neonet_id
            login_pw = login_pw or self.neonet_pw

            if not login_id or not login_pw:
                result['error'] = '로그인 정보가 제공되지 않았습니다.'
                return result

            # 드라이버 초기화
            if self.use_undetected:
                options = uc.ChromeOptions()
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--window-size=1920,1080')
                options.add_argument(
                    '--disable-blink-features=AutomationControlled')
                driver = uc.Chrome(options=options, version_main=None)
            else:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                from webdriver_manager.chrome import ChromeDriverManager

                chrome_options = Options()
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument(
                    '--disable-blink-features=AutomationControlled')

                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(
                    service=service, options=chrome_options)

            driver.set_page_load_timeout(30)

            # 1. 로그인
            if not self._login_neonet(driver, login_id, login_pw, result):
                return result

            # 2. 매물관리 페이지로 이동
            if not self._navigate_to_property_list(driver, result):
                return result

            # 3. 매물번호로 매물 찾기 및 클릭
            if not self._find_and_click_property(
                    driver, property_number, result):
                return result

            # 4. 매물 상세 페이지에서 정보 추출
            time.sleep(3)
            page_source = driver.page_source
            result['raw_html'] = page_source

            soup = BeautifulSoup(page_source, 'html.parser')
            self._extract_realestate_bank_info(soup, driver, result)

            # 정보가 추출되었는지 확인
            has_info = any([
                result.get('address'),
                result.get('deposit'),
                result.get('monthly_rent'),
                result.get('area_m2'),
                result.get('area_pyeong'),
                result.get('floor')
            ])

            if has_info:
                result['success'] = True
            else:
                result['error'] = '매물 정보를 추출할 수 없습니다.'
                result['success'] = False

        except Exception as e:
            result['error'] = f'크롤링 오류: {str(e)}'
            result['success'] = False
            import traceback
            result['debug_traceback'] = traceback.format_exc()
        finally:
            if driver:
                try:
                    driver.quit()
                except BaseException:
                    pass

        return result

    def _crawl_realestate_bank(
            self,
            url: str,
            result: Dict,
            login_wait_time: int = 60,
            auto_login: bool = True) -> Dict:
        """
        부동산뱅크 사이트 크롤링 (네이버 부동산보다 보안이 덜 엄격)

        Args:
            url: 부동산뱅크 URL
            result: 결과 딕셔너리
            login_wait_time: 로그인 대기 시간 (초, 기본값: 60초)
            auto_login: 자동 로그인 사용 여부 (기본값: True)
        """
        driver = None
        try:
            # 부동산뱅크는 보안이 덜 엄격하므로 일반 selenium으로도 가능
            # 하지만 안정성을 위해 undetected_chromedriver 우선 사용
            if self.use_selenium:
                if self.use_undetected:
                    # undetected_chromedriver 사용 (간단한 옵션)
                    options = uc.ChromeOptions()
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument('--window-size=1920,1080')
                    options.add_argument(
                        '--disable-blink-features=AutomationControlled')
                    # 헤드리스 모드 비활성화 (로그인을 위해 브라우저 창이 보여야 함)

                    driver = uc.Chrome(options=options, version_main=None)
                else:
                    # 일반 selenium 사용
                    from selenium import webdriver
                    from selenium.webdriver.chrome.service import Service
                    from selenium.webdriver.chrome.options import Options
                    from webdriver_manager.chrome import ChromeDriverManager

                    chrome_options = Options()
                    chrome_options.add_argument('--no-sandbox')
                    chrome_options.add_argument('--disable-dev-shm-usage')
                    chrome_options.add_argument('--window-size=1920,1080')
                    chrome_options.add_argument(
                        '--disable-blink-features=AutomationControlled')
                    # 헤드리스 모드 비활성화 (로그인을 위해 브라우저 창이 보여야 함)

                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(
                        service=service, options=chrome_options)

                # 자동 로그인 시도
                if auto_login and self.neonet_id and self.neonet_pw:
                    # 자동 로그인 시도
                    login_success = self._login_neonet(
                        driver, self.neonet_id, self.neonet_pw, result)
                    if not login_success:
                        # 자동 로그인 실패 시 수동 로그인 대기
                        result['login_required'] = True
                        result[
                            'login_message'] = f'자동 로그인에 실패했습니다. 브라우저 창에서 로그인을 완료해주세요. (최대 {login_wait_time}초 대기)'

                        wait_start = time.time()
                        logged_in = False

                        while time.time() - wait_start < login_wait_time:
                            time.sleep(2)
                            current_url = driver.current_url
                            page_source = driver.page_source

                            if 'login' not in current_url.lower() and not any(
                                keyword in page_source.lower() for keyword in ['로그인', 'login', '아이디', 'password']
                            ):
                                logged_in = True
                                break

                        if not logged_in:
                            result['error'] = f'로그인 대기 시간({login_wait_time}초)이 초과되었습니다.'
                            result['success'] = False
                            return result
                else:
                    # 수동 로그인 대기 (기존 방식)
                    login_url = "https://www.neonet.co.kr/novo-rebank/view/member/MemberLogin.neo?login_check=yes&return_url=/novo-rebank/index.neo"
                    driver.set_page_load_timeout(30)
                    driver.get(login_url)
                    time.sleep(3)

                    current_url = driver.current_url
                    page_source = driver.page_source

                    login_required = False
                    login_keywords = [
                        '로그인', 'login', '아이디', '비밀번호', 'password']
                    if any(keyword in page_source.lower(
                    ) or keyword in driver.title.lower() for keyword in login_keywords):
                        login_required = True
                        result['login_required'] = True
                        result[
                            'login_message'] = f'부동산뱅크 로그인이 필요합니다. 브라우저 창에서 로그인을 완료해주세요. (최대 {login_wait_time}초 대기)'

                    if login_required:
                        wait_start = time.time()
                        logged_in = False

                        while time.time() - wait_start < login_wait_time:
                            time.sleep(2)
                            current_url = driver.current_url
                            page_source = driver.page_source

                            if 'login' not in current_url.lower() and not any(
                                keyword in page_source.lower() for keyword in ['로그인', 'login', '아이디', 'password']
                            ):
                                logged_in = True
                                break

                        if not logged_in:
                            result['error'] = f'로그인 대기 시간({login_wait_time}초)이 초과되었습니다.'
                            result['success'] = False
                            return result

                # 로그인 완료 후 실제 매물 페이지로 이동
                driver.set_page_load_timeout(30)
                driver.get(url)

                # 페이지 로드 대기 (부동산뱅크는 JavaScript로 동적 로드)
                time.sleep(5)  # 충분한 대기 시간

                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    # 추가 대기 (동적 콘텐츠 로드)
                    time.sleep(3)
                except BaseException:
                    pass

                # 페이지 소스 가져오기
                page_source = driver.page_source
                result['raw_html'] = page_source

                # BeautifulSoup으로 파싱
                soup = BeautifulSoup(page_source, 'html.parser')

                # 부동산뱅크 페이지에서 정보 추출 (neonet.co.kr 사이트 구조에 맞춤)
                self._extract_realestate_bank_info(soup, driver, result)

                # 정보가 추출되었는지 확인
                has_info = any([
                    result.get('address'),
                    result.get('deposit'),
                    result.get('monthly_rent'),
                    result.get('area_m2'),
                    result.get('area_pyeong'),
                    result.get('floor')
                ])

                if has_info:
                    result['success'] = True
                else:
                    result['error'] = '부동산뱅크 페이지에서 정보를 추출할 수 없습니다. 페이지 구조를 확인해주세요.'
                    result['success'] = False
                    # 디버깅을 위해 페이지 텍스트 일부 저장
                    page_text_preview = soup.get_text()[:2000] if soup else ""
                    result['debug_info'] = f'페이지 텍스트 일부:\n{page_text_preview}'

            else:
                # requests 방법 시도 (부동산뱅크는 JavaScript가 많아 selenium이 더 안정적)
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')
                result['raw_html'] = response.text

                self._extract_realestate_bank_info(soup, None, result)

                has_info = any([
                    result.get('address'),
                    result.get('deposit'),
                    result.get('monthly_rent'),
                    result.get('area_m2')
                ])

                if has_info:
                    result['success'] = True
                else:
                    result['error'] = '부동산뱅크 페이지에서 정보를 추출할 수 없습니다. Selenium을 사용하는 것을 권장합니다.'
                    result['success'] = False

        except Exception as e:
            result['error'] = f'부동산뱅크 크롤링 오류: {str(e)}'
            result['success'] = False
            import traceback
            result['debug_traceback'] = traceback.format_exc()
        finally:
            if driver:
                try:
                    driver.quit()
                except BaseException:
                    pass

        return result

    def _extract_realestate_bank_info(
            self,
            soup: BeautifulSoup,
            driver,
            result: Dict):
        """부동산뱅크 페이지에서 매물 정보 추출 (neonet.co.kr 사이트 구조)"""
        page_text = soup.get_text()

        # Selenium driver가 있으면 더 정확한 정보 추출 시도
        if driver:
            try:
                # 부동산뱅크 사이트의 주요 정보가 있는 요소 찾기
                # 다양한 선택자로 시도
                selectors = [
                    # 테이블 형식
                    'table', 'tbody tr', '.info-table', '.detail-table',
                    # div 형식
                    '.detail-info', '.property-info', '.offerings-info',
                    # 리스트 형식
                    'dl', 'dt', 'dd', '.info-list', '.detail-list'
                ]

                for selector in selectors:
                    try:
                        elements = driver.find_elements(
                            By.CSS_SELECTOR, selector)
                        if elements:
                            # 요소에서 텍스트 추출하여 page_text에 추가
                            for elem in elements[:20]:  # 처음 20개만
                                try:
                                    elem_text = elem.text
                                    if elem_text and len(
                                            elem_text) > 5:  # 의미있는 텍스트만
                                        page_text += "\n" + elem_text
                                except BaseException:
                                    pass
                    except BaseException:
                        pass

                # 특정 필드 직접 찾기 시도 (XPath 사용)
                try:
                    # 소재지 찾기
                    address_xpaths = [
                        "//*[contains(text(), '소재지')]",
                        "//*[contains(text(), '주소')]",
                        "//*[contains(@class, 'address')]",
                        "//*[contains(@id, 'address')]",
                        "//td[contains(text(), '소재지')]",
                        "//th[contains(text(), '소재지')]",
                    ]
                    for xpath in address_xpaths:
                        try:
                            elems = driver.find_elements(By.XPATH, xpath)
                            for elem in elems[:3]:
                                try:
                                    text = elem.text
                                    if text and (
                                            '소재지' in text or '주소' in text):
                                        page_text += "\n" + text
                                except BaseException:
                                    pass
                        except BaseException:
                            pass
                except BaseException:
                    pass
            except BaseException:
                pass

        # 소재지 추출 (부동산뱅크 사이트 구조에 맞춤)
        address_patterns = [
            r'소재지[:\s]*([가-힣\s\d-]+)',
            r'주소[:\s]*([가-힣\s\d-]+)',
            r'위치[:\s]*([가-힣\s\d-]+)',
            r'(대구\s+[가-힣]+구\s+[가-힣\d\s-]+)',
            r'(서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남)\s+[가-힣\s\d-]+',
        ]
        for pattern in address_patterns:
            match = re.search(pattern, page_text)
            if match:
                address = match.group(1).strip()
                # 너무 짧은 주소는 제외 (최소 5자 이상)
                if len(address) >= 5:
                    result['address'] = address
                    break

        # 보증금/월세 추출 (부동산뱅크 사이트 구조에 맞춤)
        price_patterns = [
            r'보증금[:\s]*(\d+)[,만원\s]*[/\s]*월세[:\s]*(\d+)[,만원\s]*',
            r'보증금[:\s]*(\d+)\s*만\s*[/\s]*월세[:\s]*(\d+)\s*만',
            r'(\d+)\s*만\s*/\s*(\d+)\s*만',
            r'(\d+)\s*/\s*(\d+)',  # 단순 숫자/숫자 형식
            r'보증금[:\s]*(\d+)[,만원\s]*',
            r'월세[:\s]*(\d+)[,만원\s]*',
            r'임대료[:\s]*(\d+)[,만원\s]*',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, page_text)
            if match:
                try:
                    if len(match.groups()) >= 2:
                        deposit_val = match.group(1).replace(
                            ',', '').replace('만', '')
                        rent_val = match.group(2).replace(
                            ',', '').replace('만', '')
                        result['deposit'] = int(deposit_val)
                        result['monthly_rent'] = int(rent_val)
                        break
                    elif '보증금' in pattern or '임대료' in pattern:
                        deposit_val = match.group(1).replace(
                            ',', '').replace('만', '')
                        result['deposit'] = int(deposit_val)
                    elif '월세' in pattern:
                        rent_val = match.group(1).replace(
                            ',', '').replace('만', '')
                        result['monthly_rent'] = int(rent_val)
                except BaseException:
                    pass

        # 면적 추출 (부동산뱅크 사이트 구조에 맞춤)
        area_patterns = [
            r'전용면적[:\s]*(\d+\.?\d*)\s*[㎡m²]',
            r'계약면적[:\s]*(\d+\.?\d*)\s*[㎡m²]',
            r'면적[:\s]*(\d+\.?\d*)\s*[㎡m²]',
            r'(\d+\.?\d*)\s*[㎡m²]',
            r'(\d+\.?\d*)\s*평',
            r'약\s*(\d+\.?\d*)\s*평',
        ]
        for pattern in area_patterns:
            match = re.search(pattern, page_text)
            if match:
                try:
                    area_value = float(match.group(1))
                    if '㎡' in pattern or 'm²' in pattern or '[㎡m²]' in pattern:
                        result['area_m2'] = area_value
                        # 평수 계산 (1평 = 3.3058㎡)
                        result['area_pyeong'] = round(area_value / 3.3058, 2)
                    elif '평' in pattern:
                        result['area_pyeong'] = area_value
                        # ㎡ 계산
                        result['area_m2'] = round(area_value * 3.3058, 2)
                    break
                except BaseException:
                    pass

        # 층수 추출 (부동산뱅크 사이트 구조에 맞춤)
        floor_patterns = [
            r'해당층[:\s]*(\d+)\s*층',
            r'층수[:\s]*(\d+)\s*층',
            r'층[:\s]*(\d+)',
            r'(\d+)\s*층',
            r'(\d+)[/]\s*(\d+)\s*층',  # 해당층/총층 형식
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, page_text)
            if match:
                try:
                    if len(match.groups()) >= 2:
                        # 해당층/총층 형식
                        result['floor'] = int(match.group(1))
                        result['total_floors'] = int(match.group(2))
                    else:
                        result['floor'] = int(match.group(1))
                    break
                except BaseException:
                    pass

        # 총 층수 추출 (별도)
        if not result.get('total_floors'):
            total_floor_patterns = [
                r'총\s*(\d+)\s*층',
                r'전체\s*(\d+)\s*층',
                r'건물\s*(\d+)\s*층',
            ]
            for pattern in total_floor_patterns:
                match = re.search(pattern, page_text)
                if match:
                    try:
                        result['total_floors'] = int(match.group(1))
                        break
                    except BaseException:
                        pass

        # 용도 추출
        usage_patterns = [
            r'용도[:\s]*([가-힣\s]+)',
            r'중개대상물[:\s]*([가-힣\s]+)',
        ]
        for pattern in usage_patterns:
            match = re.search(pattern, page_text)
            if match:
                result['usage'] = match.group(1).strip()
                break

        # 화장실 개수 추출
        bathroom_match = re.search(r'화장실[:\s]*(\d+)\s*개', page_text)
        if bathroom_match:
            try:
                result['bathroom_count'] = int(bathroom_match.group(1))
            except BaseException:
                pass

        # 주차 대수 추출
        parking_patterns = [
            r'주차[:\s]*(\d+)\s*대',
            r'주차대수[:\s]*(\d+)',
        ]
        for pattern in parking_patterns:
            match = re.search(pattern, page_text)
            if match:
                try:
                    result['parking'] = int(match.group(1))
                    break
                except BaseException:
                    pass

        # 방향 추출
        direction_patterns = [
            r'방향[:\s]*([가-힣]+향)',
            r'([동서남북]+향)',
        ]
        for pattern in direction_patterns:
            match = re.search(pattern, page_text)
            if match:
                result['direction'] = match.group(1).strip()
                break

        # 사용승인일 추출
        approval_patterns = [
            r'사용승인일[:\s]*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})',
            r'승인일[:\s]*(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2})',
        ]
        for pattern in approval_patterns:
            match = re.search(pattern, page_text)
            if match:
                approval_date_str = match.group(1)
                # 날짜 형식 정규화 (YYYYMMDD)
                approval_date_str = re.sub(r'[.\-/]', '', approval_date_str)
                if len(approval_date_str) == 8:
                    result['approval_date'] = approval_date_str
                break

    def _crawl_with_undetected_chromedriver(
            self, url: str, result: Dict) -> Dict:
        """undetected_chromedriver를 사용한 크롤링 (네이버 보안 시스템 우회)"""
        driver = None
        try:
            # undetected_chromedriver 옵션 설정 (네이버 보안 시스템 강력 우회)
            options = uc.ChromeOptions()

            # 기본 옵션
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')

            # headless 모드 비활성화 (네이버 부동산이 봇을 감지할 수 있음)
            # options.add_argument('--headless=new')

            # 봇 감지 우회를 위한 강력한 옵션
            options.add_argument(
                '--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-infobars')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins-discovery')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')

            # User-Agent를 실제 브라우저처럼 설정
            options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # 실험적 옵션 (봇 감지 우회)
            options.add_experimental_option(
                'excludeSwitches', [
                    'enable-automation', 'enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # Preferences 설정 (봇 감지 우회)
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2
            }
            options.add_experimental_option("prefs", prefs)

            # undetected_chromedriver 생성 (자동으로 봇 감지 우회)
            # version_main=None은 자동으로 Chrome 버전 감지
            # use_subprocess=True로 더 강력한 우회
            driver = uc.Chrome(
                options=options,
                version_main=None,
                use_subprocess=True)

            # 추가적인 봇 감지 우회 스크립트 실행 (더 강력한 버전)
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    // webdriver 속성 완전히 제거
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // plugins 속성 설정
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });

                    // languages 속성 설정
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['ko-KR', 'ko', 'en-US', 'en']
                    });

                    // chrome 객체 추가
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };

                    // permissions API 모킹
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );

                    // WebGL 정보 모킹
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return getParameter.call(this, parameter);
                    };
                '''
            })

            # 마우스 움직임 시뮬레이션 (봇 감지 우회)
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                # 랜덤한 마우스 움직임
                actions.move_by_offset(
                    random.randint(
                        10, 50), random.randint(
                        10, 50)).perform()
                time.sleep(0.5)
            except BaseException:
                pass

            # 원본 URL 그대로 사용
            target_url = url

            # 페이지 로드 (타임아웃 설정)
            driver.set_page_load_timeout(30)  # 30초 타임아웃

            # articleNo 파라미터 보존을 위해 JavaScript로 직접 URL 설정
            # 네이버 사이트가 URL을 리다이렉트하면서 파라미터를 제거하는 것을 방지
            if 'articleNo=' in target_url or 'articleNc=' in target_url:
                # 먼저 네이버 부동산 메인 페이지로 이동 (보안 체크 우회)
                base_url = 'https://new.land.naver.com/offices'
                try:
                    driver.get(base_url)
                    # 랜덤 대기 (봇 감지 우회)
                    time.sleep(random.uniform(3, 5))

                    # 마우스 움직임 시뮬레이션
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_by_offset(
                            random.randint(
                                50, 100), random.randint(
                                50, 100)).perform()
                        time.sleep(random.uniform(1, 2))
                    except BaseException:
                        pass
                except BaseException:
                    pass

                # JavaScript로 전체 URL 설정 (파라미터 포함)
                # 네이버의 리다이렉트를 우회하기 위해 직접 location.href 설정
                driver.execute_script(
                    f"window.location.href = {
                        repr(target_url)};")
                # 랜덤 대기 (봇 감지 우회)
                time.sleep(random.uniform(4, 6))
            else:
                # articleNo가 없는 경우 일반적으로 접속
                driver.get(target_url)
                # 랜덤 대기
                time.sleep(random.uniform(3, 5))

            # JavaScript 렌더링 대기 (네이버 보안 시스템 우회를 위해 충분한 대기)
            # 랜덤 대기로 봇 패턴 숨기기
            time.sleep(random.uniform(5, 8))

            # 마우스 움직임 시뮬레이션 (봇 감지 우회)
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                # 여러 번 랜덤 마우스 움직임
                for _ in range(random.randint(2, 4)):
                    actions.move_by_offset(
                        random.randint(-50, 50), random.randint(-50, 50)).perform()
                    time.sleep(random.uniform(0.5, 1.5))
            except BaseException:
                pass

            # 네이버 부동산 페이지의 주요 요소 대기
            try:
                # 매물 정보가 로드될 때까지 대기
                WebDriverWait(driver, 25).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                # 추가 대기 (네이버 부동산은 동적 콘텐츠가 많고 보안 체크가 있음)
                time.sleep(random.uniform(6, 10))  # 랜덤 대기로 봇 패턴 숨기기

                # 네이버 보안 페이지로 리다이렉트되었는지 확인
                current_url_check = driver.current_url
                page_title_check = driver.title

                # 보안 페이지 감지 (더 많은 패턴 체크)
                security_patterns = [
                    'verify',
                    'security',
                    'captcha',
                    'challenge',
                    'blocked',
                    'access denied']
                is_security_page = any(
                    pattern in current_url_check.lower() for pattern in security_patterns) or any(
                    pattern in page_title_check.lower() for pattern in security_patterns)

                if is_security_page:
                    # 보안 페이지로 이동한 경우 추가 대기 및 재시도
                    time.sleep(random.uniform(10, 15))

                    # 마우스 움직임 추가
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(driver)
                        actions.move_by_offset(
                            random.randint(
                                100, 200), random.randint(
                                100, 200)).perform()
                        time.sleep(random.uniform(2, 4))
                    except BaseException:
                        pass

                    # 다시 원래 URL로 이동 시도
                    if 'articleNo=' in url or 'articleNc=' in url:
                        driver.execute_script(
                            f"window.location.href = {repr(url)};")
                        time.sleep(random.uniform(6, 10))
                    else:
                        driver.get(url)
                        time.sleep(random.uniform(6, 10))
            except BaseException:
                pass  # 타임아웃되어도 계속 진행

            # 페이지 제목과 URL 먼저 확인
            try:
                page_title = driver.title
                current_url = driver.current_url

                # articleNo가 원본 URL에 있었는데 현재 URL에서 사라진 경우 재시도
                if ('articleNo=' in url or 'articleNc=' in url) and \
                   ('articleNo=' not in current_url and 'articleNc=' not in current_url) and \
                   '/404' not in current_url and 'land.naver.com' in current_url:
                    # articleNo 추출
                    article_id = self.extract_article_id(url)
                    if article_id:
                        # 현재 URL에 articleNo 추가
                        if '?' in current_url:
                            retry_url = f"{current_url}&articleNo={article_id}"
                        else:
                            retry_url = f"{current_url}?articleNo={article_id}"

                        # JavaScript로 다시 설정
                        driver.execute_script(
                            f"window.location.href = {
                                repr(retry_url)};")
                        time.sleep(5)  # 대기 시간 증가
                        current_url = driver.current_url
                        page_title = driver.title

                # 404 오류 체크
                if '/404' in current_url or current_url.endswith('/404'):
                    result['error'] = f'요청하신 페이지를 찾을 수 없습니다 (404 오류).\nURL: {current_url}\n원본 URL: {url}\n\n매물이 삭제되었거나 URL이 잘못되었을 수 있습니다.'
                    result['success'] = False
                    result['debug_info'] = f'404 오류 (URL 확인)\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                    return result

                # 네이버 보안 페이지나 메인 페이지로 리다이렉트 확인
                if '네이버 :: 세상의 모든 지식' in page_title and 'land.naver.com' not in current_url:
                    # 보안 페이지 패턴 체크
                    security_patterns = [
                        'verify', 'security', 'captcha', 'challenge', 'blocked']
                    is_security_page = any(
                        pattern in current_url.lower() for pattern in security_patterns)

                    if is_security_page:
                        # 보안 페이지로 이동한 경우, 추가 대기 후 재시도 (최대 3회)
                        max_retries = 3
                        for retry in range(max_retries):
                            time.sleep(random.uniform(10, 15))

                            # 마우스 움직임 시뮬레이션
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                actions = ActionChains(driver)
                                actions.move_by_offset(
                                    random.randint(
                                        100, 300), random.randint(
                                        100, 300)).perform()
                                time.sleep(random.uniform(2, 4))
                            except BaseException:
                                pass

                            # 원래 URL로 다시 이동 시도
                            if 'articleNo=' in url or 'articleNc=' in url:
                                driver.execute_script(
                                    f"window.location.href = {repr(url)};")
                            else:
                                driver.get(url)

                            time.sleep(random.uniform(6, 10))
                            current_url = driver.current_url
                            page_title = driver.title

                            # 네이버 부동산 페이지로 돌아왔는지 확인
                            if 'land.naver.com' in current_url and '네이버 :: 세상의 모든 지식' not in page_title:
                                break  # 성공적으로 돌아옴

                    # 여전히 메인 페이지인 경우 오류 반환
                    if '네이버 :: 세상의 모든 지식' in page_title and 'land.naver.com' not in current_url:
                        result['error'] = f'네이버 메인 페이지로 리다이렉트되었습니다.\n원본 URL: {url}\n현재 URL: {current_url}\n\n로그인이 필요하거나 접근이 제한되었을 수 있습니다.\n\n💡 해결 방법:\n1. 네이버에 로그인한 상태에서 시도해보세요\n2. 잠시 후 다시 시도해보세요\n3. VPN을 사용 중이라면 해제 후 시도해보세요'
                        result['success'] = False
                        result['debug_info'] = f'리다이렉트 발생\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                        return result

                # URL이 네이버 부동산이 아닌 경우 체크
                if 'land.naver.com' not in current_url and 'naver.com' in current_url:
                    # 네이버 다른 페이지로 이동한 경우 재시도
                    time.sleep(5)
                    if 'articleNo=' in url or 'articleNc=' in url:
                        driver.execute_script(
                            f"window.location.href = {repr(url)};")
                        time.sleep(5)
                        current_url = driver.current_url
                    else:
                        driver.get(url)
                        time.sleep(5)
                        current_url = driver.current_url

                    # 여전히 네이버 부동산이 아닌 경우 오류 반환
                    if 'land.naver.com' not in current_url:
                        result['error'] = f'페이지가 네이버 부동산으로 리다이렉트되었습니다. 현재 URL: {current_url}'
                        result['success'] = False
                        result['debug_info'] = f'리다이렉트 발생\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                        return result
            except Exception as e:
                # URL이나 제목을 가져오는 중 오류 발생 (세션 종료 등)
                result['error'] = f'페이지 정보를 가져오는 중 오류 발생: {str(e)}'
                result['success'] = False
                return result

            # 페이지 소스 가져오기
            page_source = driver.page_source
            result['raw_html'] = page_source

            # 페이지 소스에서 404 오류 메시지 확인
            if '찾을 수 없습니다' in page_source or '요청하신 페이지를 찾을 수 없습니다' in page_source:
                result['error'] = f'요청하신 페이지를 찾을 수 없습니다 (404 오류).\nURL: {current_url}\n원본 URL: {url}\n\n매물이 삭제되었거나 URL이 잘못되었을 수 있습니다.'
                result['success'] = False
                result['debug_info'] = f'404 오류 (페이지 소스 확인)\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                return result

            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(page_source, 'html.parser')

            # 정보 추출
            self._extract_info_from_selenium(driver, soup, result)

            # 정보가 하나라도 추출되었는지 확인
            has_info = any([
                result.get('address'),
                result.get('deposit'),
                result.get('monthly_rent'),
                result.get('area_m2'),
                result.get('area_pyeong'),
                result.get('floor')
            ])

            if not has_info:
                # 정보 추출 실패 - 디버깅을 위해 페이지 텍스트 일부 저장
                page_text_preview = soup.get_text()[:1000] if soup else ""
                result['debug_info'] = f'페이지 제목: {page_title}\n페이지 텍스트 일부:\n{page_text_preview}'

            result['success'] = True

        except Exception as e:
            error_msg = str(e)
            result['error'] = f'undetected_chromedriver 크롤링 오류: {error_msg}'
            result['success'] = False
            import traceback
            result['debug_traceback'] = traceback.format_exc()

            # 세션 오류인 경우 특별 처리
            if 'invalid session id' in error_msg.lower(
            ) or 'session deleted' in error_msg.lower():
                result['error'] = '브라우저 세션이 예기치 않게 종료되었습니다. Chrome 브라우저가 정상적으로 설치되어 있는지 확인하고, 다시 시도해주세요.'
        finally:
            if driver:
                try:
                    driver.quit()
                except BaseException:
                    pass

        return result

    def _crawl_with_selenium(self, url: str, result: Dict) -> Dict:
        """Selenium을 사용한 크롤링 (폴백)"""
        driver = None
        try:
            # Chrome 옵션 설정
            chrome_options = Options()
            # headless 모드 비활성화 (네이버 부동산이 봇을 감지할 수 있음)
            # chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(
                f'user-agent={self.headers["User-Agent"]}')
            chrome_options.add_experimental_option(
                'excludeSwitches', ['enable-logging', 'enable-automation'])
            chrome_options.add_experimental_option(
                'useAutomationExtension', False)
            chrome_options.add_argument(
                '--disable-blink-features=AutomationControlled')
            # 추가 옵션: 네이버 부동산 접근을 위한 설정
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')

            # ChromeDriver 자동 다운로드 및 설정
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)

            # 자바스크립트 실행으로 봇 감지 우회
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                '''
            })

            # 원본 URL 그대로 사용 (변환하지 않음)
            # 네이버 부동산의 /offices 형식 URL은 /article/detail로 변환하면 404 오류 발생
            # 따라서 원본 URL을 그대로 사용
            target_url = url

            # 페이지 로드 (타임아웃 설정)
            driver.set_page_load_timeout(30)  # 30초 타임아웃

            # articleNo 파라미터 보존을 위해 JavaScript로 직접 URL 설정
            # 네이버 사이트가 URL을 리다이렉트하면서 파라미터를 제거하는 것을 방지
            if 'articleNo=' in target_url or 'articleNc=' in target_url:
                # 먼저 기본 페이지로 이동
                base_url = target_url.split(
                    '?')[0] if '?' in target_url else target_url
                driver.get(base_url)
                time.sleep(1)  # 페이지 로드 대기

                # JavaScript로 전체 URL 설정 (파라미터 포함)
                driver.execute_script(
                    f"window.location.href = {
                        repr(target_url)};")
                time.sleep(2)  # 리다이렉트 대기
            else:
                # articleNo가 없는 경우 일반적으로 접속
                driver.get(target_url)

            # JavaScript 렌더링 대기 (최대 15초)
            time.sleep(3)  # 기본 대기

            # 네이버 부동산 페이지의 주요 요소 대기
            try:
                # 매물 정보가 로드될 때까지 대기
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                # 추가 대기 (네이버 부동산은 동적 콘텐츠가 많음)
                time.sleep(3)
            except BaseException:
                pass  # 타임아웃되어도 계속 진행

            # 페이지 제목과 URL 먼저 확인 (페이지 소스 가져오기 전에)
            try:
                page_title = driver.title
                current_url = driver.current_url

                # articleNo가 원본 URL에 있었는데 현재 URL에서 사라진 경우 재시도
                if ('articleNo=' in url or 'articleNc=' in url) and \
                   ('articleNo=' not in current_url and 'articleNc=' not in current_url) and \
                   '/404' not in current_url and 'land.naver.com' in current_url:
                    # articleNo 추출
                    article_id = self.extract_article_id(url)
                    if article_id:
                        # 현재 URL에 articleNo 추가
                        if '?' in current_url:
                            retry_url = f"{current_url}&articleNo={article_id}"
                        else:
                            retry_url = f"{current_url}?articleNo={article_id}"

                        # JavaScript로 다시 설정
                        driver.execute_script(
                            f"window.location.href = {
                                repr(retry_url)};")
                        time.sleep(3)
                        current_url = driver.current_url

                # 404 오류 체크 (URL 우선 확인 - 가장 확실한 방법)
                if '/404' in current_url or current_url.endswith('/404'):
                    result['error'] = f'요청하신 페이지를 찾을 수 없습니다 (404 오류).\nURL: {current_url}\n원본 URL: {url}\n\n매물이 삭제되었거나 URL이 잘못되었을 수 있습니다.'
                    result['success'] = False
                    result['debug_info'] = f'404 오류 (URL 확인)\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                    return result

                # 네이버 메인 페이지로 리다이렉트 확인
                if '네이버 :: 세상의 모든 지식' in page_title and 'land.naver.com' not in current_url:
                    result['error'] = f'네이버 메인 페이지로 리다이렉트되었습니다.\n원본 URL: {url}\n현재 URL: {current_url}\n\n로그인이 필요하거나 접근이 제한되었을 수 있습니다.'
                    result['success'] = False
                    result['debug_info'] = f'리다이렉트 발생\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                    return result

                # URL이 네이버 부동산이 아닌 경우 체크
                if 'land.naver.com' not in current_url:
                    result['error'] = f'페이지가 네이버 부동산으로 리다이렉트되었습니다. 현재 URL: {current_url}'
                    result['success'] = False
                    result['debug_info'] = f'리다이렉트 발생\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                    return result
            except Exception as e:
                # URL이나 제목을 가져오는 중 오류 발생 (세션 종료 등)
                result['error'] = f'페이지 정보를 가져오는 중 오류 발생: {str(e)}'
                result['success'] = False
                return result

            # 페이지 소스 가져오기
            page_source = driver.page_source
            result['raw_html'] = page_source

            # 페이지 소스에서 404 오류 메시지 확인
            if '찾을 수 없습니다' in page_source or '요청하신 페이지를 찾을 수 없습니다' in page_source:
                result['error'] = f'요청하신 페이지를 찾을 수 없습니다 (404 오류).\nURL: {current_url}\n원본 URL: {url}\n\n매물이 삭제되었거나 URL이 잘못되었을 수 있습니다.'
                result['success'] = False
                result['debug_info'] = f'404 오류 (페이지 소스 확인)\n원본 URL: {url}\n현재 URL: {current_url}\n페이지 제목: {page_title}'
                return result

            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(page_source, 'html.parser')

            # 정보 추출
            self._extract_info_from_selenium(driver, soup, result)

            # 정보가 하나라도 추출되었는지 확인
            has_info = any([
                result.get('address'),
                result.get('deposit'),
                result.get('monthly_rent'),
                result.get('area_m2'),
                result.get('area_pyeong'),
                result.get('floor')
            ])

            if not has_info:
                # 정보 추출 실패 - 디버깅을 위해 페이지 텍스트 일부 저장
                page_text_preview = soup.get_text()[:1000] if soup else ""
                result['debug_info'] = f'페이지 제목: {page_title}\n페이지 텍스트 일부:\n{page_text_preview}'

            result['success'] = True

        except Exception as e:
            error_msg = str(e)
            result['error'] = f'Selenium 크롤링 오류: {error_msg}'
            result['success'] = False
            import traceback
            result['debug_traceback'] = traceback.format_exc()

            # 세션 오류인 경우 특별 처리
            if 'invalid session id' in error_msg.lower(
            ) or 'session deleted' in error_msg.lower():
                result['error'] = '브라우저 세션이 예기치 않게 종료되었습니다. Chrome 브라우저가 정상적으로 설치되어 있는지 확인하고, 다시 시도해주세요.'
        finally:
            if driver:
                try:
                    driver.quit()
                except BaseException:
                    pass

        return result

    def _crawl_with_requests(self, url: str, result: Dict) -> Dict:
        """requests를 사용한 크롤링 (폴백)"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            result['raw_html'] = response.text

            self._extract_basic_info(soup, result)
            result['success'] = True

        except requests.RequestException as e:
            result['error'] = f'페이지 요청 오류: {str(e)}'
            result['success'] = False

        return result

    def _extract_info_from_selenium(
            self,
            driver,
            soup: BeautifulSoup,
            result: Dict):
        """Selenium으로 렌더링된 페이지에서 정보 추출"""
        # 네이버 부동산 페이지 구조는 변경될 수 있으므로
        # 실제 페이지 구조를 확인하여 수정해야 합니다.

        # 텍스트 전체에서 패턴 매칭 시도
        page_text = soup.get_text()

        # 소재지 추출 (다양한 패턴 시도)
        # 예: "대구 중구 삼덕동2가 122" 또는 "소재지: ..."
        address_patterns = [
            r'소재지[:\s]+([가-힣\s\d-]+)',
            r'주소[:\s]+([가-힣\s\d-]+)',
            r'(대구\s+중구\s+[가-힣\d\s-]+)',
        ]
        for pattern in address_patterns:
            match = re.search(pattern, page_text)
            if match:
                result['address'] = match.group(1).strip()
                break

        # 가격 정보 추출 (보증금/월세)
        # 예: "보증금 1,000만원 / 월세 65만원" 또는 "1000/65"
        price_patterns = [
            r'보증금[:\s]*(\d+)[,만원\s]*/\s*월세[:\s]*(\d+)[,만원\s]*',
            r'(\d+)\s*/\s*(\d+)\s*만',
            r'(\d+)\s*만\s*/\s*(\d+)\s*만',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, page_text)
            if match:
                try:
                    result['deposit'] = int(match.group(1).replace(',', ''))
                    result['monthly_rent'] = int(
                        match.group(2).replace(',', ''))
                    break
                except BaseException:
                    pass

        # 면적 추출 (㎡ 및 평)
        area_patterns = [
            r'(\d+\.?\d*)\s*㎡',
            r'(\d+\.?\d*)\s*m²',
            r'(\d+\.?\d*)\s*평',
        ]
        for pattern in area_patterns:
            match = re.search(pattern, page_text)
            if match:
                area_value = float(match.group(1))
                if '㎡' in pattern or 'm²' in pattern:
                    result['area_m2'] = area_value
                elif '평' in pattern:
                    result['area_pyeong'] = area_value

        # 층수 추출
        floor_match = re.search(r'(\d+)\s*층', page_text)
        if floor_match:
            result['floor'] = int(floor_match.group(1))

        # 총 층수 추출 (예: "5층 / 5층" 또는 "5/5층")
        total_floor_match = re.search(r'(\d+)\s*/\s*(\d+)\s*층', page_text)
        if total_floor_match:
            result['floor'] = int(total_floor_match.group(1))
            result['total_floors'] = int(total_floor_match.group(2))

    def _extract_basic_info(self, soup: BeautifulSoup, result: Dict):
        """HTML에서 기본 정보 추출 (requests 사용 시)"""
        # 네이버 부동산 페이지 구조는 변경될 수 있으므로
        # 실제 페이지 구조를 확인하여 수정해야 합니다.

        # 소재지 추출
        address_elem = soup.find(
            'span', class_=re.compile(
                '.*address.*', re.I))
        if address_elem:
            result['address'] = address_elem.get_text(strip=True)

        # 가격 정보 추출 (보증금/월세)
        price_elem = soup.find('span', class_=re.compile('.*price.*', re.I))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # 가격 파싱 (예: "1000/65" 형식)
            price_match = re.search(r'(\d+)\s*/\s*(\d+)', price_text)
            if price_match:
                result['deposit'] = int(price_match.group(1))
                result['monthly_rent'] = int(price_match.group(2))

        # 면적 추출
        area_elem = soup.find('span', class_=re.compile('.*area.*', re.I))
        if area_elem:
            area_text = area_elem.get_text(strip=True)
            # 면적 파싱 (예: "43.09m²" 또는 "13평")
            area_m2_match = re.search(r'(\d+\.?\d*)\s*m[²2]', area_text)
            if area_m2_match:
                result['area_m2'] = float(area_m2_match.group(1))

            area_pyeong_match = re.search(r'(\d+\.?\d*)\s*평', area_text)
            if area_pyeong_match:
                result['area_pyeong'] = float(area_pyeong_match.group(1))

        # 층수 추출
        floor_elem = soup.find('span', class_=re.compile('.*floor.*', re.I))
        if floor_elem:
            floor_text = floor_elem.get_text(strip=True)
            floor_match = re.search(r'(\d+)\s*층', floor_text)
            if floor_match:
                result['floor'] = int(floor_match.group(1))


if __name__ == "__main__":
    # 테스트
    crawler = NaverPropertyCrawler()

    # 테스트 URL (실제 네이버 부동산 URL로 교체 필요)
    test_url = "https://land.naver.com/article/detail/12345678"

    print("네이버 부동산 크롤링 테스트")
    print(f"URL: {test_url}")
    print("-" * 60)

    result = crawler.crawl_property_info(test_url)

    print(f"성공: {result['success']}")
    if result['error']:
        print(f"오류: {result['error']}")
    else:
        print(f"주소: {result['address']}")
        print(f"보증금: {result['deposit']}")
        print(f"월세: {result['monthly_rent']}")
        print(f"면적(m²): {result['area_m2']}")
        print(f"면적(평): {result['area_pyeong']}")
        print(f"층수: {result['floor']}")
