# data.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import concurrent.futures
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Metric, RunReportRequest, OrderBy, FilterExpression, Filter
)

# 모듈 임포트
import config
from auth import get_ga4_client
from utils import WEEK_MAP, clean_author_name

# -----------------------------------------------------------------------------
# URL 정규화 함수
# -----------------------------------------------------------------------------
def normalize_page_path(page_path):
    """
    pagePath에서 쿼리 파라미터(? 이후)를 제거하고 정규화
    예: /article/view?idxno=1234&m=1 -> /article/view?idxno=1234
    """
    if not page_path or pd.isna(page_path):
        return page_path
    
    page_path = str(page_path)
    # ?가 있으면 쿼리 파라미터 추출
    if '?' in page_path:
        base_path, query = page_path.split('?', 1)
        # idxno 파라미터 추출 (기사 고유 ID)
        idxno_match = re.search(r'idxno=(\d+)', query)
        if idxno_match:
            # idxno만 유지하고 나머지 파라미터 제거
            return f"{base_path}?idxno={idxno_match.group(1)}"
        else:
            # idxno가 없으면 쿼리 파라미터 모두 제거
            return base_path
    return page_path

def extract_article_id(page_path):
    """
    pagePath에서 기사 고유 ID(idxno) 추출
    예: /article/view?idxno=1234 -> 1234
    """
    if not page_path or pd.isna(page_path):
        return None
    
    page_path = str(page_path)
    idxno_match = re.search(r'idxno=(\d+)', page_path)
    if idxno_match:
        return idxno_match.group(1)
    return None

# -----------------------------------------------------------------------------
# [설정] 본명-필명 매핑 데이터 (2025.12.31 기준)
# -----------------------------------------------------------------------------
AUTHOR_MAPPING_DATA = [
    {"본명": "오영호", "필명": "오영호"},
    {"본명": "이지헌", "필명": "이지헌"},
    {"본명": "이정호", "필명": "이정호"},
    {"본명": "김성은", "필명": "김성은"},
    {"본명": "송자은", "필명": "송자은"},
    {"본명": "허선", "필명": "허세인"},
    {"본명": "박현우", "필명": "박하늘"},
    {"본명": "이정호", "필명": "이준민"},
    {"본명": "홍정민", "필명": "홍지우"},
    {"본명": "김성은", "필명": "김세온"},
    {"본명": "조소현", "필명": "조서율"},
    {"본명": "송자은", "필명": "송채연"},
    {"본명": "심세은", "필명": "심예린"},
    {"본명": "정수연", "필명": "정서윤"},
    {"본명": "서진영", "필명": "서현민"},
    {"본명": "AI협력", "필명": "오요리"},
    {"본명": "AI협력", "필명": "제조리"},
    {"본명": "AI협력", "필명": "길라떼"},
    {"본명": "이경엽", "필명": "김병일"},
    {"본명": "이경엽", "필명": "노하빈"},
    {"본명": "이경엽", "필명": "민혜경"},
    {"본명": "이경엽", "필명": "이은지"},
    {"본명": "이경엽", "필명": "이경엽"},
    {"본명": "이경엽", "필명": "정영"},
    {"본명": "조용수", "필명": "김철호"},
    {"본명": "조용수", "필명": "마종수"},
    {"본명": "조용수", "필명": "박노석"},
    {"본명": "조용수", "필명": "안정미"},
    {"본명": "조용수", "필명": "유성욱"},
    {"본명": "조용수", "필명": "조용수"}
]

def run_ga4_report(start_date, end_date, dimensions, metrics, order_by_metric=None, limit=None, dimension_filter=None):
    client = get_ga4_client()
    if not client: return pd.DataFrame()
    
    order_bys = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)] if order_by_metric else []
    
    request_params = {
        "property": f"properties/{config.PROPERTY_ID}",
        "dimensions": [Dimension(name=d) for d in dimensions],
        "metrics": [Metric(name=m) for m in metrics],
        "date_ranges": [DateRange(start_date=start_date, end_date=end_date)],
        "order_bys": order_bys,
        "limit": limit if limit else 10000
    }
    if dimension_filter:
        request_params["dimension_filter"] = dimension_filter

    request = RunReportRequest(**request_params)
    
    try:
        response = client.run_report(request)
        data = []
        for row in response.rows:
            row_dict = {dimensions[i]: row.dimension_values[i].value for i in range(len(dimensions))}
            for i, met in enumerate(metrics):
                val = row.metric_values[i].value
                try:
                    if isinstance(val, str):
                        row_dict[met] = float(val) if '.' in val else int(val)
                    else:
                        row_dict[met] = float(val) if isinstance(val, float) else int(val)
                except (ValueError, TypeError):
                    row_dict[met] = 0
            data.append(row_dict)
        return pd.DataFrame(data)
    except: return pd.DataFrame(columns=dimensions + metrics)

