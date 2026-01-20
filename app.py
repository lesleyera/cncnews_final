# app.py
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime

# 내부 모듈
import config
import auth
import data
import views
from utils import WEEK_MAP


# =====================================================
# 1. 페이지 기본 설정
# =====================================================
st.set_page_config(
    layout="wide",
    page_title="쿡앤셰프 주간 성과보고서",
)


# =====================================================
# 2. 프린트(A4) 전용 CSS
# =====================================================
st.markdown("""
<style>

/* ===============================
   공통
================================ */
html, body {
    font-family: Pretendard, Apple SD Gothic Neo, sans-serif;
}

/* ===============================
   프린트 전용 스타일
================================ */
@media print {

    /* A4 페이지 설정 */
    @page {
        size: A4 portrait;
        margin: 18mm 15mm 20mm 15mm;
    }

    /* 페이지 강제 분리 */
    .page-break {
        page-break-before: always;
        break-before: page;
    }

    /* 그래프/컨텐츠 잘림 방지 */
    section, div, article {
        break-inside: avoid;
        page-break-inside: avoid;
    }

    /* Streamlit UI 제거 */
    header, footer, nav {
        display: none !important;
    }

    .stTabs [role="tablist"] {
        display: none !important;
    }

    /* 프린트 제외 */
    .no-print {
        display: none !important;
    }

    /* 제목 스타일 */
    h1, h2, h3 {
        margin-top: 0;
        padding-top: 0;
    }
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# 3. 공통 헬퍼 (페이지 단위 섹션)
# =====================================================
def print_section(title: str):
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    st.header(title)


# =====================================================
# 4. 인증
# =====================================================
auth.login_required()


# =====================================================
# 5. 데이터 로드
# =====================================================
(
    df_weekly,
    df_daily,
    df_traffic_curr,
    df_traffic_last,
    df_region_curr,
    df_region_last,
    df_age_curr,
    df_age_last,
    df_gender_curr,
    df_gender_last,
    df_top10,
    df_top10_sources,
    writers_df,
    cur_pv,
    cur_uv,
    pv_ratio,
    uv_ratio,
    active_article_count,
    published_article_count,
) = data.load_all()


# =====================================================
# 6. 상단 제목
# =====================================================
today = datetime.now().strftime("%Y.%m.%d")
st.title("쿡앤셰프 주간 성과 보고서")
st.caption(f"보고서 생성일: {today}")


# =====================================================
# 7. 탭 구성
# =====================================================
tabs = st.tabs([
    "주간 요약",
    "트래픽 분석",
    "인구통계",
    "TOP10 상세",
    "TOP10 트렌드",
    "카테고리 분석",
    "작가 분석(실명)",
    "작가 분석(필명)",
])


# =====================================================
# 8. 탭별 콘텐츠 (페이지 강제 분리 적용)
# =====================================================
with tabs[0]:
    print_section("1. 주간 성과 요약")
    views.render_summary(
        df_weekly,
        cur_pv,
        cur_uv,
        pv_ratio,
        uv_ratio,
        df_daily,
        active_article_count,
        published_article_count,
    )


with tabs[1]:
    print_section("2. 트래픽 분석")
    views.render_traffic(df_traffic_curr, df_traffic_last)


with tabs[2]:
    print_section("3. 인구통계 분석")
    views.render_demo_region(df_region_curr, df_region_last)
    st.markdown("---")
    views.render_demo_age_gender(
        df_age_curr,
        df_age_last,
        df_gender_curr,
        df_gender_last,
    )


with tabs[3]:
    print_section("4. TOP10 콘텐츠 상세")
    views.render_top10_detail(df_top10)


with tabs[4]:
    print_section("5. TOP10 트렌드 분석")
    views.render_top10_trends(df_top10, df_top10_sources)


with tabs[5]:
    print_section("6. 카테고리별 성과 분석")
    views.render_category(df_top10)


with tabs[6]:
    print_section("7. 작가 성과 분석 (실명)")
    views.render_writer_real(writers_df)


with tabs[7]:
    print_section("8. 작가 성과 분석 (필명)")
    views.render_writer_pen(writers_df)


# =====================================================
# 9. 하단 주석 (프린트 제외)
# =====================================================
st.markdown(
    """
    <div class="footer-note no-print">
    ※ 본 보고서는 쿡앤셰프(Cook&Chef) 홈페이지 및 애널리틱스 데이터를 기반으로 자동 생성되었습니다.
    </div>
    """,
    unsafe_allow_html=True
)
