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
/* 표 스크롤 제거 - 데이터가 있는 모든 행 표시 */
[data-testid="stDataFrame"] {{
    max-height: none !important;
    overflow: visible !important;
}}
[data-testid="stDataFrame"] > div {{
    max-height: none !important;
    overflow: visible !important;
    height: auto !important;
}}
[data-testid="stDataFrame"] > div > div {{
    max-height: none !important;
    overflow: visible !important;
    height: auto !important;
}}
[data-testid="stDataFrame"] table {{
    display: table !important;
}}
.footer-note {{ font-size: 1rem; color: #78909c; margin-top: 50px; border-top: 1px solid #eceff1; padding-top: 15px; text-align: center; }}

/* 인쇄 미리보기 모드에서 모든 콘텐츠 표시 */
.print-preview-layout {{
    position: relative;
    width: 100%;
    min-height: 100vh;
}}

.print-preview-layout * {{
    visibility: visible !important;
}}

.print-preview-layout [data-testid="stTabs"] {{
    display: block !important;
}}

.print-preview-layout [data-testid="stTabs"] [role="tabpanel"] {{
    display: block !important;
    visibility: visible !important;
    height: auto !important;
    overflow: visible !important;
    opacity: 1 !important;
}}
</style>
"""

# 인쇄용 CSS (가로보기, 여백 상하 15mm/좌우 10mm, 섹션별 강제 분할 최적화)
PRINT_CSS = """
<style>
@media print {
    /* 페이지 설정: A4 가로, 여백 상하 15mm/좌우 10mm */
    @page {
        size: A4 landscape;
        margin-top: 15mm !important;
        margin-bottom: 20mm !important;
        margin-left: 10mm !important;
        margin-right: 10mm !important;
    }
    
    body { 
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        background-color: white !important;
    }

    /* 2. 안내 문구 및 불필요 UI 숨김 */
    .no-print, .stButton, header, footer, 
    [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"],
    .stAlert, [data-testid="stNotification"], .footer-note,
    .report-title, .period-info, .update-time,
    .print-mode-button-area,
    [class*="stButton"],
    [data-testid="stButton"] { 
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        visibility: hidden !important;
    }
    
    /* 3. 섹션 강제 분할 - 각 섹션을 독립 페이지로 */
    .section-header-container { 
        display: block !important;
        break-before: page !important;
        page-break-before: always !important;
        margin-top: 0 !important;
        padding-top: 10mm !important;
    }

    /* 첫 번째 섹션은 넘김 제외 */
    .print-preview-layout .section-header-container:first-of-type {
        break-before: auto !important;
        page-break-before: auto !important;
        padding-top: 0 !important;
    }

    /* 4. page-break 마커 처리 */
    .page-break {
        break-after: page !important;
        page-break-after: always !important;
    }

    /* 5. 콘텐츠 레이아웃 최적화 */
    .block-container {
        max-width: 100% !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    
    /* 인쇄 모드에서 버튼 영역 완전히 제거 */
    .stButton,
    [class*="stButton"],
    [data-testid="stButton"] {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* 인쇄 모드에서 첫 번째 섹션이 페이지 상단에서 시작 */
    .print-preview-layout {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    .print-preview-layout .section-header-container:first-of-type {
        margin-top: 0 !important;
        padding-top: 0 !important;
        break-before: auto !important;
        page-break-before: auto !important;
    }

    /* 6. 테이블 및 차트 분할 방지 */
    [data-testid="stDataFrame"], .js-plotly-plot, .stPlotlyChart {
        width: 100% !important;
        page-break-inside: avoid !important;
        break-inside: avoid !important;
    }
    
    /* 7. 테이블 행 분할 방지 및 번호 기준 분할 */
    [data-testid="stDataFrame"] tbody tr {
        page-break-inside: avoid !important;
        break-inside: avoid !important;
    }
    
    /* 8. 테이블이 페이지를 넘어갈 경우 처리 */
    [data-testid="stDataFrame"] table {
        page-break-inside: auto !important;
    }
    
    [data-testid="stDataFrame"] thead {
        display: table-header-group !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:first-child {
        page-break-before: avoid !important;
    }
    
    /* 9. 리스트 항목 분할 방지 */
    ul, ol {
        page-break-inside: avoid !important;
    }
    
    li {
        page-break-inside: avoid !important;
    }
    
    /* 10. 페이지 번호 표시 영역 */
    .page-number {
        position: fixed;
        bottom: 3mm;
        left: 50%;
        transform: translateX(-50%);
        font-size: 9pt;
        color: #666;
        z-index: 9999;
    }
    
    /* 11. 각 섹션 컨테이너에 페이지 번호 공간 확보 */
    .print-preview-layout [data-testid="stVerticalBlock"] {
        position: relative;
        page-break-inside: avoid !important;
        break-inside: avoid !important;
    }
    
    /* 인쇄 모드에서 모든 콘텐츠 표시 */
    .print-preview-layout {
        display: block !important;
        visibility: visible !important;
    }
    
    .print-preview-layout * {
        visibility: visible !important;
        display: block !important;
    }
    
    .print-preview-layout [data-testid="stDataFrame"],
    .print-preview-layout .js-plotly-plot,
    .print-preview-layout .stPlotlyChart {
        display: block !important;
        visibility: visible !important;
    }
    
    /* 12. 하단 푸터 숨김 */
    .print-footer {
        display: none !important;
    }
}

/* 인쇄 미리보기용 스타일 (화면 표시용) */
.print-preview-layout {
    position: relative;
    width: 100%;
    min-height: 100vh;
    display: block !important;
    margin-top: 0 !important;
    padding-top: 0 !important;
}

/* 인쇄 미리보기 모드에서 모든 콘텐츠 표시 */
.print-preview-layout * {
    visibility: visible !important;
}

.print-preview-layout [data-testid="stTabs"] {
    display: block !important;
}

.print-preview-layout [data-testid="stTabs"] [role="tabpanel"] {
    display: block !important;
    visibility: visible !important;
    height: auto !important;
    overflow: visible !important;
}

/* 인쇄 미리보기에서 헤더와 버튼 숨김 */
.print-preview-layout ~ .report-title,
.print-preview-layout ~ .period-info,
.print-preview-layout ~ .update-time,
.print-preview-layout ~ .stButton,
.print-preview-layout ~ [class*="stButton"] {
    display: none !important;
}

/* 인쇄 미리보기에서 첫 번째 섹션이 상단에서 시작 */
.print-preview-layout .section-header-container:first-of-type {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

/* 인쇄 미리보기에서 block-container padding 제거 */
.print-preview-layout ~ .block-container {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
</style>
"""