@st.cache_data(ttl=86400)
def crawl_single_article_cached(url_path):
    """크롤링: 헤더 추가, 인코딩 보정, 하이브리드 파싱(DOM+텍스트패턴)"""
    full_url = f"http://www.cooknchefnews.com{url_path}"
    
    # [봇 차단 방지]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(full_url, headers=headers, timeout=3.0)
        # [한글 깨짐 방지]
        response.encoding = response.apparent_encoding 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reg_date = "-"
        author = "관리자"
        cat, subcat = "뉴스", "이슈"

        # ---------------------------------------------------------
        # 1. 작성자 & 발행일시 추출
        # ---------------------------------------------------------
        target_text = ""
        
        # [Priority 1] 정확한 DOM 경로 (.viewTitle > dl > dd)
        view_title_section = soup.select_one('.viewTitle')
        if view_title_section:
            dd_elem = view_title_section.select_one('dl dd')
            if dd_elem:
                target_text = dd_elem.get_text(separator=' ', strip=True)

        # [Priority 2] 실패 시 "기사승인" 키워드 전수 조사
        if "기사승인" not in target_text:
            fallback_elem = soup.find(string=re.compile("기사승인"))
            if fallback_elem:
                target_text = fallback_elem.parent.get_text(separator=' ', strip=True)

        # 파싱 ("쿡앤셰프 / 기사승인 : 2026-01-07 ...")
        if "기사승인" in target_text:
            parts = target_text.split("기사승인")
            
            # 1-1. 발행일시 (우측)
            if len(parts) > 1:
                right_part = parts[1]
                date_match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?', right_part)
                if date_match:
                    reg_date = date_match.group()
            
            # 1-2. 작성자 (좌측)
            left_part = parts[0]
            left_part = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', left_part) # 이메일 제거
            left_part = left_part.replace('/', '').replace('|', '').replace('기자', '').strip()
            if left_part:
                author = left_part
        
        # Fallback
        if reg_date == "-":
            date_match = re.search(r'\d{4}[.-]\d{2}[.-]\d{2}(\s+\d{2}:\d{2})?', soup.text)
            if date_match: reg_date = date_match.group()
        
        if author == "관리자" or len(author) > 20:
             author_tag = soup.select_one('.user-name') or soup.select_one('.writer') or soup.select_one('.byline')
             if author_tag: author = author_tag.text.strip()
        
        author = clean_author_name(author)

        # ---------------------------------------------------------
        # 2. 카테고리 추출
        # ---------------------------------------------------------
        navi_text = ""
        
        # [Priority 1] .naviLink 클래스
        navi_elem = soup.select_one('.naviLink')
        if navi_elem:
            navi_text = navi_elem.get_text(separator=' ', strip=True)
        
        # [Priority 2] "Home >" 텍스트 패턴
        if "Home" not in navi_text:
            crumb_elem = soup.find(string=re.compile(r"Home\s*[>|]"))
            if crumb_elem:
                navi_text = crumb_elem.parent.get_text(separator=' ', strip=True)

        # 파싱 ("Home > 푸드이슈 > ...")
        if "Home" in navi_text and (">" in navi_text or "|" in navi_text):
            clean_navi = re.sub(r'\s*[>|]\s*', '>', navi_text)
            parts = clean_navi.split('>')
            parts = [p.strip() for p in parts if p.strip()]
            
            if parts and parts[0].lower() == 'home':
                parts = parts[1:]
            
            if len(parts) >= 1: cat = parts[0]
            if len(parts) >= 2: subcat = parts[1]
        else:
            path_div = soup.select_one('.path') or soup.select_one('.location') or soup.select_one('#navigation')
            if path_div:
                txt = path_div.get_text().strip()
                parts = re.split(r'\s*[>|]\s*', txt)
                parts = [p.strip() for p in parts if p.strip()]
                if parts and parts[0].lower() == 'home': parts = parts[1:]
                if len(parts) >= 1: cat = parts[0]
                if len(parts) >= 2: subcat = parts[1]

        # 3. 기타 정보
        likes_elem = soup.select_one('.sns-like-count')
        likes = int(likes_elem.text.replace(',', '').strip()) if likes_elem and likes_elem.text and likes_elem.text.replace(',', '').strip().isdigit() else 0
        comments_elem = soup.select_one('.comment-count')
        comments = int(comments_elem.text.replace(',', '').strip()) if comments_elem and comments_elem.text and comments_elem.text.replace(',', '').strip().isdigit() else 0
        
        return (author, likes, comments, cat, subcat, reg_date)
    except: 
        return ("관리자", 0, 0, "뉴스", "이슈", "-")

