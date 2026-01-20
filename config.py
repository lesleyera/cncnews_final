# config.py
# ----------------- 설정 및 스타일 정의 -----------------

# GA4 속성 ID
PROPERTY_ID = "370663478"

# 색상 팔레트
COLOR_NAVY = "#1a237e"
COLOR_RED = "#d32f2f"
COLOR_GREY = "#78909c"
COLOR_BG_ACCENT = "#fffcf7"
CHART_PALETTE = [COLOR_NAVY, COLOR_RED, "#5c6bc0", "#ef5350", "#8d6e63", COLOR_GREY]
COLOR_GENDER = {'여성': '#d32f2f', '남성': '#1a237e'}

# 기본 화면 CSS
CSS = f"""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css');
body {{ background-color: #ffffff; font-family: 'Pretendard', sans-serif; color: #263238; }}

/* 헤더 및 툴바 숨김 */
header[data-testid="stHeader"] {{ visibility: hidden !important; }}
[data-testid="stToolbar"] {{ visibility: hidden !important; }}
.block-container {{ padding-top: 2rem !important; padding-bottom: 5rem; max_width: 1600px; }}
[data-testid="stSidebar"] {{ background-color: #f8f9fa; }}

/* 타이틀 및 섹션 헤더 */
.report-title {{ font-size: 28px; font-weight: 800; color: {COLOR_NAVY}; margin-bottom: 20px; }}
.section-header-container {{ margin-top: 30px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid {COLOR_NAVY}; }}
.section-header {{ font-size: 20px; font-weight: 700; color: {COLOR_NAVY}; }}

/* 메트릭 카드 */
.metric-container {{ background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 20px; text-align: center; }}
.metric-label {{ font-size: 14px; color: {COLOR_GREY}; margin-bottom: 5px; }}
.metric-value {{ font-size: 24px; font-weight: 700; color: {COLOR_NAVY}; }}
.metric-delta {{ font-size: 14px; margin-top: 5px; }}

/* 데이터프레임 스타일 */
.stDataFrame {{ border: 1px solid #e0e0e0; border-radius: 8px; }}

/* 푸터 */
.print-footer {{ display: none; }}
</style>
"""

# 인쇄용 CSS (탭당 1페이지 구성 및 여백 설정)
PRINT_CSS = """
<style>
/* 1. 화면 미리보기용 설정 */
.print-preview-layout {
    width: 100%;
    margin: 0 auto;
}

@media print {
    /* 2. 페이지 설정: A4 가로, 여백 10mm */
    @page { 
        size: A4 landscape; 
        margin: 10mm 10mm 10mm 10mm; 
    }
    
    body { 
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    /* 3. 숨김 처리 */
    .no-print, .stButton, header, footer, [data-testid="stSidebar"], [data-testid="stHeader"] { 
        display: none !important; 
    }
    
    /* 4. 섹션별 강제 페이지 넘김 (1탭 1페이지) */
    .section-header-container { 
        page-break-before: always !important; 
        break-before: page !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* 첫 번째 섹션은 페이지 넘김 제외 */
    div:first-child > .section-header-container {
        page-break-before: auto !important;
        break-before: auto !important;
    }

    /* 차트 및 테이블 크기 조정 */
    .js-plotly-plot { width: 100% !important; }
    
    .print-footer { 
        display: block !important; 
        position: fixed; 
        bottom: 0; 
        width: 100%; 
        font-size: 10px; 
        color: #999; 
        text-align: center;
        border-top: 1px solid #eee;
        padding-top: 5px;
    }
}

/* 화면에서도 섹션 구분을 위해 여백 추가 */
.section-header-container {
    margin-top: 50px !important;
}
</style>
"""
