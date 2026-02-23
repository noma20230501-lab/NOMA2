"""
모드 A: 블로그 필수표시사항 생성기 - 독립 로직 모듈

카카오톡 매물 텍스트를 입력받아 건축물대장 API와 연동하여
블로그 필수표시사항 광고 텍스트를 생성하는 순수 로직입니다.

사용법:
    from mode_a_logic import ModeAProcessor

    # 방법 1: config.py에 BUILDING_API_KEY가 있으면 자동 로드 (권장)
    processor = ModeAProcessor()

    # 방법 2: API 키 직접 지정
    processor = ModeAProcessor(api_key="YOUR_API_KEY")

    result = processor.process(kakao_text)
    
    if result.get("error"):
        print(f"오류: {result['error']}")
    elif result.get("need_building_selection"):
        # 건축물 여러 개 → 사용자 선택 필요
        buildings = result["buildings"]
        # 선택 후: result = processor.process(kakao_text, building_idx=0)
    elif result.get("need_unit_selection"):
        # 전유부분 여러 개 → 사용자 선택 필요
        units = result["units"]
        # 선택 후: result = processor.process(kakao_text, unit_idx=0) 또는 unit_idx="total"
    elif result.get("need_usage_selection"):
        # 점포 용도 선택 필요
        # 선택 후: result = processor.process(kakao_text, selected_usage="제1종 근린생활시설")
    else:
        # 최종 결과
        print(result["text"])

의존 모듈:
    - kakao_parser.py (KakaoPropertyParser)
    - building_registry_api.py (BuildingRegistryAPI)
    - address_code_helper.py (parse_address)
"""

import re
from typing import Dict, Optional, List, Tuple, Any
from concurrent.futures import ThreadPoolExecutor

from kakao_parser import KakaoPropertyParser
from building_registry_api import BuildingRegistryAPI
from address_code_helper import parse_address


