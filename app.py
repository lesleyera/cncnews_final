# app.py
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import pandas as pd

# 모듈 임포트
import config
import auth
import data
import views
from utils import WEEK_MAP

# 1. 페이지 설정
st.set_page_config(
    layout="wide", 
    page_title="쿡앤셰프 주간 성과보고서", 
    page_icon="📰", 
    initial_sidebar_state="collapsed"
)

# 2. 스타일 적용
st.markdown(config.CSS, unsafe_allow_html=True)
st.markdown(config.PRINT_CSS, unsafe_allow_html=True)

# html2pdf.js 미리 로드
pdf_library_script = """
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
"""
st.components.v1.html(pdf_library_script, height=0, width=0)

# 3. 보안 체크
if not auth.check_password():
    st.stop()

# =================================================================
# ▼ 메인 로직 시작 ▼
# =================================================================

# 세션 상태 초기화
if 'print_mode' not in st.session_state:
    st.session_state['print_mode'] = False
if 'generate_pdf' not in st.session_state:
    st.session_state['generate_pdf'] = False

# 상단 헤더 영역 (인쇄 모드에서는 숨김)
if not st.session_state['print_mode']:
    c1, c2 = st.columns([2, 1])
    with c1: 
        st.markdown('<div class="report-title">📰 쿡앤셰프 주간 성과보고서</div>', unsafe_allow_html=True)

    with c2:
        col_btn1, col_btn2 = st.columns(2)
        # 일반 모드에서 인쇄 미리보기 버튼
        if col_btn2.button("🖨️ 인쇄 미리보기", type="primary"):
            st.session_state['print_mode'] = True
            st.rerun()
        
        selected_week = st.selectbox("📅 조회 주차", list(WEEK_MAP.keys()), key="week_select", label_visibility="collapsed")
        st.session_state['selected_week_for_print'] = selected_week

    st.markdown(f'<div class="period-info">📅 조회 기간: {WEEK_MAP[selected_week]}</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='update-time'>최종 집계: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
else:
    # 인쇄 모드에서는 헤더 영역에 버튼만 표시 (인쇄 시 숨김)
    st.markdown("""
    <style>
    /* 인쇄 모드에서 버튼 영역을 최소화 */
    .print-mode-button-area {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
        height: auto !important;
    }
    </style>
    <div class="print-mode-button-area no-print">
    """, unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("🔙 대시보드로 복귀", type="secondary"):
            st.session_state['print_mode'] = False
            st.rerun()
    with col_btn2:
        if st.button("🖨️ 인쇄/PDF 저장", type="primary"):
            print_script = """
            <script>
            setTimeout(function() {
                window.print();
            }, 500);
            </script>
            """
            st.components.v1.html(print_script, height=0, width=0)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    selected_week = st.session_state.get('selected_week_for_print', st.session_state.get('week_select', list(WEEK_MAP.keys())[0]))

# 데이터 로드
(cur_uv, cur_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
 df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
 df_top10, df_raw_all, new_ratio, search_ratio, active_article_count, published_article_count, 
 df_top10_sources, df_published_top10, df_published_all_week, visitor_24h, visitor_48h) = data.load_all_dashboard_data(selected_week)

# 기자별 데이터 생성 (본명 기준, 필명 기준)
writers_df_real, writers_df_pen = data.get_writers_df_real(df_published_all_week if not df_published_all_week.empty else df_top10)

# 발행기사 수 보정
if not df_published_all_week.empty:
    published_article_count = len(df_published_all_week)

# 뷰 렌더링
if st.session_state['print_mode']:
    # [인쇄 모드] - 모든 섹션을 순차적으로 표시
    st.markdown("""
    <style>
    .print-preview-layout { margin-top: 0 !important; padding-top: 0 !important; }
    .stButton { display: none !important; }
    .print-preview-layout > *:first-child { margin-top: 0 !important; padding-top: 0 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="print-preview-layout">', unsafe_allow_html=True)
    
    # 1~7 섹션 순차 렌더링
    views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count)
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_traffic(df_traffic_curr, df_traffic_last)
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_demo_region(df_region_curr, df_region_last)
    st.markdown('---')
    views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last)
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_top10_detail(df_top10, df_published_top10)
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_top10_trends(df_top10, df_top10_sources)
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    # 6. 카테고리별 분석
    views.render_category(df_published_all_week if not df_published_all_week.empty else df_top10)
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    # 7. 기자별 분석 (본명 + 필명 통합 섹션 호출)
    views.render_writer_analysis(writers_df_real, writers_df_pen)
    
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # [일반 모드] 탭 정의
    tabs = st.tabs(["1.성과요약", "2.접근경로", "3.방문자특성", "4.Top10상세", "5.Top10추이", "6.카테고리", "7.기자별분석"])
    
    with tabs[0]: views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count)
    with tabs[1]: views.render_traffic(df_traffic_curr, df_traffic_last)
    with tabs[2]: 
        views.render_demo_region(df_region_curr, df_region_last)
        st.markdown("---")
        views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last)
    with tabs[3]: views.render_top10_detail(df_top10, df_published_top10)
    with tabs[4]: views.render_top10_trends(df_top10, df_top10_sources)
    with tabs[5]: 
        target_df = df_published_all_week if not df_published_all_week.empty else df_top10
        views.render_category(target_df)
    with tabs[6]: 
        # 통합된 7번 탭 내에서 본명/필명 순위 각각 출력
        views.render_writer_analysis(writers_df_real, writers_df_pen)
