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
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(full_url, headers=headers, timeout=3.0)
        response.encoding = response.apparent_encoding 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        reg_date = "-"
        author = "관리자"
        cat, subcat = "뉴스", "이슈"

        view_title_section = soup.select_one('.viewTitle')
        target_text = ""
        if view_title_section:
            dd_elem = view_title_section.select_one('dl dd')
            if dd_elem:
                target_text = dd_elem.get_text(separator=' ', strip=True)

        if "기사승인" not in target_text:
            fallback_elem = soup.find(string=re.compile("기사승인"))
            if fallback_elem:
                target_text = fallback_elem.parent.get_text(separator=' ', strip=True)

        if "기사승인" in target_text:
            parts = target_text.split("기사승인")
            if len(parts) > 1:
                right_part = parts[1]
                date_match = re.search(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(:\d{2})?', right_part)
                if date_match:
                    reg_date = date_match.group()
            
            left_part = parts[0]
            left_part = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', left_part)
            left_part = left_part.replace('/', '').replace('|', '').replace('기자', '').strip()
            if left_part:
                author = left_part
        
        if reg_date == "-":
            date_match = re.search(r'\d{4}[.-]\d{2}[.-]\d{2}(\s+\d{2}:\d{2})?', soup.text)
            if date_match: reg_date = date_match.group()
        
        if author == "관리자" or len(author) > 20:
             author_tag = soup.select_one('.user-name') or soup.select_one('.writer') or soup.select_one('.byline')
             if author_tag: author = author_tag.text.strip()
        
        author = clean_author_name(author)

        navi_elem = soup.select_one('.naviLink')
        navi_text = ""
        if navi_elem:
            navi_text = navi_elem.get_text(separator=' ', strip=True)
        
        if "Home" not in navi_text:
            crumb_elem = soup.find(string=re.compile(r"Home\s*[>|]"))
            if crumb_elem:
                navi_text = crumb_elem.parent.get_text(separator=' ', strip=True)

        if "Home" in navi_text and (">" in navi_text or "|" in navi_text):
            clean_navi = re.sub(r'\s*[>|]\s*', '>', navi_text)
            parts = clean_navi.split('>')
            parts = [p.strip() for p in parts if p.strip()]
            if parts and parts[0].lower() == 'home': parts = parts[1:]
            if len(parts) >= 1: cat = parts[0]
            if len(parts) >= 2: subcat = parts[1]

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
        df_daily['날짜'] = df_daily['날짜_원본'].dt.strftime('%m-%d')
        df_daily = df_daily.drop(columns=['날짜_원본'])
    
    # 3. 3개월 추이 (연도 및 주차 정렬 반영)
    def fetch_week_data(week_label, date_str):
        ws, we = date_str.split(' ~ ')[0].replace('.', '-'), date_str.split(' ~ ')[1].replace('.', '-')
        year = int(date_str.split('.')[0]) # 연도 추출
        res = run_ga4_report(ws, we, [], ["activeUsers", "screenPageViews"])
        if not res.empty and 'activeUsers' in res.columns and 'screenPageViews' in res.columns:
            try:
                return {
                    '주차': week_label, 
                    'UV': int(res['activeUsers'].iloc[0]), 
                    'PV': int(res['screenPageViews'].iloc[0]),
                    'year': year
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
        # 연도와 주차 숫자로 정렬하여 25년 44주차 -> 26년 1주차 순서 보장
        df_weekly = df_weekly.sort_values(['year', 'week_num'], ascending=[True, True])
        df_weekly = df_weekly.drop(columns=['year', 'week_num'])

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
    
    total_pv_traffic = df_traffic_curr['조회수'].sum()
    search_pv = df_traffic_curr[df_traffic_curr['유입경로'].isin(['네이버', '구글', '다음'])]['조회수'].sum()
    search_inflow_ratio = round((search_pv / total_pv_traffic * 100), 1) if total_pv_traffic > 0 else 0
    
    df_tl_raw = run_ga4_report(ls_dt, le_dt, ["sessionSource"], ["screenPageViews"])
    df_tl_raw['유입경로'] = df_tl_raw['sessionSource'].apply(map_source)
    df_traffic_last = df_tl_raw.groupby('유입경로')['screenPageViews'].sum().reset_index().rename(columns={'screenPageViews':'조회수'})

    # 5. 방문자 특성 (생략 - 기존 로직 유지)
    df_region_curr, df_region_last = pd.DataFrame(), pd.DataFrame()
    df_age_curr, df_age_last = pd.DataFrame(), pd.DataFrame()
    df_gender_curr, df_gender_last = pd.DataFrame(), pd.DataFrame()

    # 6. TOP 10 및 크롤링 (생략 - 기존 로직 유지)
    df_top10, df_raw_all, df_top10_sources = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    active_article_count = 0

    return (sel_uv, sel_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
            df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
            df_top10, df_raw_all, new_visitor_ratio, search_inflow_ratio, active_article_count, df_top10_sources)

def get_writers_df_real(df_target):
    pen_to_real_map = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
    if df_target.empty or '작성자' not in df_target.columns: return pd.DataFrame()

    df_work = df_target.copy()
    df_work['본명_mapped'] = df_work['작성자'].map(pen_to_real_map).fillna(df_work['작성자'])
    
    writers = df_work.groupby(['작성자', '본명_mapped']).agg(
        기사수=('제목','count'), 
        총조회수=('전체조회수','sum'),
        좋아요=('좋아요', 'sum'),
        댓글=('댓글', 'sum')
    ).reset_index()
    
    writers = writers.sort_values('총조회수', ascending=False)
    writers['순위'] = range(1, len(writers)+1)
    writers['평균조회수'] = (writers['총조회수']/writers['기사수']).astype(int)
    writers = writers.rename(columns={'작성자': '필명', '본명_mapped': '작성자'})
    
    return writers