@st.cache_data(ttl=3600, show_spinner="데이터 불러오는 중...")
def load_all_dashboard_data(selected_week):
    dr = WEEK_MAP[selected_week]
    s_dt = dr.split(' ~ ')[0].replace('.', '-')
    e_dt = dr.split(' ~ ')[1].replace('.', '-')
    ls_dt = (datetime.strptime(s_dt, '%Y-%m-%d')-timedelta(days=7)).strftime('%Y-%m-%d')
    le_dt = (datetime.strptime(e_dt, '%Y-%m-%d')-timedelta(days=7)).strftime('%Y-%m-%d')

    # 1. KPI
    summary = run_ga4_report(s_dt, e_dt, [], ["activeUsers", "screenPageViews", "newUsers"])
    if not summary.empty:
        sel_uv = int(summary['activeUsers'].iloc[0])
        sel_pv = int(summary['screenPageViews'].iloc[0])
        sel_new = int(summary['newUsers'].iloc[0])
    else: sel_uv, sel_pv, sel_new = 0, 0, 0
    new_visitor_ratio = round((sel_new / sel_uv * 100), 1) if sel_uv > 0 else 0
    
    # 1-1. 24시간/48시간 방문자 수 (실시간 지표)
    today = datetime.now().date()
    yesterday = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    two_days_ago = (today - timedelta(days=2)).strftime('%Y-%m-%d')
    today_str = today.strftime('%Y-%m-%d')
    
    # 24시간 방문자 수 (어제 ~ 오늘)
    df_24h = run_ga4_report(yesterday, today_str, [], ["activeUsers"])
    visitor_24h = int(df_24h['activeUsers'].iloc[0]) if not df_24h.empty else 0
    
    # 48시간 방문자 수 (2일 전 ~ 오늘, 중복 제거된 UV)
    df_48h = run_ga4_report(two_days_ago, today_str, [], ["activeUsers"])
    visitor_48h = int(df_48h['activeUsers'].iloc[0]) if not df_48h.empty else 0

    # 2. 일별 데이터
    today = datetime.now().date()
    e_dt_date = datetime.strptime(e_dt, '%Y-%m-%d').date()
    actual_end_date = min(today, e_dt_date)
    actual_e_dt = actual_end_date.strftime('%Y-%m-%d')
    
    df_daily = run_ga4_report(s_dt, actual_e_dt, ["date"], ["activeUsers", "screenPageViews"])
    if not df_daily.empty:
        df_daily = df_daily.rename(columns={'date':'날짜', 'activeUsers':'UV', 'screenPageViews':'PV'})
        df_daily['날짜_원본'] = pd.to_datetime(df_daily['날짜'])
        df_daily = df_daily.sort_values('날짜_원본')
        df_daily = df_daily[df_daily['날짜_원본'].dt.date <= actual_end_date]
        df_daily['날짜'] = df_daily['날짜_원본'].dt.strftime('%m-%d')
        df_daily = df_daily.drop(columns=['날짜_원본'])
    
    # 3. 3개월 추이
    def fetch_week_data(week_label, date_str):
        ws, we = date_str.split(' ~ ')[0].replace('.', '-'), date_str.split(' ~ ')[1].replace('.', '-')
        res = run_ga4_report(ws, we, [], ["activeUsers", "screenPageViews"])
        if not res.empty and 'activeUsers' in res.columns and 'screenPageViews' in res.columns and len(res) > 0:
            try:
                # 날짜 정보도 함께 저장
                start_date_obj = datetime.strptime(ws, '%Y-%m-%d')
                return {
                    '주차': week_label, 
                    'UV': int(res['activeUsers'].iloc[0]), 
                    'PV': int(res['screenPageViews'].iloc[0]),
                    'start_date': start_date_obj,
                    'year': start_date_obj.year
                }
            except: return None
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_week_data, wl, dstr) for wl, dstr in list(WEEK_MAP.items())[:12]]
        results = [f.result() for f in concurrent.futures.as_completed(futures) if f.result()]
    
    df_weekly = pd.DataFrame(results)
    if not df_weekly.empty:
        def extract_week_num(x):
            match = re.search(r'\d+', str(x))
            return int(match.group()) if match else 0
        df_weekly['week_num'] = df_weekly['주차'].apply(extract_week_num)
        
        # 정렬: 연도 오름차순, 주차 오름차순 (2025년 이후 2026년 데이터가 오도록)
        # 1주차 오른편에 2, 3, 4, ..., n주차가 오도록 배치
        def sort_key(row):
            year = row['year']
            week_num = row['week_num']
            # 1주차는 각 연도의 첫 번째에 배치 (작은 값 부여)
            if week_num == 1:
                return (year, 0)
            # 2주차부터는 순서대로 (1주차 다음에 오도록)
            return (year, week_num)
        
        df_weekly['sort_key'] = df_weekly.apply(sort_key, axis=1)
        df_weekly = df_weekly.sort_values('sort_key').drop(columns=['sort_key', 'week_num', 'start_date', 'year'])
    
    # 3-1. GA4에서 활성기사 수 가져오기 (기간 내 조회가 발생한 고유 기사 주소 수)
    df_active_articles = run_ga4_report(s_dt, e_dt, ["pagePath", "date"], ["screenPageViews"], "screenPageViews", limit=10000)
    if not df_active_articles.empty:
        # URL 정규화 적용 (쿼리 파라미터 제거, idxno만 유지)
        df_active_articles['pagePath_normalized'] = df_active_articles['pagePath'].apply(normalize_page_path)
        df_active_articles['article_id'] = df_active_articles['pagePath'].apply(extract_article_id)
        
        # 기사 페이지 필터링 (article, news, view, story 포함)
        mask_article = df_active_articles['pagePath_normalized'].str.contains(r'article|news|view|story', case=False, regex=True, na=False)
        df_filtered_articles = df_active_articles[mask_article].copy()
        if df_filtered_articles.empty:
            # 필터링 결과가 없으면 전체 페이지 수 사용
            df_filtered_articles = df_active_articles[df_active_articles['pagePath_normalized'].str.len() > 1].copy()
        
        # 고유한 기사 주소(pagePath_normalized) 개수 계산 (중복 제거)
        active_article_count = df_filtered_articles['pagePath_normalized'].nunique()
    else:
        active_article_count = 0
        df_filtered_articles = pd.DataFrame()
    
    # 3-2. 발행기사 수 계산 (GA4 기준: 해당 주차에 처음으로 조회수(PV)가 발생한 기사)
    published_article_count = 0
    if not df_filtered_articles.empty:
        # 기간 날짜 객체 생성
        start_date_obj = datetime.strptime(s_dt, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(e_dt, '%Y-%m-%d').date()
        
        # 이전 주차 데이터 가져오기 (해당 주차 이전에 조회가 있었는지 확인)
        prev_week_start = (datetime.strptime(s_dt, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
        prev_week_end = (datetime.strptime(s_dt, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 이전 주차에 조회가 있었던 기사 목록
        df_prev_week = run_ga4_report(prev_week_start, prev_week_end, ["pagePath"], ["screenPageViews"], "screenPageViews", limit=10000)
        prev_week_paths = set()
        if not df_prev_week.empty:
            df_prev_week['pagePath_normalized'] = df_prev_week['pagePath'].apply(normalize_page_path)
            prev_week_paths = set(df_prev_week['pagePath_normalized'].unique())
        
        # 해당 주차에 처음으로 조회가 발생한 기사 찾기
        # 각 기사의 첫 조회 날짜 확인
        df_filtered_articles['date'] = pd.to_datetime(df_filtered_articles['date'])
        df_filtered_articles = df_filtered_articles.sort_values(['pagePath_normalized', 'date'])
        
        # 각 정규화된 pagePath별로 첫 조회 날짜 확인
        first_view_dates = df_filtered_articles.groupby('pagePath_normalized')['date'].min()
        
        # 해당 주차에 처음 조회가 발생한 기사 카운트
        for normalized_path, first_date in first_view_dates.items():
            first_date_obj = first_date.date() if hasattr(first_date, 'date') else pd.to_datetime(first_date).date()
            # 이전 주차에 조회가 없었고, 해당 주차 기간 내에 첫 조회가 발생한 경우
            if normalized_path not in prev_week_paths and start_date_obj <= first_date_obj <= end_date_obj:
                published_article_count += 1

    # 4. 유입경로
    def map_source(s):
        s = s.lower()
        if 'naver' in s: return '네이버'
        if 'daum' in s: return '다음'
        if 'facebook' in s: return '페이스북'
        if '(direct)' in s: return '직접'
        if 'google' in s: return '구글'
        return '기타'
    df_t_raw = run_ga4_report(s_dt, e_dt, ["sessionSource"], ["screenPageViews"])
    df_t_raw['유입경로'] = df_t_raw['sessionSource'].apply(map_source)
    df_traffic_curr = df_t_raw.groupby('유입경로')['screenPageViews'].sum().reset_index().rename(columns={'screenPageViews':'조회수'})
    
    search_engines = ['네이버', '구글', '다음']
    search_pv = df_traffic_curr[df_traffic_curr['유입경로'].isin(search_engines)]['조회수'].sum()
    total_pv_traffic = df_traffic_curr['조회수'].sum()
    search_inflow_ratio = round((search_pv / total_pv_traffic * 100), 1) if total_pv_traffic > 0 else 0
    
    df_tl_raw = run_ga4_report(ls_dt, le_dt, ["sessionSource"], ["screenPageViews"])
    df_tl_raw['유입경로'] = df_tl_raw['sessionSource'].apply(map_source)
    df_traffic_last = df_tl_raw.groupby('유입경로')['screenPageViews'].sum().reset_index().rename(columns={'screenPageViews':'조회수'})

    # 5. 방문자 특성
    def clean_and_group(df, col_name):
        if df.empty: return pd.DataFrame(columns=['구분', 'activeUsers'])
        df['구분'] = df[col_name].replace({'(not set)': '기타', '': '기타', 'unknown': '기타'}).fillna('기타')
        return df.groupby('구분', as_index=False)['activeUsers'].sum()

    region_map = {'Seoul':'서울','Gyeonggi-do':'경기','Incheon':'인천','Busan':'부산','Daegu':'대구','Gyeongsangnam-do':'경남','Gyeongsangbuk-do':'경북','Chungcheongnam-do':'충남','Chungcheongbuk-do':'충북','Jeollanam-do':'전남','Jeollabuk-do':'전북','Gangwon-do':'강원','Daejeon':'대전','Gwangju':'광주','Ulsan':'울산','Jeju-do':'제주','Sejong-si':'세종'}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        f_reg_c = executor.submit(run_ga4_report, s_dt, e_dt, ["region"], ["activeUsers"], "activeUsers", 50)
        f_reg_l = executor.submit(run_ga4_report, ls_dt, le_dt, ["region"], ["activeUsers"], "activeUsers", 50)
        f_age_c = executor.submit(run_ga4_report, s_dt, e_dt, ["userAgeBracket"], ["activeUsers"], "activeUsers")
        f_age_l = executor.submit(run_ga4_report, ls_dt, le_dt, ["userAgeBracket"], ["activeUsers"], "activeUsers")
        f_gen_c = executor.submit(run_ga4_report, s_dt, e_dt, ["userGender"], ["activeUsers"], "activeUsers")
        f_gen_l = executor.submit(run_ga4_report, ls_dt, le_dt, ["userGender"], ["activeUsers"], "activeUsers")

        d_rc, d_rl = f_reg_c.result(), f_reg_l.result()
        if not d_rc.empty: d_rc['region_mapped'] = d_rc['region'].map(region_map).fillna('기타')
        if not d_rl.empty: d_rl['region_mapped'] = d_rl['region'].map(region_map).fillna('기타')
        df_region_curr = clean_and_group(d_rc, 'region_mapped')
        df_region_last = clean_and_group(d_rl, 'region_mapped')

        d_ac, d_al = f_age_c.result(), f_age_l.result()
        for df in [d_ac, d_al]:
            if not df.empty:
                df['temp_age'] = df['userAgeBracket'].replace({'unknown': '기타', '(not set)': '기타'}).fillna('기타')
                df['구분'] = df['temp_age'].apply(lambda x: x + '세' if x != '기타' and '세' not in str(x) else x)
        df_age_curr = d_ac[d_ac['구분'] != '기타'].groupby('구분', as_index=False)['activeUsers'].sum() if not d_ac.empty else pd.DataFrame(columns=['구분', 'activeUsers'])
        df_age_last = d_al[d_al['구분'] != '기타'].groupby('구분', as_index=False)['activeUsers'].sum() if not d_al.empty else pd.DataFrame(columns=['구분', 'activeUsers'])

        d_gc, d_gl = f_gen_c.result(), f_gen_l.result()
        gender_map = {'male': '남성', 'female': '여성'}
        df_gender_curr = pd.DataFrame(columns=['구분', 'activeUsers'])
        df_gender_last = pd.DataFrame(columns=['구분', 'activeUsers'])
        
        if not d_gc.empty:
            d_gc['mapped'] = d_gc['userGender'].map(gender_map)
            df_gender_curr = d_gc.dropna(subset=['mapped']).groupby('mapped', as_index=False)['activeUsers'].sum()
            df_gender_curr = df_gender_curr.rename(columns={'mapped': '구분'})
            total_gc = d_gc['activeUsers'].sum()
            mapped_gc = df_gender_curr['activeUsers'].sum() if not df_gender_curr.empty else 0
            if total_gc > 0 and mapped_gc == 0:
                df_gender_curr = pd.DataFrame({'구분': ['기타'], 'activeUsers': [total_gc]})
        
        if not d_gl.empty:
            d_gl['mapped'] = d_gl['userGender'].map(gender_map)
            df_gender_last = d_gl.dropna(subset=['mapped']).groupby('mapped', as_index=False)['activeUsers'].sum()
            df_gender_last = df_gender_last.rename(columns={'mapped': '구분'})
            total_gl = d_gl['activeUsers'].sum()
            mapped_gl = df_gender_last['activeUsers'].sum() if not df_gender_last.empty else 0
            if total_gl > 0 and mapped_gl == 0:
                df_gender_last = pd.DataFrame({'구분': ['기타'], 'activeUsers': [total_gl]})

    # 6. TOP 10 및 크롤링
    df_raw_top = run_ga4_report(s_dt, e_dt, ["pageTitle", "pagePath"], ["screenPageViews", "activeUsers", "newUsers", "userEngagementDuration", "bounceRate"], "screenPageViews", limit=100)
    
    df_top10_sources = pd.DataFrame()

    if not df_raw_top.empty:
        # URL 정규화 적용
        df_raw_top['pagePath_normalized'] = df_raw_top['pagePath'].apply(normalize_page_path)
        df_raw_top['article_id'] = df_raw_top['pagePath'].apply(extract_article_id)
        
        def is_excluded(row):
            t = str(row['pageTitle']).lower().replace(' ', '')
            if 'cook&chef' in t or '쿡앤셰프' in t: return True
            return False
        exclude_mask = df_raw_top.apply(is_excluded, axis=1)
        df_raw_all = df_raw_top[~exclude_mask].copy()
        
        # df_raw_all도 정규화된 경로를 '경로' 컬럼으로 사용하도록 설정 (나중에 사용할 때)
        df_raw_all['경로'] = df_raw_all['pagePath_normalized']
        
        # 정규화된 pagePath 기준으로 그룹화하여 중복 제거 및 집계
        # article_id가 있으면 article_id 기준, 없으면 pagePath_normalized 기준
        df_raw_all['group_key'] = df_raw_all.apply(
            lambda row: row['article_id'] if row['article_id'] else row['pagePath_normalized'], 
            axis=1
        )
        
        # 그룹별로 집계 (조회수, 방문자수 등 합산)
        df_grouped = df_raw_all.groupby(['group_key', 'pagePath_normalized', 'pageTitle']).agg({
            'screenPageViews': 'sum',
            'activeUsers': 'sum',
            'newUsers': 'sum',
            'userEngagementDuration': 'mean',  # 평균 체류시간
            'bounceRate': 'mean'  # 평균 이탈률
        }).reset_index()
        
        # 조회수 기준으로 정렬하고 상위 10개 선택
        df_sorted = df_grouped.sort_values('screenPageViews', ascending=False).head(10)
        paths_normalized = df_sorted['pagePath_normalized'].tolist()
        
        if paths_normalized:
            # 6-1. 유입경로 데이터 수집 (Raw Data)
            # 정규화된 경로에 대응하는 모든 원본 경로 찾기 (GA4 필터링용)
            # df_raw_top에서 정규화된 경로에 매칭되는 모든 원본 경로 수집
            all_original_paths = []
            for norm_path in paths_normalized:
                # 정규화된 경로와 매칭되는 원본 경로들 찾기
                matching = df_raw_top[df_raw_top['pagePath_normalized'] == norm_path]
                if not matching.empty:
                    all_original_paths.extend(matching['pagePath'].unique().tolist())
            
            all_original_paths = list(set(all_original_paths))  # 중복 제거
            
            if all_original_paths:
                filter_ex = FilterExpression(
                    filter=Filter(
                        field_name="pagePath",
                        in_list_filter=Filter.InListFilter(values=all_original_paths, case_sensitive=False)
                    )
                )
                df_sources_raw = run_ga4_report(
                    s_dt, e_dt, 
                    ["pagePath", "sessionSource"], 
                    ["screenPageViews"], 
                    limit=1000, 
                    dimension_filter=filter_ex
                )
            else:
                df_sources_raw = pd.DataFrame()
            
            if not df_sources_raw.empty:
                # URL 정규화 적용
                df_sources_raw['pagePath_normalized'] = df_sources_raw['pagePath'].apply(normalize_page_path)
                
                # 정규화된 경로가 top10에 포함되는지 확인 (필터링)
                df_sources_raw = df_sources_raw[df_sources_raw['pagePath_normalized'].isin(paths_normalized)]
                
                # category (네이버, 구글 등) 매핑
                df_sources_raw['category'] = df_sources_raw['sessionSource'].apply(map_source)
                
                # 정규화된 pagePath 기준으로 집계 (동일 기사 통합)
                # [A] 테이블용: 기사별로 가장 많이 유입된 경로 찾기
                # pagePath_normalized별로 조회수 내림차순 정렬 후 첫 번째 행 추출
                df_best_source = df_sources_raw.sort_values('screenPageViews', ascending=False).drop_duplicates('pagePath_normalized')
                # '기타'인 경우 구체적 경로 표시, 아니면 카테고리 표시
                df_best_source['best_source_display'] = df_best_source.apply(
                    lambda x: f"기타({x['sessionSource']})" if x['category'] == '기타' else x['category'], axis=1
                )
                best_source_map = dict(zip(df_best_source['pagePath_normalized'], df_best_source['best_source_display']))
                
                # [B] 차트용: (pagePath_normalized, category) 그룹핑 + 툴팁용 상세 경로(top_detail) 추출
                # B-1. 그룹별 최다 유입 raw source 찾기
                df_grp_best = df_sources_raw.sort_values('screenPageViews', ascending=False).drop_duplicates(['pagePath_normalized', 'category'])
                df_grp_best = df_grp_best[['pagePath_normalized', 'category', 'sessionSource']].rename(columns={'sessionSource': 'top_detail'})
                
                # B-2. 그룹별 조회수 합계 (정규화된 경로 기준으로 동일 기사 통합)
                df_grp_sum = df_sources_raw.groupby(['pagePath_normalized', 'category'], as_index=False)['screenPageViews'].sum()
                
                # B-3. 병합 (합계 + 상세경로)
                df_top10_sources = pd.merge(df_grp_sum, df_grp_best, on=['pagePath_normalized', 'category'], how='left')
                df_top10_sources = df_top10_sources.rename(columns={'category': '유입경로', 'pagePath_normalized': 'pagePath'})

            else:
                best_source_map = {}

        # 6-2. 크롤링 수행 (정규화된 경로 사용)
        scraped_data_dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(crawl_single_article_cached, path): idx for idx, path in enumerate(paths)}
            for future in concurrent.futures.as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result(timeout=3.0)
                    scraped_data_dict[idx] = result
                except: scraped_data_dict[idx] = ("관리자", 0, 0, "뉴스", "이슈", "-")
        
        scraped_data = [scraped_data_dict[i] for i in range(len(paths))]
        auths, lks, cmts, cats, subcats, reg_dates = zip(*scraped_data) if scraped_data else ([], [], [], [], [], [])
        
        # 6-3. 데이터 병합 및 정리
        # 정규화된 경로로 크롤링 (원본 경로가 아닌 정규화된 경로 사용)
        df_sorted['작성자'] = list(auths) if auths else ["관리자"] * len(df_sorted)
        df_sorted['좋아요'] = list(lks) if lks else [0] * len(df_sorted)
        df_sorted['댓글'] = list(cmts) if cmts else [0] * len(df_sorted)
        df_sorted['카테고리'] = list(cats) if cats else ["뉴스"] * len(df_sorted)
        df_sorted['세부카테고리'] = list(subcats) if subcats else ["이슈"] * len(df_sorted)
        df_sorted['실발행일시'] = list(reg_dates) if reg_dates else ["-"] * len(df_sorted)
        
        def is_excluded_author(row):
            a = str(row['작성자']).lower().replace(' ', '')
            if '인기기사' in a: return True
            return False
            
        exclude_mask_author = df_sorted.apply(is_excluded_author, axis=1)
        df_top10 = df_sorted[~exclude_mask_author].copy()
        df_top10['순위'] = range(1, len(df_top10)+1)
        # 정규화된 경로를 '경로' 컬럼으로 사용
        df_top10 = df_top10.rename(columns={'pageTitle': '제목', 'pagePath_normalized': '경로', 'screenPageViews': '전체조회수', 'activeUsers': '전체방문자수', 'userEngagementDuration': '평균체류시간', 'bounceRate': '이탈률'})
        
        df_raw_all = df_raw_top.copy()
        def format_duration(sec):
            try:
                sec_int = int(float(sec))
                m, s = divmod(sec_int, 60)
                return f"{m}분 {s}초"
            except: return "0분 0초"
        df_top10['체류시간_fmt'] = df_top10['평균체류시간'].apply(format_duration)
        df_top10['발행일시'] = df_top10['실발행일시']
        
        # 24시간, 48시간 방문자 수 추가 (주차 기간의 마지막 날짜 기준으로 계산)
        # 주차 기간의 마지막 날짜를 기준으로 역산하여 계산 (전체방문자수보다 작아야 함)
        e_dt_date = datetime.strptime(e_dt, '%Y-%m-%d').date()
        today = datetime.now().date()
        # 주차 기간의 마지막 날짜와 오늘 중 작은 값 사용 (미래 날짜 방지)
        period_end_date = min(e_dt_date, today)
        
        # 24시간 방문자 수: 마지막 날 하루만 (period_end_date 하루)
        df_24h_all = run_ga4_report(
            period_end_date.strftime('%Y-%m-%d'), 
            period_end_date.strftime('%Y-%m-%d'),
            ['pagePath'],
            ['activeUsers'],
            order_by_metric='activeUsers',
            limit=10000
        )
        visitor_24h = {}
        if not df_24h_all.empty:
            # URL 정규화 적용
            df_24h_all['pagePath_normalized'] = df_24h_all['pagePath'].apply(normalize_page_path)
            # 정규화된 경로 기준으로 집계
            df_24h_grouped = df_24h_all.groupby('pagePath_normalized')['activeUsers'].sum()
            for path, uv in df_24h_grouped.items():
                visitor_24h[path] = int(uv) if pd.notna(uv) else 0
        
        # 48시간 방문자 수: 마지막 날 + 그 전날 (2일치)
        # (주차 기간 내에서만 계산)
        period_end_48h_start = max(
            (period_end_date - timedelta(days=1)),
            datetime.strptime(s_dt, '%Y-%m-%d').date()
        )
        df_48h_all = run_ga4_report(
            period_end_48h_start.strftime('%Y-%m-%d'), 
            period_end_date.strftime('%Y-%m-%d'),
            ['pagePath'],
            ['activeUsers'],
            order_by_metric='activeUsers',
            limit=10000
        )
        visitor_48h = {}
        if not df_48h_all.empty:
            # URL 정규화 적용
            df_48h_all['pagePath_normalized'] = df_48h_all['pagePath'].apply(normalize_page_path)
            # 정규화된 경로 기준으로 집계 (중복 제거된 UV)
            df_48h_grouped = df_48h_all.groupby('pagePath_normalized')['activeUsers'].sum()
            for path, uv in df_48h_grouped.items():
                visitor_48h[path] = int(uv) if pd.notna(uv) else 0
        
        # 24시간/48시간 방문자 수는 정규화된 경로 기준으로 매핑
        df_top10['24시간방문자수'] = df_top10['경로'].apply(lambda x: visitor_24h.get(x, 0))
        df_top10['48시간방문자수'] = df_top10['경로'].apply(lambda x: visitor_48h.get(x, 0))
        
        # 검증: 24시간/48시간 방문자 수가 전체방문자수보다 크면 전체방문자수로 제한
        df_top10['24시간방문자수'] = df_top10.apply(
            lambda row: min(row['24시간방문자수'], row['전체방문자수']), axis=1
        )
        df_top10['48시간방문자수'] = df_top10.apply(
            lambda row: min(row['48시간방문자수'], row['전체방문자수']), axis=1
        )
        
        if 'newUsers' in df_top10.columns and '전체방문자수' in df_top10.columns:
            df_top10['신규방문자비율'] = df_top10.apply(
                lambda row: f"{round((float(row['newUsers']) / float(row['전체방문자수']) * 100), 1) if float(row['전체방문자수']) > 0 else 0}%",
                axis=1
            )
        else: df_top10['신규방문자비율'] = f"{new_visitor_ratio}%"
        
        # [테이블용] 유입경로 1순위 컬럼 추가 (정규화된 경로 기준)
        if not df_sources_raw.empty and best_source_map:
            df_top10['유입경로 1순위'] = df_top10['경로'].map(best_source_map).fillna("-")
        else:
            df_top10['유입경로 1순위'] = "-"
            
        # 기존 로직 (최다유입 % 표시용 - 하위 호환성 유지)
        if not df_top10_sources.empty:
            page_sums = df_top10_sources.groupby('pagePath')['screenPageViews'].transform('sum')
            df_top10_sources['ratio'] = (df_top10_sources['screenPageViews'] / page_sums * 100).round(1)
            # 여기서는 최다유입 표시용으로 기존처럼 둠 (UI에서는 위에서 만든 '유입경로 1순위'를 쓸 예정)
            df_top10['최다유입'] = df_top10['유입경로 1순위'] 
        else:
            df_top10['최다유입'] = "-"

    else: 
        df_top10 = pd.DataFrame()
        df_raw_all = pd.DataFrame()
        df_top10_sources = pd.DataFrame()
    
    # 6-4. 발행기사 기준 TOP 10 생성 (크롤링 기준 마스터 데이터 + GA4 Left Join)
    df_published_top10 = pd.DataFrame()
    
    # 기간 날짜 객체 생성
    start_date_obj = datetime.strptime(s_dt, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(e_dt, '%Y-%m-%d').date()
    
    # 이전 주차 데이터 가져오기 (해당 주차 이전에 조회가 있었는지 확인)
    prev_week_start = (datetime.strptime(s_dt, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
    prev_week_end = (datetime.strptime(s_dt, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 이전 주차에 조회가 있었던 기사 목록 (정규화된 경로 기준)
    df_prev_week = run_ga4_report(prev_week_start, prev_week_end, ["pagePath", "date"], ["screenPageViews"], "screenPageViews", limit=10000)
    prev_week_paths = set()
    if not df_prev_week.empty:
        df_prev_week['pagePath_normalized'] = df_prev_week['pagePath'].apply(normalize_page_path)
        prev_week_paths = set(df_prev_week['pagePath_normalized'].unique())
    
    # 해당 주차 데이터에서 정규화된 경로 기준으로 첫 조회 날짜 확인
    df_raw_all_with_date = run_ga4_report(s_dt, e_dt, ["pageTitle", "pagePath", "date"], ["screenPageViews", "activeUsers", "newUsers", "userEngagementDuration", "bounceRate"], "screenPageViews", limit=10000)
    
    # [STEP 1] 크롤링 기준 마스터 데이터 생성: 해당 주차에 처음 조회가 발생한 기사 수집
    published_articles_master = []
    if not df_raw_all_with_date.empty:
        df_raw_all_with_date['pagePath_normalized'] = df_raw_all_with_date['pagePath'].apply(normalize_page_path)
        df_raw_all_with_date['article_id'] = df_raw_all_with_date['pagePath'].apply(extract_article_id)
        df_raw_all_with_date['date'] = pd.to_datetime(df_raw_all_with_date['date'])
        
        # 정규화된 경로별로 첫 조회 날짜 확인
        first_view_dates = df_raw_all_with_date.groupby('pagePath_normalized')['date'].min()
        
        # 해당 주차에 처음 조회가 발생한 기사 필터링 (크롤링 기준 마스터 데이터)
        for normalized_path, first_date in first_view_dates.items():
            first_date_obj = first_date.date() if hasattr(first_date, 'date') else pd.to_datetime(first_date).date()
            # 이전 주차에 조회가 없었고, 해당 주차 기간 내에 첫 조회가 발생한 경우
            if normalized_path not in prev_week_paths and start_date_obj <= first_date_obj <= end_date_obj:
                # 크롤링으로 제목/카테고리 매핑 (정규화된 경로 사용)
                crawl_path = normalized_path
                try:
                    crawl_result = crawl_single_article_cached(crawl_path)
                    # 크롤링 결과를 마스터 데이터로 저장 (GA4 데이터는 나중에 Left Join)
                    master_row = {
                        'pagePath_normalized': normalized_path,
                        'article_id': extract_article_id(normalized_path),
                        '작성자': crawl_result[0] if len(crawl_result) > 0 else "관리자",
                        '좋아요': crawl_result[1] if len(crawl_result) > 1 else 0,
                        '댓글': crawl_result[2] if len(crawl_result) > 2 else 0,
                        '카테고리': crawl_result[3] if len(crawl_result) > 3 else "뉴스",
                        '세부카테고리': crawl_result[4] if len(crawl_result) > 4 else "이슈",
                        '실발행일시': crawl_result[5] if len(crawl_result) > 5 else "-"
                    }
                    published_articles_master.append(master_row)
                except:
                    pass
    
    # [STEP 2] 크롤링 결과를 마스터 데이터로 사용 (최대 10건)
    if published_articles_master:
        df_master = pd.DataFrame(published_articles_master)
        # 최대 10건으로 제한 (크롤링 기준)
        df_master = df_master.head(10)
        
        # [STEP 3] GA4 데이터와 Left Join (정규화된 경로 기준)
        # GA4 데이터 집계 (정규화된 경로 기준)
        if not df_raw_all_with_date.empty:
            df_ga4_agg = df_raw_all_with_date.groupby('pagePath_normalized').agg({
                'screenPageViews': 'sum',
                'activeUsers': 'sum',
                'newUsers': 'sum',
                'userEngagementDuration': 'mean',
                'bounceRate': 'mean',
                'pageTitle': 'first'  # 첫 번째 제목 사용
            }).reset_index()
        else:
            df_ga4_agg = pd.DataFrame(columns=['pagePath_normalized', 'screenPageViews', 'activeUsers', 'newUsers', 'userEngagementDuration', 'bounceRate', 'pageTitle'])
        
        # Left Join: 크롤링 마스터 데이터를 기준으로 GA4 데이터 병합 (조회수 0인 기사도 포함)
        df_published_all = pd.merge(df_master, df_ga4_agg, on='pagePath_normalized', how='left')
        
        # GA4 데이터가 없는 기사는 0으로 채우기
        for col in ['screenPageViews', 'activeUsers', 'newUsers']:
            df_published_all[col] = df_published_all[col].fillna(0)
        for col in ['userEngagementDuration', 'bounceRate']:
            df_published_all[col] = df_published_all[col].fillna(0.0)
        df_published_all['pageTitle'] = df_published_all['pageTitle'].fillna('')
        
        # 조회수로 정렬하고 상위 10개 선택 (df_published_top10용)
        df_published = df_published_all.copy().sort_values('screenPageViews', ascending=False).head(10)
        
        # df_top10과 동일한 형식으로 변환
        df_published['순위'] = range(1, len(df_published)+1)
        df_published = df_published.rename(columns={
            'pageTitle': '제목', 
            'pagePath_normalized': '경로', 
            'screenPageViews': '전체조회수', 
            'activeUsers': '전체방문자수', 
            'userEngagementDuration': '평균체류시간', 
            'bounceRate': '이탈률'
        })
        
        def format_duration(sec):
            try:
                sec_int = int(float(sec))
                m, s = divmod(sec_int, 60)
                return f"{m}분 {s}초"
            except: return "0분 0초"
        df_published['체류시간_fmt'] = df_published['평균체류시간'].apply(format_duration)
        df_published['발행일시'] = df_published['실발행일시']
        
        # 24시간, 48시간 방문자 수 추가 (df_top10과 동일한 방식)
        # visitor_24h, visitor_48h는 전체 방문자 수이므로, 각 기사별로는 0으로 설정 (개별 기사별 24h/48h 방문자 수는 별도 계산 필요)
        df_published['24시간방문자수'] = 0
        df_published['48시간방문자수'] = 0
        
        # 검증: 24시간/48시간 방문자 수가 전체방문자수보다 크면 전체방문자수로 제한
        df_published['24시간방문자수'] = df_published.apply(
            lambda row: min(row['24시간방문자수'], row['전체방문자수']), axis=1
        )
        df_published['48시간방문자수'] = df_published.apply(
            lambda row: min(row['48시간방문자수'], row['전체방문자수']), axis=1
        )
        
        if 'newUsers' in df_published.columns and '전체방문자수' in df_published.columns:
            df_published['신규방문자비율'] = df_published.apply(
                lambda row: f"{round((float(row['newUsers']) / float(row['전체방문자수']) * 100), 1) if float(row['전체방문자수']) > 0 else 0}%",
                axis=1
            )
        else: 
            df_published['신규방문자비율'] = f"{new_visitor_ratio}%"
        
        df_published['최다유입'] = "-"
        df_published['유입경로 1순위'] = "-"
        df_published_top10 = df_published
            
        # 이번주 발행기사 전체를 df_published_all로 변환 (기자별 분석용) - 크롤링 기준 10건
        df_published_all = df_published_all.rename(columns={
            'pageTitle': '제목', 
            'pagePath_normalized': '경로', 
            'screenPageViews': '전체조회수', 
            'activeUsers': '전체방문자수', 
            'userEngagementDuration': '평균체류시간', 
            'bounceRate': '이탈률'
        })
        df_published_all['체류시간_fmt'] = df_published_all['평균체류시간'].apply(format_duration)
        df_published_all['발행일시'] = df_published_all['실발행일시']
    else:
        df_published_all = pd.DataFrame()

    # 이번주 발행기사 전체 (기자별 분석용) - 크롤링 기준 마스터 데이터
    df_published_all_week = df_published_all if 'df_published_all' in locals() else pd.DataFrame()
    
    # 발행기사 수를 크롤링 기준 마스터 데이터(최대 10건)로 재계산
    if not df_published_all_week.empty:
        published_article_count = len(df_published_all_week)
    
    return (sel_uv, sel_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
            df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
            df_top10, df_raw_all, new_visitor_ratio, search_inflow_ratio, active_article_count, published_article_count, df_top10_sources, df_published_top10, df_published_all_week, visitor_24h, visitor_48h)

def get_writers_df_real(df_target):
    # 1. 엑셀 데이터로부터 매핑 딕셔너리 생성 (필명 -> 본명)
    #    동일한 필명이 여러 명에게 할당되지 않았다고 가정 (1:1 또는 N:1 구조)
    #    AUTHOR_MAPPING_DATA는 {'본명': ..., '필명': ...} 리스트
    pen_to_real_map = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
    
    if df_target.empty or '작성자' not in df_target.columns: 
        return pd.DataFrame(), pd.DataFrame()

    # 2. 크롤링된 데이터(df_target)의 '작성자'(필명) 컬럼을 기준으로 본명 매핑
    df_work = df_target.copy()
    df_work['본명_mapped'] = df_work['작성자'].map(pen_to_real_map).fillna(df_work['작성자'])
    
    # 3-1. 본명 기준 집계: 본명으로 그룹화하여 합산
    writers_by_real = df_work.groupby('본명_mapped').agg(
        기사수=('제목','count'), 
        총조회수=('전체조회수','sum'),
        좋아요=('좋아요', 'sum'),
        댓글=('댓글', 'sum')
    ).reset_index()
    writers_by_real = writers_by_real.rename(columns={'본명_mapped': '작성자'})
    writers_by_real['평균조회수'] = (writers_by_real['총조회수']/writers_by_real['기사수']).astype(int)
    writers_by_real = writers_by_real.sort_values('총조회수', ascending=False)
    writers_by_real['순위'] = range(1, len(writers_by_real)+1)
    # 필명 컬럼 추가 (빈 값 또는 대표 필명)
    writers_by_real['필명'] = ''
    
    # 3-2. 필명 기준 집계: 필명(작성자)으로 그룹화하여 합산
    writers_by_pen = df_work.groupby('작성자').agg(
        기사수=('제목','count'), 
        총조회수=('전체조회수','sum'),
        좋아요=('좋아요', 'sum'),
        댓글=('댓글', 'sum')
    ).reset_index()
    writers_by_pen['본명_mapped'] = writers_by_pen['작성자'].map(pen_to_real_map).fillna(writers_by_pen['작성자'])
    writers_by_pen = writers_by_pen.rename(columns={'작성자': '필명', '본명_mapped': '작성자'})
    writers_by_pen['평균조회수'] = (writers_by_pen['총조회수']/writers_by_pen['기사수']).astype(int)
    writers_by_pen = writers_by_pen.sort_values('총조회수', ascending=False)
    writers_by_pen['순위'] = range(1, len(writers_by_pen)+1)
    
    return writers_by_real, writers_by_pen
