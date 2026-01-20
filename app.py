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

# 2. 스타일 적용 (config 기반 + 물리적 페이징 스타일 추가)
st.markdown(config.CSS, unsafe_allow_html=True)
st.markdown(config.PRINT_CSS, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* 1. 화면 미리보기용: 실제 A4 용지 뭉치처럼 보이게 설정 */
    @media screen {
        .print-mode-wrapper {
            background-color: #525659; /* PDF 뷰어 배경색 */
            padding: 50px 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 40px;
        }
        .page-sheet {
            background-color: white;
            width: 297mm;  /* A4 가로 */
            min-height: 210mm;
            padding: 15mm 20mm;
            box-shadow: 0 0 20px rgba(0,0,0,0.5);
            box-sizing: border-box;
            position: relative;
        }
        .page-number-footer {
            position: absolute;
            bottom: 10mm;
            right: 15mm;
            font-size: 12px;
            color: #999;
        }
    }
    
    /* 2. 인쇄 시 설정: 여백 제거 및 강제 페이지 절단 */
    @media print {
        .no-print { display: none !important; }
        .print-mode-wrapper { background: none; padding: 0; gap: 0; }
        .page-sheet { 
            width: 297mm !important; 
            min-height: 210mm !important; 
            padding: 0; 
            margin: 0; 
            box-shadow: none; 
            page-break-after: always !important; 
            break-after: page !important;
            display: block !important;
        }
        .page-number-footer { display: block !important; }
    }
    </style>
""", unsafe_allow_html=True)

# 3. 보안 체크
if not auth.check_password():
    st.stop()

# 세션 상태 초기화
if 'print_mode' not in st.session_state:
    st.session_state['print_mode'] = False

# 상단 헤더 및 컨트롤 영역 (no-print)
with st.container():
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1: 
        st.markdown('<div class="report-title">📰 쿡앤셰프 주간 성과보고서</div>', unsafe_allow_html=True)
    with c2:
        col_btn1, col_btn2 = st.columns(2)
        if st.session_state['print_mode']:
            if col_btn1.button("🔙 대시보드 복귀", type="secondary"):
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
        selected_week = st.session_state.get('selected_week_for_print', list(WEEK_MAP.keys())[0])

    st.markdown(f'<div class="period-info">📅 조회 기간: {WEEK_MAP[selected_week]}</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='update-time'>최종 집계: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 4. 데이터 로드 (원본 인자 유지)
(cur_uv, cur_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
 df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
 df_top10, df_raw_all, new_ratio, search_ratio, active_article_count, df_top10_sources) = data.load_all_dashboard_data(selected_week)

writers_df = data.get_writers_df_real(df_top10)
published_article_count = writers_df['기사수'].sum() if not writers_df.empty and '기사수' in writers_df.columns else 0

# 5. 렌더링 로직
if st.session_state['print_mode']:
    # [인쇄 모드] 물리적인 페이지 시트 단위로 호출
    st.markdown('<div class="print-mode-wrapper">', unsafe_allow_html=True)
    
    # 각 페이지 정의 (함수, 페이지 번호)
    report_pages = [
        (lambda: views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count), "1"),
        (lambda: views.render_traffic(df_traffic_curr, df_traffic_last), "2"),
        (lambda: views.render_demo_region(df_region_curr, df_region_last), "3"),
        (lambda: views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last), "4"),
        (lambda: (views.render_top10_detail(df_top10), st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True), views.render_top10_trends(df_top10, df_top10_sources)), "5"),
        (lambda: views.render_category(df_top10), "6"),
        (lambda: (views.render_writer_real(writers_df), st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True), views.render_writer_pen(writers_df)), "7")
    ]
    
    for page_func, page_num in report_pages:
        st.markdown(f'<div class="page-sheet" id="page-{page_num}">', unsafe_allow_html=True)
        page_func()  # 콘텐츠 삽입
        st.markdown(f'<div class="page-number-footer">Page {page_num}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) 

else:
    # [일반 모드] 기존 탭 구조
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
