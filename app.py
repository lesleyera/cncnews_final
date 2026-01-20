# app.py
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

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

# 3. 보안 체크
if not auth.check_password():
    st.stop()

# =================================================================
# ▼ 메인 로직 시작 ▼
# =================================================================

# 세션 상태 초기화
if 'print_mode' not in st.session_state:
    st.session_state['print_mode'] = False

# 상단 헤더 영역
c1, c2 = st.columns([2, 1])
with c1: 
    st.markdown('<div class="report-title">📰 쿡앤셰프 주간 성과보고서</div>', unsafe_allow_html=True)

with c2:
    col_btn1, col_btn2 = st.columns(2)
    # 인쇄 모드 토글 버튼
    if st.session_state['print_mode']:
        if col_btn1.button("🔙 대시보드로 복귀", type="secondary"):
            st.session_state['print_mode'] = False
            st.rerun()
        if col_btn2.button("🖨️ 인쇄 실행", type="primary"):
            st.components.v1.html("<script>window.parent.print();</script>", height=0, width=0)
    else:
        if col_btn2.button("🖨️ 인쇄 미리보기", type="primary"):
            st.session_state['print_mode'] = True
            st.rerun()
        
    if not st.session_state['print_mode']:
        selected_week = st.selectbox("📅 조회 주차", list(WEEK_MAP.keys()), key="week_select", label_visibility="collapsed")
        st.session_state['selected_week_for_print'] = selected_week
    else:
        selected_week = st.session_state.get('selected_week_for_print', st.session_state.get('week_select', list(WEEK_MAP.keys())[0]))

st.markdown(f'<div class="period-info">📅 조회 기간: {WEEK_MAP[selected_week]}</div>', unsafe_allow_html=True)
st.markdown(f"<div class='update-time'>최종 집계: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

# 데이터 로드
(cur_uv, cur_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
 df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
 df_top10, df_raw_all, new_ratio, search_ratio, active_article_count, df_top10_sources) = data.load_all_dashboard_data(selected_week)

# 기자별 데이터 생성
writers_df = data.get_writers_df_real(df_top10)

# 발행 기사 수 계산
published_article_count = 0
if not writers_df.empty and '기사수' in writers_df.columns:
    published_article_count = writers_df['기사수'].sum()

# 뷰 렌더링
if st.session_state['print_mode']:
    # [인쇄 모드] - 물리적으로 div를 찢어서 페이지 분리
    st.markdown('<div class="print-preview-layout">', unsafe_allow_html=True)
    
    # 1. 성과 요약 (첫 페이지)
    views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count)
    
    # 2. 접근 경로 (여기서부터 강제 분리)
    st.markdown('<div style="page-break-before: always;"></div>', unsafe_allow_html=True)
    views.render_traffic(df_traffic_curr, df_traffic_last)
    
    # 3-1. 지역 분석
    st.markdown('<div style="page-break-before: always;"></div>', unsafe_allow_html=True)
    views.render_demo_region(df_region_curr, df_region_last)
    
    # 3-2. 연령/성별 분석
    st.markdown('<div style="page-break-before: always;"></div>', unsafe_allow_html=True)
    views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last)
    
    # 4 & 5. TOP10 상세 및 추이 (하나의 논리적 묶음)
    st.markdown('<div style="page-break-before: always;"></div>', unsafe_allow_html=True)
    views.render_top10_detail(df_top10)
    st.markdown("<br>", unsafe_allow_html=True)
    views.render_top10_trends(df_top10, df_top10_sources)
    
    # 6. 카테고리별 분석
    st.markdown('<div style="page-break-before: always;"></div>', unsafe_allow_html=True)
    views.render_category(df_top10)
    
    # 7 & 8. 기자별 분석 (7번과 8번은 한 페이지에 묶음)
    st.markdown('<div style="page-break-before: always;"></div>', unsafe_allow_html=True)
    views.render_writer_real(writers_df)
    st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True) # 구분용 여백
    views.render_writer_pen(writers_df)
    
    st.markdown('</div>', unsafe_allow_html=True) 

else:
    # [일반 모드]
    tabs = st.tabs(["1.성과요약", "2.접근경로", "3.방문자특성", "4.Top10상세", "5.Top10추이", "6.카테고리", "7.기자(본명)", "8.기자(필명)"])
    
    with tabs[0]: views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count)
    with tabs[1]: views.render_traffic(df_traffic_curr, df_traffic_last)
    with tabs[2]: 
        views.render_demo_region(df_region_curr, df_region_last)
        st.markdown("---")
        views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last)
    with tabs[3]: views.render_top10_detail(df_top10)
    with tabs[4]: views.render_top10_trends(df_top10, df_top10_sources)
    with tabs[5]: views.render_category(df_top10)
    with tabs[6]: views.render_writer_real(writers_df)
    with tabs[7]: views.render_writer_pen(writers_df)

st.markdown('<div class="footer-note no-print">※ 본 보고서는 쿡앤셰프(Cook&Chef) 홈페이지 및 애널리틱스 데이터를 활용하여 구성하였습니다.</div>', unsafe_allow_html=True)