class ModeAProcessor:
    """모드 A 블로그 필수표시사항 생성 프로세서 (UI 독립)"""

    def __init__(self, api_key: str = None):
        """
        Args:
            api_key: 공공데이터포털 건축물대장 API 키
                     미입력 시 config.py의 BUILDING_API_KEY를 자동으로 사용합니다.
        """
        if api_key is None:
            try:
                from config import BUILDING_API_KEY
                api_key = BUILDING_API_KEY
            except ImportError:
                raise ValueError(
                    "API 키를 입력하거나 config.py에 BUILDING_API_KEY를 설정해주세요.\n"
                    "예시: ModeAProcessor(api_key='YOUR_KEY')"
                )
        self.api = BuildingRegistryAPI(api_key)
        self.kakao_parser = KakaoPropertyParser()

    # ──────────────────────────────────────────────
    # 메인 엔트리포인트
    # ──────────────────────────────────────────────
    def process(
        self,
        kakao_text: str,
        building_idx: Optional[int] = None,
        unit_idx: Optional[Any] = None,       # int 또는 "total"
        selected_usage: Optional[str] = None,
        cached_buildings: Optional[List[Dict]] = None,
        cached_floor_result: Optional[Dict] = None,
        cached_area_result: Optional[Dict] = None,
        cached_unit_result: Optional[Dict] = None,
    ) -> Dict:
        """
        카카오톡 매물 텍스트를 처리하여 블로그 필수표시사항을 생성합니다.

        Args:
            kakao_text: 카카오톡 매물 텍스트
            building_idx: 건축물 선택 인덱스 (여러 건축물 중 선택)
            unit_idx: 전유부분 선택 인덱스 (int) 또는 "total" (통임대)
            selected_usage: 점포 용도 선택 ("제1종 근린생활시설" 등)
            cached_buildings: 이전에 조회된 건축물 목록 (API 재호출 방지)
            cached_floor_result: 이전에 조회된 층별 정보
            cached_area_result: 이전에 조회된 면적 정보
            cached_unit_result: 이전에 조회된 전유부 정보

        Returns:
            Dict: 결과 딕셔너리
                성공 시: {"text": str, "parsed": dict, ...}
                건축물 선택 필요 시: {"need_building_selection": True, "buildings": [...]}
                전유부분 선택 필요 시: {"need_unit_selection": True, "units": [...]}
                용도 선택 필요 시: {"need_usage_selection": True, "usage_options": [...]}
                오류 시: {"error": str}
        """
        try:
            return self._process_internal(
                kakao_text, building_idx, unit_idx, selected_usage,
                cached_buildings, cached_floor_result,
                cached_area_result, cached_unit_result,
            )
        except Exception as e:
            import traceback
            return {"error": f"오류 발생: {str(e)}\n\n{traceback.format_exc()}"}

    def _process_internal(
        self, kakao_text, building_idx, unit_idx, selected_usage,
        cached_buildings, cached_floor_result, cached_area_result, cached_unit_result,
    ) -> Dict:
        # ── 1. 위반건축물 감지 ──
        violation_detected = False
        violation_keywords = ["위반건축물", "불법건축물", "위반있음"]
        first_line = kakao_text.split("\n")[0] if kakao_text else ""
        for keyword in violation_keywords:
            cleaned = re.sub(r"[^\w\s가-힣]", "", first_line)
            if keyword in cleaned:
                violation_detected = True
                kakao_text = "\n".join(kakao_text.split("\n")[1:])
                break

        # ── 2. 카카오톡 파싱 ──
        parsed = self.kakao_parser.parse(kakao_text)
        if violation_detected:
            parsed["violation_building"] = True
        if not parsed.get("address"):
            return {"error": "주소를 찾을 수 없습니다."}

        address = parsed["address"]
        floor = parsed.get("floor")
        ho = parsed.get("ho")
        dong = parsed.get("dong")

        # ── 3. 주소 파싱 ──
        address_info = parse_address(address)
        if not address_info.get("sigungu_code") or not address_info.get("bjdong_code"):
            return {"error": f"주소를 파싱할 수 없습니다: {address}"}

        # ── 4. 건축물대장 조회 (캐시 또는 API) ──
        buildings = cached_buildings
        if buildings is None:
            title_result = self.api.get_title_info(
                sigungu_cd=address_info["sigungu_code"],
                bjdong_cd=address_info["bjdong_code"],
                bun=address_info["bun"],
                ji=address_info["ji"],
                num_of_rows=10,
            )
            if not title_result.get("success") or not title_result.get("data"):
                error_msg = title_result.get("error", "") or title_result.get("resultMsg", "알 수 없는 오류")
                return {"error": f"건축물대장 정보를 조회할 수 없습니다.\n오류: {error_msg}"}
            buildings = title_result["data"]

            # 동 정보로 필터링
            if dong and len(buildings) > 1:
                filtered = self._filter_buildings_by_dong(buildings, dong)
                if filtered:
                    buildings = filtered

        # ── 5. 건축물 선택 ──
        if len(buildings) > 1:
            if building_idx is None:
                return {
                    "need_building_selection": True,
                    "buildings": buildings,
                    "parsed": parsed,
                    "address_info": address_info,
                    "building_count": len(buildings),
                }
            if building_idx >= len(buildings):
                return {"error": f"선택한 건축물 인덱스({building_idx})가 범위를 벗어났습니다."}
            building = buildings[building_idx]
        else:
            building = buildings[0]

        # ── 6. 층별/면적/전유부 API 병렬 호출 ──
        floor_result = cached_floor_result
        area_result = cached_area_result
        unit_result = cached_unit_result

        if floor_result is None and building and building.get("mgmBldrgstPk"):
            floor_result, area_result, unit_result = self._fetch_detail_apis(
                address_info, building, ho
            )

        # ── 7. 전유부분 선택 (같은 층 여러 호수) ──
        selected_units_info = None
        if floor:
            all_units = self._get_all_units_on_floor(area_result, floor, floor_result)

            if len(all_units) > 1:
                if unit_idx is None:
                    # 자동 호수 매칭 시도
                    auto_idx = self._auto_match_ho(parsed.get("ho"), all_units)
                    if auto_idx is not None:
                        unit_idx = auto_idx
                    else:
                        kakao_area = parsed.get("area_m2") or parsed.get("actual_area_m2")
                        unit_comparison = self._compare_unit_areas(kakao_area, all_units)
                        return {
                            "need_unit_selection": True,
                            "units": all_units,
                            "unit_comparison": unit_comparison,
                            "parsed": parsed,
                            "address_info": address_info,
                            "building": building,
                            "buildings": buildings,
                            "floor": floor,
                            "floor_result": floor_result,
                            "area_result": area_result,
                            "unit_result": unit_result,
                            "unit_count": len(all_units),
                        }

                # 선택된 전유부분 처리
                if unit_idx == "total":
                    total_area = sum(u["area"] for u in all_units)
                    selected_units_info = {
                        "type": "total",
                        "area": total_area,
                        "usage": all_units[0].get("main_usage"),
                        "units": all_units,
                    }
                elif isinstance(unit_idx, int) and unit_idx < len(all_units):
                    sel = all_units[unit_idx]
                    selected_units_info = {
                        "type": "single",
                        "area": sel["area"],
                        "usage": sel.get("main_usage"),
                        "ho": sel.get("ho"),
                        "unit": sel,
                    }

        # ── 8. 용도 판정 ──
        usage_judgment = self._judge_usage(building, parsed, floor_result, floor, area_result)

        if usage_judgment.get("judged_usage") == "__NEED_USAGE_SELECTION__":
            if selected_usage:
                usage_judgment["judged_usage"] = selected_usage
            else:
                return {
                    "need_usage_selection": True,
                    "usage_options": ["제1종 근린생활시설", "제2종 근린생활시설", "근린생활시설"],
                    "parsed": parsed,
                    "building": building,
                    "buildings": buildings,
                    "floor_result": floor_result,
                    "area_result": area_result,
                    "unit_result": unit_result,
                    "floor": floor,
                    "address_info": address_info,
                    "selected_units_info": selected_units_info,
                }

        # 선택된 전유부분 용도 반영
        if selected_units_info and selected_units_info.get("usage"):
            usage_judgment["selected_unit_usage"] = selected_units_info["usage"]
            if not usage_judgment.get("judged_usage"):
                usage_judgment["judged_usage"] = selected_units_info["usage"]

        if selected_usage:
            usage_judgment["judged_usage"] = selected_usage

        # ── 9. 면적 비교 ──
        area_comparison = self._compare_areas(
            parsed, building, floor_result, area_result, floor, unit_result, selected_units_info
        )
        if area_comparison is None:
            area_comparison = {}

        if selected_units_info:
            if "registry_area" not in area_comparison or area_comparison.get("registry_area") is None:
                area_comparison["registry_area"] = selected_units_info["area"]
            area_comparison["selected_unit_area"] = selected_units_info["area"]
            area_comparison["selected_unit_type"] = selected_units_info["type"]
            if selected_units_info["type"] == "total":
                area_comparison["unit_breakdown"] = [
                    {"ho": u.get("ho"), "area": u["area"], "usage": u.get("main_usage")}
                    for u in selected_units_info["units"]
                ]

        # ── 10. 블로그 텍스트 생성 ──
        blog_result = self._generate_blog_text(
            parsed, building, floor_result, floor,
            usage_judgment, area_comparison, area_result, None
        )

        if isinstance(blog_result, tuple):
            result_lines = blog_result[0]
        else:
            result_lines = blog_result

        if isinstance(result_lines, str):
            result_lines = result_lines.split("\n")
        elif not isinstance(result_lines, (list, tuple)):
            result_lines = [str(result_lines)]

        # ── 11. 결과 텍스트 조립 ──
        result_text, area_options = self._assemble_result_text(result_lines)

        # 면적 정보 교체
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
                area_parts.append(f"대장: {area_options['registry']}㎡({pyeong}평)")
            area_text = " / ".join(area_parts) if area_parts else "확인요망"
            result_text = result_text.replace("• 전용면적: \n", f"• 전용면적: {area_text}\n")

        return {
            "text": result_text.strip(),
            "parsed": parsed,
            "building": building,
            "buildings": buildings,
            "address_info": address_info,
            "usage_judgment": usage_judgment,
            "area_comparison": area_comparison,
            "area_options": area_options,
            "floor_result": floor_result,
            "area_result": area_result,
            "unit_result": unit_result,
        }

    # ──────────────────────────────────────────────
    # 내부 헬퍼 메서드
    # ──────────────────────────────────────────────
    def _filter_buildings_by_dong(self, buildings: List[Dict], dong: str) -> List[Dict]:
        """동 정보로 건축물 필터링"""
        filtered = []
        for bld in buildings:
            bld_dong = None
            for field in ["dongNm", "dongNo", "dong", "dongNmNm", "bldDongNm"]:
                if field in bld and bld[field]:
                    bld_dong = str(bld[field]).strip()
                    break
            if bld_dong:
                input_dong_num = re.sub(r"[^\d]", "", str(dong))
                api_dong_num = re.sub(r"[^\d]", "", bld_dong)
                if input_dong_num and api_dong_num and input_dong_num == api_dong_num:
                    filtered.append(bld)
        return filtered

    def _fetch_detail_apis(self, address_info: Dict, building: Dict, ho) -> Tuple:
        """층별/면적/전유부 API 병렬 호출"""
        params = {
            "sigungu_cd": address_info["sigungu_code"],
            "bjdong_cd": address_info["bjdong_code"],
            "bun": address_info["bun"],
            "ji": address_info["ji"],
            "mgm_bldrgst_pk": building["mgmBldrgstPk"],
        }
        with ThreadPoolExecutor(max_workers=3) as executor:
            floor_future = executor.submit(self.api.get_floor_info, **params, num_of_rows=50)
            area_future = executor.submit(self.api.get_unit_area_info, **params, num_of_rows=100)
            unit_future = None
            if ho:
                unit_future = executor.submit(self.api.get_unit_info, **params, num_of_rows=100)
            floor_result = floor_future.result()
            area_result = area_future.result()
            unit_result = unit_future.result() if unit_future else None
        return floor_result, area_result, unit_result

    def _auto_match_ho(self, input_ho, all_units: List[Dict]) -> Optional[int]:
        """카톡 호수와 전유부분 자동 매칭"""
        if not input_ho:
            return None
        normalized = str(input_ho).replace('호', '').strip()
        matched = []
        for idx, unit in enumerate(all_units):
            unit_ho = str(unit.get('ho', '')).replace('호', '').strip()
            if normalized == unit_ho or normalized.lower() == unit_ho.lower():
                matched.append(idx)
        return matched[0] if len(matched) == 1 else None

    def _assemble_result_text(self, result_lines: List) -> Tuple[str, Dict]:
        """결과 라인을 텍스트로 조립하고 면적 옵션 추출"""
        result_text = ""
        area_options = {}
        pending_area_line = None
        area_selection_found = False

        for line in result_lines:
            line_str = str(line).strip()

            if not line_str:
                result_text += "\n"
                continue

            if line_str == "__AREA_SELECTION__":
                area_selection_found = True
                if pending_area_line:
                    result_text += pending_area_line + "\n"
                    pending_area_line = None
                continue
            elif line_str.startswith("__ACTUAL_AREA__"):
                val = line_str.replace("__ACTUAL_AREA__", "").replace("__", "").strip()
                if val:
                    try: area_options["actual"] = float(val)
                    except: pass
                continue
            elif line_str.startswith("__KAKAO_AREA__"):
                val = line_str.replace("__KAKAO_AREA__", "").replace("__", "").strip()
                if val:
                    try: area_options["kakao"] = float(val)
                    except: pass
                continue
            elif line_str.startswith("__REGISTRY_AREA__"):
                val = line_str.replace("__REGISTRY_AREA__", "").replace("__", "").strip()
                if val:
                    try: area_options["registry"] = float(val)
                    except: pass
                continue
            elif line_str.startswith("__USAGE_") or line_str.startswith("__"):
                continue
            elif "전용면적:" in line_str:
                if area_selection_found:
                    pending_area_line = line_str if line_str.startswith("•") else "• " + line_str
                    continue
                else:
                    result_text += (line_str if line_str.startswith("•") else "• " + line_str) + "\n"
                    continue
            else:
                result_text += (line_str if line_str.startswith("•") else "• " + line_str) + "\n"

        if pending_area_line:
            result_text += pending_area_line + "\n"

        # 비어있으면 원본 라인에서 재구성
        if not result_text.strip():
            for line in result_lines:
                line_str = str(line).strip()
                if line_str and not line_str.startswith("__"):
                    result_text += ("• " + line_str if not line_str.startswith("•") else line_str) + "\n"

        if not result_text.strip():
            result_text = "⚠️ 결과 텍스트가 생성되지 않았습니다.\n입력 정보를 확인하고 다시 시도해주세요.\n"

        return result_text, area_options

    # ──────────────────────────────────────────────
    # 용도 분류 마스터 (28가지 대분류 매칭 규칙)
    # ──────────────────────────────────────────────
    def _classify_usage_master(self, api_usage_str, area_m2, floor_result, floor, area_result, ho, unit_result):
        """
        중개대상물 종류 판정 마스터 함수 (3단계 프로세스)
        Returns: (final_usage, show_usage_warning, show_usage_warning_point)
        """
        show_usage_warning = False
        show_usage_warning_point = False

        if api_usage_str:
            api_usage_str = api_usage_str.replace('사무실', '사무소')

        # 3단계: 출력 예외 규칙
        if api_usage_str and ('점포 및 주택' in api_usage_str or '주택 및 점포' in api_usage_str or
                              ('점포' in api_usage_str and '주택' in api_usage_str and '및' in api_usage_str)):
            return (api_usage_str, True, False)

        if api_usage_str and api_usage_str.strip() == '점포':
            return ('__NEED_USAGE_SELECTION__', False, False)

        if api_usage_str:
            if '제1종근린생활시설' in api_usage_str or '제1종 근린생활시설' in api_usage_str:
                return ('제1종 근린생활시설', False, False)
            elif '제2종근린생활시설' in api_usage_str or '제2종 근린생활시설' in api_usage_str:
                return ('제2종 근린생활시설', False, False)

        # 층별개요 용도 우선 처리
        if api_usage_str and area_m2:
            usage_lower = api_usage_str.lower()
            area = float(area_m2) if area_m2 else 0

            if '소매점' in usage_lower:
                return ('제1종 근린생활시설', False, False) if area < 1000 else ('판매시설', False, False)
            if any(kw in usage_lower for kw in ['휴게음식점', '커피숍', '제과점', '카페']):
                return ('제1종 근린생활시설', False, False) if area < 300 else ('제2종 근린생활시설', False, False)
            if '일반음식점' in usage_lower:
                return ('제2종 근린생활시설', False, False)
            if '사무소' in usage_lower:
                if area < 30: return ('제1종 근린생활시설', False, False)
                elif area < 500: return ('제2종 근린생활시설', False, False)
                else: return ('업무시설', False, False)
            if any(kw in usage_lower for kw in ['학원', '교습소']):
                return ('제2종 근린생활시설', False, False) if area < 500 else ('교육연구시설', False, False)
            if '노래연습장' in usage_lower or '노래방' in usage_lower:
                return ('제2종 근린생활시설', False, False)
            if any(kw in usage_lower for kw in ['의원', '치과', '한의원']):
                return ('제1종 근린생활시설', False, False)
            if any(kw in usage_lower for kw in ['이용원', '미용원', '세탁소', '미용실', '이발소']):
                return ('제1종 근린생활시설', False, False)
            if '체육도장' in usage_lower or '헬스장' in usage_lower:
                return ('제1종 근린생활시설', False, False) if area < 500 else ('운동시설', False, False)
            if 'pc방' in usage_lower or '게임장' in usage_lower:
                return ('제2종 근린생활시설', False, False) if area < 500 else ('위락시설', False, False)

        # 2단계: 28가지 대분류 매칭 규칙
        if not api_usage_str or not area_m2:
            return ("확인요망", False, False)

        usage_lower = api_usage_str.lower()
        area = float(area_m2) if area_m2 else 0

        commercial_keywords = [
            '점포', '소매점', '슈퍼마켓', '마트', '편의점', '상점', '매장',
            '사무소', '사무실', '휴게음식점', '일반음식점', '카페', '커피숍',
            '학원', '교습소', '노래연습장', '의원', '병원', '미용원', '이용원'
        ]
        has_commercial = any(k in usage_lower for k in commercial_keywords)

        # 주택
        if not has_commercial:
            if any(kw in usage_lower for kw in ['단독', '단독주택', '다중', '다중주택', '다가구', '다가구주택', '공관']):
                return ('단독주택', False, False)
            if any(kw in usage_lower for kw in ['아파트', '연립', '연립주택', '다세대', '다세대주택', '기숙사', '공동주택']):
                return ('공동주택', False, False)

        # 제1종 근린생활시설
        if any(kw in usage_lower for kw in ['소매점', '슈퍼마켓', '마트', '편의점', '상점', '매장', '일용품']) and area < 1000:
            return ('제1종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['휴게음식점', '커피숍', '제과점', '카페']) and area < 300:
            return ('제1종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['이용원', '미용원', '목욕장', '세탁소', '미용실', '이발소']):
            return ('제1종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['의원', '치과의원', '한의원', '산후조리원']):
            return ('제1종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['탁구장', '체육도장']) and area < 500:
            return ('제1종 근린생활시설', False, False)
        if '공공업무시설' in usage_lower and area < 1000:
            return ('제1종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['사무소', '중개사무소']) and area < 30:
            return ('제1종 근린생활시설', False, False)

        # 제2종 근린생활시설
        if any(kw in usage_lower for kw in ['공연장', '종교집회장']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        if '자동차영업소' in usage_lower and area < 1000:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['서점', '사진관', '동물병원']):
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['pc방', '게임장']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['휴게음식점', '커피숍', '제과점', '카페']) and area >= 300:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['일반음식점', '안마시술소', '노래연습장', '노래방']):
            return ('제2종 근린생활시설', False, False)
        if '단란주점' in usage_lower and area < 150:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['학원', '교습소']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['운동시설', '체육시설']) and area < 500:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['사무소', '중개사무소']) and 30 <= area < 500:
            return ('제2종 근린생활시설', False, False)
        if '고시원' in usage_lower and area < 500:
            return ('제2종 근린생활시설', False, False)
        if any(kw in usage_lower for kw in ['제조업소', '수리점']) and area < 500:
            return ('제2종 근린생활시설', False, False)

        # 기타 대분류
        if (any(kw in usage_lower for kw in ['공연장', '집회장']) and area >= 300) or \
           (any(kw in usage_lower for kw in ['관람장']) and area >= 1000) or \
           any(kw in usage_lower for kw in ['전시장', '동식물원']):
            return ('문화 및 집회시설', False, False)
        if any(kw in usage_lower for kw in ['종교집회장', '봉안당']) and area >= 300:
            return ('종교시설', False, False)
        if any(kw in usage_lower for kw in ['농수산물도매시장', '대규모점포']) or \
           (any(kw in usage_lower for kw in ['소매점', '슈퍼마켓', '마트', '편의점', '상점', '매장', '일용품']) and area >= 1000) or \
           (any(kw in usage_lower for kw in ['오락실', 'pc방', '게임장']) and area >= 500):
            return ('판매시설', False, False)
        if any(kw in usage_lower for kw in ['여객자동차터미널', '철도', '공항', '항만시설']):
            return ('운수시설', False, False)
        if any(kw in usage_lower for kw in ['병원', '종합병원', '치과병원', '한방병원', '격리병원', '전염병원', '정신병원', '요양소']):
            return ('의료시설', False, False)
        if any(kw in usage_lower for kw in ['학교', '교육원', '연구소', '도서관']) or \
           ('사설강습소' in usage_lower and '근생' not in usage_lower and '무도' not in usage_lower):
            return ('교육연구시설', False, False)
        if any(kw in usage_lower for kw in ['아동관련시설', '노인복지시설', '사회복지시설']):
            return ('노유자시설', False, False)
        if any(kw in usage_lower for kw in ['청소년수련관', '수련원', '야영장', '유스호스텔']):
            return ('수련시설', False, False)
        if (any(kw in usage_lower for kw in ['탁구장', '체육도장', '볼링장']) and area >= 500) or \
           (any(kw in usage_lower for kw in ['체육관', '운동장']) and area >= 1000):
            return ('운동시설', False, False)
        if any(kw in usage_lower for kw in ['국가청사', '지자체청사', '오피스텔']) or \
           (any(kw in usage_lower for kw in ['금융업소', '사무소']) and area >= 500):
            return ('업무시설', False, False)
        if any(kw in usage_lower for kw in ['호텔', '여관', '여인숙']) or \
           ('고시원' in usage_lower and area >= 500):
            return ('숙박시설', False, False)
        if any(kw in usage_lower for kw in ['유흥음식점', '무도장']) or \
           ('단란주점' in usage_lower and area >= 150):
            return ('위락시설', False, False)
        if any(kw in usage_lower for kw in ['제조', '가공', '수리']) and area >= 500:
            return ('공장', False, False)
        if any(kw in usage_lower for kw in ['일반창고', '냉장창고', '냉동창고', '물류터미널']):
            return ('창고시설', False, False)
        if any(kw in usage_lower for kw in ['주유소', '석유판매소', '액화가스충전소', '위험물제조소']):
            return ('위험물 저장 및 처리시설', False, False)
        if any(kw in usage_lower for kw in ['주차장', '세차장', '폐차장', '검사장', '정비공장', '정비학원']):
            return ('자동차 관련시설', False, False)
        if any(kw in usage_lower for kw in ['축사', '도축장', '작물재배사', '종묘배양시설', '온실']):
            return ('동물 및 식물 관련시설', False, False)
        if any(kw in usage_lower for kw in ['고물상', '폐기물재활용', '폐기물감량화']):
            return ('분뇨 및 쓰레기 처리시설', False, False)
        if any(kw in usage_lower for kw in ['교정시설', '소년원', '국방시설', '군사시설']):
            return ('교정 및 군사시설', False, False)
        if any(kw in usage_lower for kw in ['방송국', '촬영소', '통신용시설']):
            return ('방송통신시설', False, False)
        if '발전소' in usage_lower:
            return ('발전시설', False, False)
        if (any(kw in usage_lower for kw in ['화장시설', '봉안당']) and '종교시설' not in usage_lower) or \
           any(kw in usage_lower for kw in ['묘지부수건축물']):
            return ('묘지 관련 시설', False, False)
        if any(kw in usage_lower for kw in ['야외음악당', '야외극장', '어린이회관', '휴게소']):
            return ('관광 휴게시설', False, False)
        if '장례식장' in usage_lower:
            return ('장례식장', False, False)

        return (api_usage_str, True, False)

    # ──────────────────────────────────────────────
    # 건축물대장 정보 추출 유틸리티
    # ──────────────────────────────────────────────
    def get_approval_date(self, building: Dict) -> str:
        """사용승인일 추출"""
        use_apr_day = building.get('useAprDay', '') or building.get('pmsDay', '')
        if use_apr_day and str(use_apr_day).strip():
            return self._format_date(str(use_apr_day))
        return ''

    def get_total_floors(self, building: Dict) -> int:
        """총층수 추출"""
        total_floor = building.get('grndFlrCnt', '') or building.get('heit', '') or building.get('flrCnt', '')
        if total_floor and str(total_floor).strip():
            try:
                return int(str(total_floor).strip())
            except:
                pass
        return 0

    def get_parking_count(self, building: Dict) -> int:
        """주차대수 추출"""
        parking_spaces = None
        parking_fields = {
            'indrAutoUtcnt': '자주식(실내)',
            'oudrAutoUtcnt': '자주식(실외)',
            'indrMechUtcnt': '기계식(실내)',
            'oudrMechUtcnt': '기계식(실외)',
        }
        total = 0
        for field in parking_fields:
            val = building.get(field, '')
            if val and str(val).strip():
                try:
                    total += int(float(str(val).strip()))
                except:
                    pass
        if total > 0:
            return total
        # 단일 필드 확인
        for field in ['pkngCnt', 'totPkngCnt', 'indrAutoUtcnt']:
            val = building.get(field, '')
            if val and str(val).strip():
                try:
                    return int(float(str(val).strip()))
                except:
                    pass
        return 0

    def _format_date(self, date_str: str) -> str:
        """날짜 형식 변환 (YYYYMMDD → YYYY-MM-DD)"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    def _normalize_usage(self, usage_str: str) -> Optional[str]:
        """용도 문자열을 정규화"""
        if not usage_str:
            return None
        usage_str = str(usage_str).strip()
        if '판매시설' in usage_str or '기타판매시설' in usage_str:
            return '판매시설'
        if re.search(r'제?2종\s*(?:근린생활시설|근생)?', usage_str) and \
           not re.search(r'[3-9]종|1[0-9]종|2[1-9]종', usage_str):
            return '제2종 근린생활시설'
        if re.search(r'제?1종\s*(?:근린생활시설|근생)?', usage_str) and \
           not re.search(r'[2-9]종|1[1-9]종|2[0-9]종', usage_str):
            return '제1종 근린생활시설'
        return usage_str

    def parse_floor_string(self, floor_str: str) -> Optional[int]:
        """층 문자열을 정수로 파싱 (지하: 음수, 지상: 양수)"""
        if not floor_str:
            return None
        floor_str = str(floor_str).strip()
        for pat in [r'지하\s*(\d+)', r'B\s*(\d+)', r'b\s*(\d+)', r'-\s*(\d+)']:
            m = re.search(pat, floor_str)
            if m:
                return -int(m.group(1))
        if '지상' in floor_str:
            m = re.search(r'지상\s*(\d+)', floor_str)
            if m:
                return int(m.group(1))
        for pat in [r'(\d+)\s*층', r'(\d+)\s*F', r'^(\d+)$']:
            m = re.search(pat, floor_str, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return None

    def match_floor(self, search_floor: int, registry_floor_str: str) -> bool:
        """입력 층수와 건축물대장 층 문자열 일치 확인"""
        if not registry_floor_str:
            return False
        fs = str(registry_floor_str).strip()
        ss = str(search_floor)
        fn = re.sub(r'[^0-9]', '', fs)
        sn = str(abs(search_floor))

        if search_floor < 0:
            if '지하' in fs or 'B' in fs or 'b' in fs:
                return fn == sn
            return False
        else:
            if '지하' in fs or 'B' in fs or 'b' in fs:
                return False
            if fs == ss or fs == f"{ss}층" or fs == f"{ss}F":
                return True
            if fs == f"지상{ss}" or fs == f"지상{ss}층":
                return True
            if fn == sn:
                if search_floor == 1:
                    return '지상' in fs or fs == '1'
                return True
            if fs.startswith(f"{ss}층"):
                rest = fs[len(f"{ss}층"):]
                if not rest or not rest[0].isdigit():
                    return True
            return False

    # ──────────────────────────────────────────────
    # 용도 판정
    # ──────────────────────────────────────────────
    def _judge_usage(self, building, parsed, floor_result, floor, area_result=None):
        """건축물대장 면적/용도로 법정 명칭 판정"""
        api_usage = None
        etc_usage = None
        search_floor = floor if floor else 1
        ho = parsed.get('ho')

        # 1. 전유공용면적 API에서 호수별 용도 확인
        if ho and area_result and area_result.get('success') and area_result.get('data'):
            unit_area, unit_usage = self._get_unit_area_and_usage(ho, area_result, floor_result, floor)
            if unit_usage:
                api_usage = str(unit_usage).strip()
                for area_info in area_result['data']:
                    ho_nm = area_info.get('hoNm', '')
                    ho_normalized = str(ho).replace('호', '').strip()
                    ho_nm_normalized = str(ho_nm).replace('호', '').strip()
                    if ho_normalized == ho_nm_normalized:
                        etc_purps = area_info.get('etcPurps', '')
                        if etc_purps and str(etc_purps).strip() != str(unit_usage).strip():
                            etc_usage = str(etc_purps).strip()
                        break

        # 2. 층별개요에서 용도 확인 (전유부에서 못 찾았을 때)
        api_usage_list = [api_usage] if api_usage else []
        etc_usage_list = [etc_usage] if etc_usage else []

        if not api_usage and floor_result and floor_result.get('success') and floor_result.get('data'):
            for fi in floor_result['data']:
                floor_num = (fi.get('flrNoNm', '') or fi.get('flrNo', '') or
                             fi.get('flrNoNm1', '') or fi.get('flrNo1', '') or
                             fi.get('flrNoNm2', '') or fi.get('flrNo2', ''))
                if self.match_floor(search_floor, str(floor_num).strip()):
                    mu = fi.get('mainPurpsCdNm', '') or fi.get('mainPurps', '') or fi.get('mainPurpsCdNm1', '') or fi.get('mainPurps1', '')
                    ou = fi.get('etcPurps', '') or fi.get('etcPurps1', '')
                    if mu and mu not in api_usage_list:
                        api_usage_list.append(mu)
                    if ou and ou not in etc_usage_list:
                        etc_usage_list.append(ou)

        if not api_usage:
            api_usage = ', '.join(api_usage_list) if api_usage_list else None
        if not etc_usage:
            etc_usage = ', '.join(etc_usage_list) if etc_usage_list else None

        # 카톡 용도 (참고용)
        kakao_usage = parsed.get('usage', '')

        # 건축물대장 면적 가져오기
        area_m2 = self._get_area_for_usage(area_result, floor, parsed)

        # 추가 정보
        total_area = building.get('totArea', '') or building.get('totArea1', '')
        grnd_flr_cnt = building.get('grndFlrCnt', '')
        hhld_cnt = building.get('hhldCnt', '') or building.get('hhldCnt1', '')
        try:
            total_area = float(str(total_area).strip()) if total_area else None
            grnd_flr_cnt = int(float(str(grnd_flr_cnt).strip())) if grnd_flr_cnt else None
            hhld_cnt = int(float(str(hhld_cnt).strip())) if hhld_cnt else None
        except:
            total_area = grnd_flr_cnt = hhld_cnt = None

        judgment = {
            'api_usage': api_usage, 'etc_usage': etc_usage,
            'kakao_usage': kakao_usage, 'judged_usage': None,
            'area_m2': area_m2, 'total_area': total_area,
            'grnd_flr_cnt': grnd_flr_cnt, 'hhld_cnt': hhld_cnt,
        }

        api_usage_str = str(api_usage).replace('사무실', '사무소') if api_usage else ''
        etc_usage_str = str(etc_usage).replace('사무실', '사무소') if etc_usage else ''

        if etc_usage_str and ('근린생활시설' in etc_usage_str or '제1종' in etc_usage_str or '제2종' in etc_usage_str):
            usage_str_for_classify = etc_usage_str
        else:
            usage_str_for_classify = api_usage_str
            if etc_usage_str:
                usage_str_for_classify = f"{usage_str_for_classify}, {etc_usage_str}" if usage_str_for_classify else etc_usage_str

        final_usage, warn, warn_point = self._classify_usage_master(
            usage_str_for_classify, area_m2, floor_result, floor, area_result, ho, None
        )
        judgment['judged_usage'] = final_usage
        judgment['show_usage_warning'] = warn
        judgment['show_usage_warning_point'] = warn_point
        return judgment

    def _get_area_for_usage(self, area_result, floor, parsed):
        """용도 판정용 면적 추출"""
        area_m2 = None
        search_floor = floor if floor else 1
        if area_result and area_result.get('success') and area_result.get('data'):
            for ai in area_result['data']:
                fn = ai.get('flrNoNm', '') or ai.get('flrNo', '') or ai.get('flrNo1', '')
                if self.match_floor(search_floor, str(fn).strip()):
                    for field in ['exclArea', 'exclArea1', 'exclArea2', 'exclArea3',
                                  'exclTotArea', 'exclTotArea1', 'exclTotArea2']:
                        val = ai.get(field, '')
                        if val:
                            try:
                                area_m2 = float(str(val).strip())
                                if area_m2 > 0: break
                            except: pass
                    if area_m2: break
        if not area_m2: area_m2 = parsed.get('area_m2')
        if not area_m2: area_m2 = parsed.get('actual_area_m2')
        return area_m2

    # ──────────────────────────────────────────────
    # 면적 비교
    # ──────────────────────────────────────────────
    def _compare_areas(self, parsed, building, floor_result, area_result, floor,
                       unit_result=None, selected_units_info=None):
        """건축물대장 면적과 카카오톡 면적 비교"""
        kakao_area = parsed.get('area_m2')
        if not kakao_area:
            return None

        actual_area_m2 = parsed.get('actual_area_m2')
        registry_area = None
        search_floor = floor if floor else 1
        ho = parsed.get('ho')

        if selected_units_info and selected_units_info.get("area"):
            registry_area = selected_units_info["area"]
        else:
            registry_area = self._get_floor_area_from_api(floor_result, floor, area_result, ho, unit_result)

        if not registry_area:
            registry_area = self._get_floor_area_from_api(floor_result, floor, area_result, ho, unit_result)

        comparison = {
            'kakao_area': kakao_area,
            'actual_area_m2': actual_area_m2,
            'registry_area': registry_area,
            'floor': floor,
            'ho': ho,
        }

        if registry_area and kakao_area:
            try:
                diff = abs(float(registry_area) - float(kakao_area))
                comparison['area_diff'] = round(diff, 2)
                comparison['area_match'] = diff < 0.1
            except:
                pass

        return comparison

    def _get_floor_area_from_api(self, floor_result, floor, area_result, ho=None, unit_result=None):
        """API에서 해당 층 전용면적 추출 (전유부 > 층별개요 우선)"""
        registry_area = None
        search_floor = floor if floor else 1

        # 1. 호수가 있으면 전유공용면적에서 검색
        if ho and area_result and area_result.get('success') and area_result.get('data'):
            ho_normalized = str(ho).replace('호', '').strip()
            for ai in area_result['data']:
                ho_nm = ai.get('hoNm', '')
                ho_nm_n = str(ho_nm).replace('호', '').strip() if ho_nm else ''
                expos = ai.get('exposPubuseGbCdNm', '')
                if ho_normalized == ho_nm_n and expos and '전유' in expos:
                    area_val = ai.get('area', '')
                    if area_val:
                        try:
                            registry_area = float(str(area_val).strip())
                            if registry_area > 0:
                                return registry_area
                        except:
                            pass

        # 2. 층별개요에서 검색
        if floor_result and floor_result.get('success') and floor_result.get('data'):
            for fi in floor_result['data']:
                fn = fi.get('flrNoNm', '') or fi.get('flrNo', '')
                if self.match_floor(search_floor, str(fn).strip()):
                    area_val = fi.get('area', '')
                    if area_val:
                        try:
                            registry_area = float(str(area_val).strip())
                            if registry_area > 0:
                                return registry_area
                        except:
                            pass

        return registry_area

    # ──────────────────────────────────────────────
    # 전유부분 관련
    # ──────────────────────────────────────────────
    def _compare_unit_areas(self, kakao_area, units: List[Dict]) -> Dict:
        """카카오톡 면적과 전유부분 면적 비교하여 추천"""
        if not units:
            return {}
        total_area = sum(u["area"] for u in units)
        result = {
            "type": "multiple",
            "total_area": total_area,
            "units": units,
            "recommended": None,
            "match_total": False,
        }
        if kakao_area:
            try:
                ka = float(kakao_area)
                if abs(total_area - ka) < 0.1:
                    result["recommended"] = "total"
                    result["match_total"] = True
                else:
                    for idx, u in enumerate(units):
                        if abs(u["area"] - ka) < 0.1:
                            result["recommended"] = idx
                            break
            except:
                pass
        return result

    def _get_all_units_on_floor(self, area_result, floor, floor_result=None) -> List[Dict]:
        """해당 층의 모든 전유부분 조회"""
        units = []
        search_floor = floor if floor else 1

        if area_result and area_result.get('success') and area_result.get('data'):
            for ai in area_result['data']:
                expos = ai.get('exposPubuseGbCdNm', '')
                if not expos or '전유' not in expos:
                    continue
                fn = ai.get('flrNoNm', '') or ai.get('flrNo', '')
                if self.match_floor(search_floor, str(fn).strip()):
                    area_val = ai.get('area', '')
                    try:
                        area_float = float(str(area_val).strip()) if area_val else 0
                    except:
                        area_float = 0
                    if area_float > 0:
                        units.append({
                            "ho": ai.get('hoNm', ''),
                            "area": area_float,
                            "main_usage": ai.get('mainPurpsCdNm', '') or ai.get('mainPurps', ''),
                            "etc_usage": ai.get('etcPurps', ''),
                            "floor": str(fn).strip(),
                        })

        if not units and floor_result:
            units = self._get_all_units_from_floor_result(floor_result, floor)

        return units

    def _get_all_units_from_floor_result(self, floor_result, floor) -> List[Dict]:
        """층별개요에서 해당 층의 모든 면적 추출"""
        units = []
        search_floor = floor if floor else 1

        if not floor_result or not floor_result.get('success') or not floor_result.get('data'):
            return units

        for fi in floor_result['data']:
            fn = fi.get('flrNoNm', '') or fi.get('flrNo', '')
            if self.match_floor(search_floor, str(fn).strip()):
                area_val = fi.get('area', '')
                try:
                    area_float = float(str(area_val).strip()) if area_val else 0
                except:
                    area_float = 0
                if area_float > 0:
                    units.append({
                        "ho": fi.get('hoNm', '') or '',
                        "area": area_float,
                        "main_usage": fi.get('mainPurpsCdNm', '') or fi.get('mainPurps', ''),
                        "etc_usage": fi.get('etcPurps', ''),
                        "floor": str(fn).strip(),
                    })

        return units

    def _get_unit_area_and_usage(self, ho, area_result, floor_result=None, floor=None):
        """전유공용면적 API에서 호수별 면적 및 용도 추출"""
        unit_area = None
        unit_usage = None

        if not ho or not area_result or not area_result.get('success') or not area_result.get('data'):
            return None, None

        ho_normalized = str(ho).replace('호', '').strip()

        for ai in area_result['data']:
            ho_nm = ai.get('hoNm', '')
            ho_nm_n = str(ho_nm).replace('호', '').strip() if ho_nm else ''
            expos = ai.get('exposPubuseGbCdNm', '')

            if ho_normalized == ho_nm_n:
                if expos and '전유' in expos:
                    area_val = ai.get('area', '')
                    if area_val:
                        try:
                            unit_area = float(str(area_val).strip())
                        except:
                            pass
                    usage = ai.get('mainPurpsCdNm', '') or ai.get('mainPurps', '')
                    if usage:
                        unit_usage = str(usage).strip()
                    etc_purps = ai.get('etcPurps', '')
                    if not unit_usage and etc_purps:
                        unit_usage = str(etc_purps).strip()
                    if unit_area and unit_area > 0:
                        return unit_area, unit_usage

        # 층별개요에서 재시도
        if not unit_area and floor_result and floor_result.get('success') and floor_result.get('data'):
            search_floor = floor if floor else 1
            for fi in floor_result['data']:
                fn = fi.get('flrNoNm', '') or fi.get('flrNo', '')
                if self.match_floor(search_floor, str(fn).strip()):
                    mu = fi.get('mainPurpsCdNm', '') or fi.get('mainPurps', '')
                    if mu and not unit_usage:
                        unit_usage = str(mu).strip()

        return unit_area, unit_usage

    # ──────────────────────────────────────────────
    # 블로그 텍스트 생성 (_generate_blog_text)
    # ──────────────────────────────────────────────
    def _generate_blog_text(self, parsed, building, floor_result, floor,
                            usage_judgment, area_comparison=None, area_result=None, unit_result=None):
        """블로그 필수표시사항 텍스트 생성"""
        lines = []

        ho = parsed.get('ho')
        is_collective_building = False
        unit_area = None
        unit_usage = None

        # 호수가 있으면 집합건물 여부 확인
        if ho and area_result and area_result.get('success') and area_result.get('data'):
            unit_area, unit_usage = self._get_unit_area_and_usage(ho, area_result, floor_result, floor)
            if unit_area and unit_area > 0:
                is_collective_building = True
            elif unit_usage:
                is_collective_building = True

        # 1. 소재지
        address = parsed.get('address', '')
        if address:
            address = re.sub(r'\s*\d+\s*층\s*.*$', '', address).strip()
            # 건물명 제거 (번지수 이후)
            addr_match = re.match(r'(.+?\d+(?:-\d+)?(?:번지)?)\s+(.+)', address)
            if addr_match:
                address = addr_match.group(1)
            # "대구"가 없으면 앞에 추가
            if address and not any(city in address for city in
                                    ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
                                     '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주']):
                address = f"대구 {address}"

        # 호수 포함 여부
        location_str = address
        if ho:
            location_str = f"{address} {ho}" if address else str(ho)
        lines.append(f"소재지: {location_str}")

        # 2. 면적 (전용면적)
        lines.append("__AREA_SELECTION__")
        if area_comparison:
            actual = area_comparison.get('actual_area_m2')
            kakao = area_comparison.get('kakao_area')
            registry = area_comparison.get('registry_area')
            if actual:
                lines.append(f"__ACTUAL_AREA__{actual}__")
            if kakao:
                lines.append(f"__KAKAO_AREA__{kakao}__")
            if registry:
                lines.append(f"__REGISTRY_AREA__{registry}__")
        lines.append("전용면적: ")

        # 3. 보증금/월세 (임대차 정보)
        deposit = parsed.get('deposit')
        monthly_rent = parsed.get('monthly_rent')
        if deposit is not None:
            if monthly_rent is not None and monthly_rent > 0:
                lines.append(f"보증금/월세: {deposit:,}만원 / {monthly_rent:,}만원")
            else:
                lines.append(f"보증금/월세: {deposit:,}만원")

        # 4. 관리비
        maintenance = parsed.get('maintenance_fee', '')
        if maintenance:
            lines.append(f"관리비: {maintenance}")

        # 5. 중개대상물 종류 (용도)
        judged_usage = usage_judgment.get('judged_usage', '확인요망')
        if judged_usage:
            lines.append(f"중개대상물 종류: {judged_usage}")
        else:
            lines.append("중개대상물 종류: 확인요망")

        # 6. 거래 형태
        lines.append("거래형태: 임대")

        # 7. 총 층수
        total_floors = self.get_total_floors(building)
        if total_floors > 0:
            lines.append(f"총 층수: {total_floors}층")
        else:
            lines.append("총 층수: 확인요망")

        # 8. 해당 층
        if floor:
            if floor < 0:
                lines.append(f"해당 층수: 지하{abs(floor)}층")
            else:
                lines.append(f"해당 층수: {floor}층")
        else:
            lines.append("해당 층수: 확인요망")

        # 9. 입주 가능일
        move_in = parsed.get('move_in_date', '')
        if move_in:
            lines.append(f"입주가능일: {move_in}")

        # 10. 사용승인일
        approval_date = self.get_approval_date(building)
        if approval_date:
            lines.append(f"사용승인일: {approval_date}")
        else:
            lines.append("사용승인일: 확인요망")

        # 11. 화장실
        bathroom = parsed.get('bathroom_count')
        if bathroom:
            lines.append(f"화장실: {bathroom}")

        # 12. 주차
        parking = parsed.get('parking', '')
        parking_count = self.get_parking_count(building)
        if parking:
            lines.append(f"주차: {parking}")
        elif parking_count > 0:
            lines.append(f"주차: {parking_count}대")

        # 13. 방향
        direction = parsed.get('direction', '')
        if direction:
            lines.append(f"방향: {direction}")

        # 14. 권리관계
        rights = parsed.get('rights', '')
        if rights:
            lines.append(f"권리관계: {rights}")

        # 15. 위반건축물 판정
        violation = parsed.get('violation_building', False)
        if violation:
            lines.append("건축물대장상 위반 건축물: ⚠️ 위반건축물")
        else:
            # API 데이터에서 위반 여부 확인
            vlat_gb_cd_nm = building.get('vlatGbCdNm', '') or building.get('vlatGbCd', '')
            is_violation = False
            if vlat_gb_cd_nm:
                vlat_str = str(vlat_gb_cd_nm).strip()
                violation_keywords = ['위반', '불법', 'Y', 'y', '1']
                normal_keywords = ['정상', '해당없음', '해당 없음', 'N', 'n', '0', '적합']
                is_normal = any(kw in vlat_str for kw in normal_keywords)
                if not is_normal:
                    is_violation = any(kw in vlat_str for kw in violation_keywords)
            if is_violation:
                lines.append("건축물대장상 위반 건축물: ⚠️ 위반건축물")
            else:
                is_normal = False
                if vlat_gb_cd_nm:
                    normal_kws = ['정상', '해당없음', '해당 없음', 'N', 'n', '0', '적합']
                    is_normal = any(kw in str(vlat_gb_cd_nm).strip() for kw in normal_kws)
                if is_normal:
                    lines.append("건축물대장상 위반 건축물: 해당없음")
                else:
                    lines.append("건축물대장상 위반 건축물: 확인요망")

        # 16. 미등기 건물
        items_text = parsed.get('items_text', '')
        if items_text:
            items_lower_cleaned = re.sub(r'\s', '', items_text.lower())
            for kw in ['미등기', '등기없음', '등기안됨', '등기x']:
                if kw in items_lower_cleaned:
                    lines.append("미등기 건물")
                    break

        lines.append("")
        lines.append("총 층수는 지하층은 제외")

        return lines, False, False

    # ──────────────────────────────────────────────
    # 결과에서 번지수 제거 (복사용)
    # ──────────────────────────────────────────────
    @staticmethod
    def remove_address_numbers(text: str) -> str:
        """소재지 라인에서 번지수를 제거"""
        lines = text.split('\n')
        processed = []
        for line in lines:
            if '소재지:' in line or '소재지 :' in line:
                if '소재지:' in line:
                    prefix = line.split('소재지:')[0] + '소재지:'
                    addr = line.split('소재지:')[1].strip()
                else:
                    prefix = line.split('소재지 :')[0] + '소재지 :'
                    addr = line.split('소재지 :')[1].strip()
                addr_cleaned = re.sub(r'\s+(산\s*)?\d+(-\d+)?(번지)?$', '', addr)
                processed.append(f"{prefix} {addr_cleaned}")
            else:
                processed.append(line)
        return '\n'.join(processed)
