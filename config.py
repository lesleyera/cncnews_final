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
[data-testid="stSidebar"] {{ display: none; }}

/* 보고서 스타일 */
.report-title {{ font-size: 2.6rem; font-weight: 900; color: {COLOR_NAVY}; border-bottom: 4px solid {COLOR_RED}; padding-bottom: 15px; margin-top: 10px; }}
.period-info {{ font-size: 1.2rem; font-weight: 700; color: #455a64; margin-top: 10px; }}
.update-time {{ color: {COLOR_NAVY}; font-weight: 700; font-size: 1.3rem; text-align: right; margin-top: -15px; margin-bottom: 30px; font-family: monospace; }}
.kpi-container {{ background-color: #fff; border: 1px solid #eceff1; border-top: 5px solid {COLOR_RED}; border-radius: 8px; padding: 20px 10px; text-align: center; margin-bottom: 15px; height: 160px; display: flex; flex-direction: column; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }}
.kpi-label {{ font-size: 1.1rem; font-weight: 700; color: #455a64; margin-bottom: 8px; white-space: normal; line-height: 1.3; letter-spacing: -0.05em; }}
.kpi-value {{ font-size: 2.0rem; font-weight: 900; color: {COLOR_NAVY}; line-height: 1.1; letter-spacing: -0.03em; }}
.kpi-unit {{ font-size: 1.1rem; font-weight: 600; color: #90a4ae; margin-left: 3px; }}
.section-header-container {{ margin-top: 30px; margin-bottom: 25px; padding: 15px 25px; background-color: {COLOR_BG_ACCENT}; border-left: 8px solid {COLOR_NAVY}; border-radius: 4px; }}
.section-header {{ font-size: 1.8rem; font-weight: 800; color: {COLOR_NAVY}; margin: 0; }}
.section-desc {{ font-size: 1.2rem; color: #546e7a; margin-top: 5px; }}
.sub-header {{ font-size: 1.3rem; font-weight: 700; color: {COLOR_NAVY}; margin-top: 30px; margin-bottom: 10px; padding-left: 10px; border-left: 4px solid {COLOR_RED}; }}
.chart-header {{ font-size: 1.2rem; font-weight: 700; color: {COLOR_NAVY}; margin-top: 30px; margin-bottom: 10px; border-left: 4px solid {COLOR_RED}; padding-left: 10px; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 0px; border-bottom: 2px solid #cfd8dc; display: flex; width: 100%; }}
.stTabs [data-baseweb="tab"] {{ height: 60px; background-color: #f7f9fa; border-right: 1px solid #eceff1; color: #607d8b; font-weight: 700; font-size: 1.3rem; flex-grow: 1; text-align: center; }}
.stTabs [aria-selected="true"] {{ background-color: #fff; color: {COLOR_RED}; border-bottom: 4px solid {COLOR_RED}; }}
[data-testid="stDataFrame"] thead th {{ background-color: {COLOR_NAVY} !important; color: white !important; font-size: 1.2rem !important; font-weight: 600 !important; }}
.footer-note {{ font-size: 1rem; color: #78909c; margin-top: 50px; border-top: 1px solid #eceff1; padding-top: 15px; text-align: center; }}
</style>
"""

# 인쇄용 CSS
PRINT_CSS = """
<style>
/* 1. 화면 미리보기용 */
.print-preview-layout {
    width: 100%;
    margin: 0 auto;
}

@media print {
    /* 2. 페이지 설정: A4 가로, 여백 10mm */
    @page { 
        size: A4 landscape; 
        margin: 10mm; 
    }
    
    body { 
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        background-color: white !important;
    }

    /* 3. 숨김 처리 */
    .no-print, .stButton, header, footer, [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"] { 
        display: none !important; 
    }
    
    /* 4. 섹션별 강제 페이지 넘김 (1탭 1페이지) */
    .section-header-container { 
        page-break-before: always !important; 
        break-before: page !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* 첫 번째 섹션 제외 */
    div:first-child > .section-header-container {
        page-break-before: auto !important;
        break-before: auto !important;
    }

    /* 5. 콘텐츠 확장 */
    .block-container {
        max-width: 100% !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    [data-testid="stDataFrame"], .js-plotly-plot {
        width: 100% !important;
    }
    
    /* 6. 인쇄용 푸터 영역 숨김 (문구 삭제) */
    .print-footer { 
        display: none !important; 
    }
}
</style>
"""
