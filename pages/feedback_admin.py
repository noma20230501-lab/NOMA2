"""
피드백 관리 페이지
제보된 오류 및 개선 제안을 확인하고 관리
"""

import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="피드백 관리",
    page_icon="📋",
    layout="wide"
)

st.title("📋 피드백 관리 시스템")

# 피드백 파일 로드
feedback_file = 'feedbacks.json'

if not os.path.exists(feedback_file):
    st.info("📭 제보된 피드백이 없습니다.")
    st.stop()

with open(feedback_file, 'r', encoding='utf-8') as f:
    feedbacks = json.load(f)

if not feedbacks:
    st.info("📭 제보된 피드백이 없습니다.")
    st.stop()

# 통계
st.markdown("### 📊 통계")
col1, col2, col3, col4 = st.columns(4)

total = len(feedbacks)
pending = len([f for f in feedbacks if f.get('status') == 'pending'])
in_progress = len([f for f in feedbacks if f.get('status') == 'in_progress'])
completed = len([f for f in feedbacks if f.get('status') == 'completed'])

col1.metric("전체", total)
col2.metric("대기중", pending, delta=None, delta_color="off")
col3.metric("처리중", in_progress, delta=None, delta_color="off")
col4.metric("완료", completed, delta=None, delta_color="off")

st.markdown("---")

# 필터링
st.markdown("### 🔍 필터")
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    filter_mode = st.multiselect(
        "모드",
        ["모드 A", "모드 B"],
        default=["모드 A", "모드 B"]
    )

with filter_col2:
    filter_type = st.multiselect(
        "오류 유형",
        ["버그/오류", "기능 개선 제안", "UI/UX 개선", "기타"],
        default=["버그/오류", "기능 개선 제안", "UI/UX 개선", "기타"]
    )

with filter_col3:
    filter_status = st.multiselect(
        "상태", [
            "pending", "in_progress", "completed"], default=[
            "pending", "in_progress"], format_func=lambda x: {
                "pending": "대기중", "in_progress": "처리중", "completed": "완료"}[x])

# 필터링된 피드백
filtered_feedbacks = [
    f for f in feedbacks
    if f.get('mode', 'N/A') in filter_mode
    and f.get('type') in filter_type
    and f.get('status') in filter_status
]

# 정렬 (최신순)
filtered_feedbacks.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

st.markdown("---")
st.markdown(f"### 📝 피드백 목록 ({len(filtered_feedbacks)}개)")

# 피드백 표시
for idx, feedback in enumerate(filtered_feedbacks):
    mode_emoji = "📋" if feedback.get('mode') == "모드 A" else "🔍"
    status_emoji = "✅" if feedback.get(
        'status') == 'completed' else "⏳" if feedback.get('status') == 'pending' else "🔄"

    with st.expander(
        f"{mode_emoji} #{feedback.get('id', 'N/A')} - "
        f"[{feedback.get('mode', 'N/A')}] [{feedback.get('type', '미분류')}] "
        f"({status_emoji})"
    ):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**제보자:** {feedback.get('reporter', '익명')}")
            st.markdown(f"**모드:** {feedback.get('mode', 'N/A')}")
            st.markdown(f"**유형:** {feedback.get('type', 'N/A')}")
            st.markdown(f"**오류 내용:**")

            # 오류 내용을 스크롤 없이 전체 표시 (높이 자동 조절)
            description_lines = feedback.get('description', '').count('\n') + 1
            text_height = min(max(150, description_lines * 25),
                              600)  # 최소 150, 최대 600

            st.text_area(
                "내용",
                value=feedback.get('description', ''),
                height=text_height,
                disabled=True,
                label_visibility="collapsed",
                key=f"desc_{idx}"
            )

        with col2:
            st.markdown(f"**ID:** {feedback.get('id', 'N/A')}")
            st.markdown(f"**제보일시:**")
            try:
                timestamp = datetime.fromisoformat(
                    feedback.get('timestamp', ''))
                st.write(timestamp.strftime("%Y-%m-%d %H:%M"))
            except BaseException:
                st.write(feedback.get('timestamp', 'N/A'))

            st.markdown("**상태 변경:**")
            current_status = feedback.get('status', 'pending')
            new_status = st.selectbox(
                "상태",
                ["pending", "in_progress", "completed"],
                index=["pending", "in_progress", "completed"].index(current_status),
                format_func=lambda x: {"pending": "⏳ 대기중", "in_progress": "🔄 처리중", "completed": "✅ 완료"}[x],
                key=f"status_{idx}",
                label_visibility="collapsed"
            )

            if st.button(
                "💾 상태 저장",
                key=f"save_{idx}",
                    use_container_width=True):
                # 상태 업데이트
                feedback['status'] = new_status
                feedback['updated_at'] = datetime.now().isoformat()

                # 파일 저장
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    json.dump(feedbacks, f, ensure_ascii=False, indent=2)

                st.success("✅ 상태가 업데이트되었습니다!")
                st.rerun()

            if st.button(
                "🗑️ 삭제",
                key=f"delete_{idx}",
                    use_container_width=True):
                feedbacks.remove(feedback)

                # 파일 저장
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    json.dump(feedbacks, f, ensure_ascii=False, indent=2)

                st.success("✅ 피드백이 삭제되었습니다!")
                st.rerun()

st.markdown("---")

# 전체 삭제 버튼
if st.button("🗑️ 모든 피드백 삭제", type="secondary"):
    if st.checkbox("정말 모든 피드백을 삭제하시겠습니까?"):
        feedbacks.clear()
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedbacks, f, ensure_ascii=False, indent=2)
        st.success("✅ 모든 피드백이 삭제되었습니다!")
        st.rerun()
