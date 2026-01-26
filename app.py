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

# 상단 헤더 영역
c1, c2 = st.columns([2, 1])
with c1: 
    st.markdown('<div class="report-title">📰 쿡앤셰프 주간 성과보고서</div>', unsafe_allow_html=True)

with c2:
    col_btn1, col_btn2 = st.columns(2)
    # PDF 저장 버튼 (인쇄 미리보기 제거, 바로 PDF 저장)
    if st.session_state['print_mode']:
        if col_btn1.button("🔙 대시보드로 복귀", type="secondary"):
            st.session_state['print_mode'] = False
            st.rerun()
        if col_btn2.button("📄 PDF로 저장", type="primary"):
            # PDF 저장을 위한 JavaScript
            pdf_save_script = """
            <script>
            (function() {
                function generatePDF() {
                    // html2pdf.js가 로드될 때까지 대기
                    if (typeof html2pdf === 'undefined') {
                        setTimeout(generatePDF, 100);
                        return;
                    }
                    
                    const element = document.querySelector('.print-preview-layout');
                    if (!element) {
                        alert('PDF로 저장할 내용을 찾을 수 없습니다.');
                        return;
                    }
                    
                    const opt = {
                        margin: [15, 10, 15, 10],
                        filename: '쿡앤셰프_주간성과보고서.pdf',
                        image: { type: 'jpeg', quality: 0.98 },
                        html2canvas: { 
                            scale: 2, 
                            useCORS: true,
                            logging: false,
                            letterRendering: true,
                            windowWidth: element.scrollWidth,
                            windowHeight: element.scrollHeight
                        },
                        jsPDF: { 
                            unit: 'mm', 
                            format: 'a4', 
                            orientation: 'landscape'
                        }
                    };
                    
                    html2pdf().set(opt).from(element).save().catch(function(err) {
                        console.error('PDF 생성 오류:', err);
                        alert('PDF 저장 중 오류가 발생했습니다: ' + err.message);
                    });
                }
                
                // 약간의 지연 후 실행 (DOM 준비 대기)
                setTimeout(generatePDF, 300);
            })();
            </script>
            """
            st.components.v1.html(pdf_save_script, height=0, width=0)
    else:
        # 일반 모드에서 바로 PDF 저장 버튼 표시
        if col_btn2.button("📄 PDF로 저장", type="primary"):
            # 모든 탭 내용을 포함한 컨테이너를 PDF로 저장
            pdf_save_script = """
            <script>
            (function() {
                function generatePDF() {
                    // html2pdf.js가 로드될 때까지 대기
                    if (typeof html2pdf === 'undefined') {
                        setTimeout(generatePDF, 100);
                        return;
                    }
                    
                    // 모든 탭 컨텐츠를 포함하는 컨테이너 찾기
                    const mainContainer = document.querySelector('.block-container');
                    if (!mainContainer) {
                        alert('PDF로 저장할 내용을 찾을 수 없습니다.');
                        return;
                    }
                    
                    // PDF 저장용 임시 컨테이너 생성
                    const pdfContainer = document.createElement('div');
                    pdfContainer.className = 'pdf-export-wrapper';
                    pdfContainer.style.cssText = 'position: absolute; left: -9999px; width: 297mm; background: white; padding: 20px; font-family: Pretendard, sans-serif;';
                    
                    // 헤더 영역 복사
                    const reportTitle = mainContainer.querySelector('.report-title');
                    const periodInfo = mainContainer.querySelector('.period-info');
                    const updateTime = mainContainer.querySelector('.update-time');
                    
                    if (reportTitle) {
                        const titleDiv = document.createElement('div');
                        titleDiv.innerHTML = reportTitle.outerHTML;
                        pdfContainer.appendChild(titleDiv);
                    }
                    
                    if (periodInfo) {
                        pdfContainer.appendChild(periodInfo.cloneNode(true));
                    }
                    
                    if (updateTime) {
                        pdfContainer.appendChild(updateTime.cloneNode(true));
                    }
                    
                    // 탭 버튼에서 섹션 제목 가져오기
                    const tabButtons = mainContainer.querySelectorAll('[data-testid="stTabs"] button[role="tab"]');
                    const tabTitles = Array.from(tabButtons).map(btn => btn.textContent.trim());
                    
                    // 모든 탭 컨텐츠 복사 (숨겨진 탭도 포함)
                    const tabPanels = mainContainer.querySelectorAll('[data-testid="stTabs"] [role="tabpanel"]');
                    tabPanels.forEach(function(tab, index) {
                        // 페이지 브레이크 추가 (첫 번째 섹션 제외)
                        if (index > 0) {
                            const pageBreak = document.createElement('div');
                            pageBreak.style.cssText = 'page-break-before: always;';
                            pdfContainer.appendChild(pageBreak);
                        }
                        
                        // 섹션 헤더 추가
                        const sectionHeader = document.createElement('div');
                        sectionHeader.className = 'section-header-container';
                        sectionHeader.style.cssText = 'margin-top: 30px; margin-bottom: 25px; padding: 15px 25px; background-color: #fffcf7; border-left: 8px solid #1a237e; border-radius: 4px;';
                        const headerText = document.createElement('div');
                        headerText.className = 'section-header';
                        headerText.style.cssText = 'font-size: 1.8rem; font-weight: 800; color: #1a237e; margin: 0;';
                        headerText.textContent = tabTitles[index] || ('섹션 ' + (index + 1));
                        sectionHeader.appendChild(headerText);
                        pdfContainer.appendChild(sectionHeader);
                        
                        // 탭 내용 복사
                        const tabContent = tab.cloneNode(true);
                        tabContent.style.display = 'block';
                        tabContent.style.visibility = 'visible';
                        // 숨김 스타일 제거
                        tabContent.style.height = 'auto';
                        tabContent.style.overflow = 'visible';
                        pdfContainer.appendChild(tabContent);
                    });
                    
                    document.body.appendChild(pdfContainer);
                    
                    const opt = {
                        margin: [15, 10, 15, 10],
                        filename: '쿡앤셰프_주간성과보고서.pdf',
                        image: { type: 'jpeg', quality: 0.98 },
                        html2canvas: { 
                            scale: 2, 
                            useCORS: true,
                            logging: false,
                            letterRendering: true,
                            windowWidth: pdfContainer.scrollWidth,
                            windowHeight: pdfContainer.scrollHeight,
                            scrollX: 0,
                            scrollY: 0
                        },
                        jsPDF: { 
                            unit: 'mm', 
                            format: 'a4', 
                            orientation: 'landscape'
                        }
                    };
                    
                    html2pdf().set(opt).from(pdfContainer).save().then(function() {
                        if (pdfContainer.parentNode) {
                            document.body.removeChild(pdfContainer);
                        }
                    }).catch(function(err) {
                        console.error('PDF 생성 오류:', err);
                        alert('PDF 저장 중 오류가 발생했습니다: ' + err.message);
                        if (pdfContainer.parentNode) {
                            document.body.removeChild(pdfContainer);
                        }
                    });
                }
                
                // 약간의 지연 후 실행 (DOM 준비 대기)
                setTimeout(generatePDF, 1000);
            })();
            </script>
            """
            st.components.v1.html(pdf_save_script, height=0, width=0)
        
    if not st.session_state['print_mode']:
        selected_week = st.selectbox("📅 조회 주차", list(WEEK_MAP.keys()), key="week_select", label_visibility="collapsed")
        st.session_state['selected_week_for_print'] = selected_week
    else:
        selected_week = st.session_state.get('selected_week_for_print', st.session_state.get('week_select', list(WEEK_MAP.keys())[0]))

st.markdown(f'<div class="period-info">📅 조회 기간: {WEEK_MAP[selected_week]}</div>', unsafe_allow_html=True)
st.markdown(f"<div class='update-time'>최종 집계: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>", unsafe_allow_html=True)

# 데이터 로드
# [수정] data.py에서 반환하는 published_article_count, df_published_top10 추가 수신 (총 20개 항목)
(cur_uv, cur_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
 df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
 df_top10, df_raw_all, new_ratio, search_ratio, active_article_count, published_article_count, df_top10_sources, df_published_top10) = data.load_all_dashboard_data(selected_week)

# 기자별 데이터 생성 (본명 기준)
writers_df = data.get_writers_df_real(df_top10)

# 발행기사 수를 카테고리별 기사 수와 연동 (df_top10의 기사 수 사용)
if not df_top10.empty:
    published_article_count = len(df_top10)

# 뷰 렌더링
if st.session_state['print_mode']:
    # [인쇄 모드]    
    st.markdown('<div class="print-preview-layout">', unsafe_allow_html=True)
    
    views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count)
    st.markdown("<br>", unsafe_allow_html=True)
    views.render_traffic(df_traffic_curr, df_traffic_last)
    
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_demo_region(df_region_curr, df_region_last)
    
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last)
    
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_top10_detail(df_top10, df_published_top10)
    st.markdown("<br>", unsafe_allow_html=True)
    # [수정] df_top10_sources 인자 추가
    views.render_top10_trends(df_top10, df_top10_sources)
    
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_category(df_top10)
    
    st.markdown('<div class="page-break"></div>', unsafe_allow_html=True)
    
    views.render_writer_analysis(writers_df)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 페이지 번호 추가를 위한 JavaScript
    page_number_script = """
    <script>
    (function() {
        function addPageNumbers() {
            const sections = document.querySelectorAll('.section-header-container');
            const totalPages = sections.length;
            
            sections.forEach((section, index) => {
                // 기존 페이지 번호 제거
                const existing = section.parentElement.querySelector('.page-number');
                if (existing) existing.remove();
                
                // 페이지 번호 추가
                const pageNum = document.createElement('div');
                pageNum.className = 'page-number';
                pageNum.textContent = (index + 1) + ' / ' + totalPages;
                pageNum.style.cssText = 'position: fixed; bottom: 3mm; left: 50%; transform: translateX(-50%); font-size: 9pt; color: #666; z-index: 9999;';
                
                // 섹션의 부모 컨테이너 찾기
                let container = section.closest('[data-testid="stVerticalBlock"]');
                if (!container) container = section.parentElement;
                
                if (container) {
                    container.style.position = 'relative';
                    container.appendChild(pageNum);
                }
            });
        }
        
        // 페이지 로드 시 실행
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', addPageNumbers);
        } else {
            addPageNumbers();
        }
        
        // 인쇄 전 실행
        window.addEventListener('beforeprint', addPageNumbers);
    })();
    </script>
    """
    st.markdown(page_number_script, unsafe_allow_html=True) 

else:
    # [일반 모드]
    tabs = st.tabs(["1.성과요약", "2.접근경로", "3.방문자특성", "4.Top10상세", "5.Top10추이", "6.카테고리", "7.기자별분석"])
    
    with tabs[0]: views.render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count)
    with tabs[1]: views.render_traffic(df_traffic_curr, df_traffic_last)
    with tabs[2]: 
        views.render_demo_region(df_region_curr, df_region_last)
        st.markdown("---")
        views.render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last)
    with tabs[3]: views.render_top10_detail(df_top10, df_published_top10)
    # [수정] df_top10_sources 인자 추가
    with tabs[4]: views.render_top10_trends(df_top10, df_top10_sources)
    with tabs[5]: 
        category_count = views.render_category(df_top10)
        # 카테고리별 기사 수로 발행기사 수 업데이트
        if category_count > 0:
            published_article_count = category_count
    with tabs[6]: views.render_writer_analysis(writers_df)

st.markdown('<div class="footer-note no-print">※ 본 보고서는 쿡앤셰프(Cook&Chef) 홈페이지 및 애널리틱스 데이터를 활용하여 구성하였습니다.</div>', unsafe_allow_html=True)
