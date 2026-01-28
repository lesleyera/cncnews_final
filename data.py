# data.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import concurrent.futures
import re
import json
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
# URL 및 이름 정제 함수
# -----------------------------------------------------------------------------
def normalize_page_path(page_path):
    if not page_path or pd.isna(page_path): return page_path
    page_path = str(page_path)
    if '?' in page_path:
        base_path, query = page_path.split('?', 1)
        idxno_match = re.search(r'idxno=(\d+)', query)
        if idxno_match: return f"{base_path}?idxno={idxno_match.group(1)}"
        return base_path
    return page_path

def process_author_name(raw_name):
    """기자명에서 직함을 제거 (김성민 편집인 -> 김성민)"""
    if not raw_name: return "관리자"
    clean_name = re.sub(r'(편집인|전문기자|기자|전문|#)', '', raw_name).strip()
    return ' '.join(clean_name.split()) if clean_name else "관리자"

# -----------------------------------------------------------------------------
# 본명-필명 매핑 데이터
# -----------------------------------------------------------------------------
AUTHOR_MAPPING_DATA = [
    {"본명": "오영호", "필명": "오영호"}, {"본명": "이지헌", "필명": "이지헌"},
    {"본명": "이정호", "필명": "이정호"}, {"본명": "김성은", "필명": "김성은"},
    {"본명": "송자은", "필명": "송자은"}, {"본명": "허선", "필명": "허세인"},
    {"본명": "박현우", "필명": "박하늘"}, {"본명": "이정호", "필명": "이준민"},
    {"본명": "홍정민", "필명": "홍지우"}, {"본명": "김성은", "필명": "김세온"},
    {"본명": "조소현", "필명": "조서율"}, {"본명": "송자은", "필명": "송채연"},
    {"본명": "심세은", "필명": "심예린"}, {"본명": "정수연", "필명": "정서윤"},
    {"본명": "서진영", "필명": "서현민"}, {"본명": "AI협력", "필명": "오요리"},
    {"본명": "AI협력", "필명": "제조리"}, {"본명": "AI협력", "필명": "길라떼"},
    {"본명": "이경엽", "필명": "김병일"}, {"본명": "이경엽", "필명": "노하빈"},
    {"본명": "이경엽", "필명": "민혜경"}, {"본명": "이경엽", "필명": "이은지"},
    {"본명": "이경엽", "필명": "이경엽"}, {"본명": "이경엽", "필명": "정영"},
    {"본명": "조용수", "필명": "김철호"}, {"본명": "조용수", "필명": "마종수"},
    {"본명": "조용수", "필명": "박노석"}, {"본명": "조용수", "필명": "안정미"},
    {"본명": "조용수", "필명": "유성욱"}, {"본명": "조용수", "필명": "조용수"}
]

@st.cache_data(ttl=86400)
def crawl_single_article_cached(url_path):
    """웹페이지 소스에서 직접 메타태그와 기자명 추출"""
    full_url = f"http://www.cooknchefnews.com{url_path}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(full_url, headers=headers, timeout=3)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 카테고리 추출
        m_cat = soup.find("meta", property="article:section")
        cat = m_cat["content"] if m_cat else "뉴스"
        m_sub = soup.find("meta", property="article:section2")
        sub = m_sub["content"] if m_sub else "기타"

        # 기자명 추출
        author = "관리자"
        ld_json = soup.find("script", type="application/ld+json")
        if ld_json:
            try:
                js = json.loads(ld_json.string)
                author = js.get("author", {}).get("name", "관리자") if isinstance(js, dict) else js[0].get("author", {}).get("name", "관리자")
            except: pass
        if author == "관리자":
            dd = soup.select_one('.viewTitle dl dd')
            if dd: author = dd.get_text().split("기사승인")[0].strip()
        
        author = process_author_name(author)
        
        # 발행일 및 기타
        m_date = soup.find("meta", property="article:published_time")
        reg_date = m_date["content"].split('T')[0] if m_date else "-"
        
        return (author, cat, sub, reg_date)
    except:
        return ("관리자", "뉴스", "기타", "-")

def run_ga4_report(start_date, end_date, dimensions, metrics, order_by_metric=None, limit=None, dimension_filter=None):
    client = get_ga4_client()
    if not client: return pd.DataFrame()
    req = RunReportRequest(
        property=f"properties/{config.PROPERTY_ID}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)] if order_by_metric else [],
        limit=limit if limit else 10000,
        dimension_filter=dimension_filter
    )
    response = client.run_report(req)
    data = []
    for row in response.rows:
        row_dict = {dimensions[i]: row.dimension_values[i].value for i in range(len(dimensions))}
        for i, m in enumerate(metrics):
            row_dict[m] = float(row.metric_values[i].value) if '.' in row.metric_values[i].value else int(row.metric_values[i].value)
        data.append(row_dict)
    return pd.DataFrame(data)

@st.cache_data(ttl=3600)
def load_all_dashboard_data(selected_week):
    dr = WEEK_MAP[selected_week]
    s_dt, e_dt = dr.split(' ~ ')[0].replace('.', '-'), dr.split(' ~ ')[1].replace('.', '-')
    
    # 1. KPI 데이터
    df_kpi = run_ga4_report(s_dt, e_dt, [], ["activeUsers", "screenPageViews", "newUsers", "sessions"])
    cur_uv = df_kpi['activeUsers'].iloc[0] if not df_kpi.empty else 0
    cur_pv = df_kpi['screenPageViews'].iloc[0] if not df_kpi.empty else 0

    # 2. 일별/주별 추이 (기존 로직 유지)
    df_daily = run_ga4_report(s_dt, e_dt, ["date"], ["screenPageViews", "activeUsers"]).sort_values("date")
    df_weekly = pd.DataFrame() # 기존 데이터 수집 로직...

    # 3. 유입 채널 (기존 로직 유지)
    df_traffic_curr = run_ga4_report(s_dt, e_dt, ["sessionDefaultChannelGroup"], ["sessions"])
    df_traffic_last = pd.DataFrame() 

    # 4. 지역/연령/성별 (기존 로직 유지)
    df_region_curr = pd.DataFrame(); df_region_last = pd.DataFrame()
    df_age_curr = pd.DataFrame(); df_age_last = pd.DataFrame()
    df_gender_curr = pd.DataFrame(); df_gender_last = pd.DataFrame()

    # 5. Top 10 상세 데이터 (수정 핵심)
    df_top10 = run_ga4_report(s_dt, e_dt, ["pageTitle", "pagePath"], ["screenPageViews", "activeUsers", "newUsers"], "screenPageViews", limit=15)
    if not df_top10.empty:
        df_top10['pagePath_normalized'] = df_top10['pagePath'].apply(normalize_page_path)
        paths = df_top10['pagePath_normalized'].tolist()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as exec:
            results = list(exec.map(crawl_single_article_cached, paths))
        
        auths, cats, subcats, regs = zip(*results)
        df_top10['작성자'] = auths
        df_top10['카테고리'] = cats
        df_top10['세부카테고리'] = subcats
        df_top10['실발행일시'] = regs
        
        # 컬럼명 정리 (screenPageViews -> 전체조회수, pageTitle -> 제목, pagePath -> 경로)
        if 'screenPageViews' in df_top10.columns:
            df_top10['전체조회수'] = df_top10['screenPageViews']
        if 'pageTitle' in df_top10.columns:
            df_top10['제목'] = df_top10['pageTitle']
        if 'pagePath' in df_top10.columns:
            df_top10['경로'] = df_top10['pagePath']
        
        mapping_dict = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
        df_top10['본명'] = df_top10['작성자'].map(mapping_dict).fillna(df_top10['작성자'])

    # 6. 기타 필요한 변수들 정의 (Error 방지를 위해 app.py의 순서와 개수 일치)
    df_raw_all = df_top10.copy() if not df_top10.empty else pd.DataFrame()
    df_top10_sources = pd.DataFrame()
    df_published_top10 = df_top10.copy() if not df_top10.empty else pd.DataFrame()
    df_published_all_week = pd.DataFrame()
    visitor_24h = 0
    visitor_48h = 0
    new_ratio = 0
    search_ratio = 0
    active_article_count = len(df_top10) if not df_top10.empty else 0
    published_article_count = 0

    # app.py 라인 99의 언팩킹 순서에 맞춰 반환
    return (cur_uv, cur_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last,
            df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last,
            df_top10, df_raw_all, new_ratio, search_ratio, active_article_count, published_article_count,
            df_top10_sources, df_published_top10, df_published_all_week, visitor_24h, visitor_48h)

def get_writers_df_real(df_target):
    """기자별 데이터 생성 (본명 기준, 필명 기준)"""
    if df_target.empty or '작성자' not in df_target.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    # 필명 -> 본명 매핑
    pen_to_real_map = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
    
    df_work = df_target.copy()
    
    # 본명 매핑 (이미 '본명' 컬럼이 있으면 사용, 없으면 매핑)
    if '본명' not in df_work.columns:
        df_work['본명'] = df_work['작성자'].map(pen_to_real_map).fillna(df_work['작성자'])
    
    # '본명' 컬럼이 실제로 존재하는지 확인
    if '본명' not in df_work.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    # 카운트용 컬럼 결정 및 생성
    count_col = None
    if '제목' in df_work.columns:
        count_col = '제목'
    elif 'pageTitle' in df_work.columns:
        count_col = 'pageTitle'
    else:
        df_work['_count'] = 1
        count_col = '_count'
    
    # count_col이 실제로 존재하는지 확인
    if count_col not in df_work.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    # 집계용 컬럼 확인 및 생성 (반드시 존재하는 컬럼만 agg_dict에 추가)
    agg_dict = {}
    
    # 기사수는 항상 추가 (count_col은 위에서 보장됨)
    agg_dict['기사수'] = (count_col, 'count')
    
    # 총조회수 컬럼 확인 및 생성
    if '전체조회수' in df_work.columns:
        agg_dict['총조회수'] = ('전체조회수', 'sum')
    elif 'screenPageViews' in df_work.columns:
        agg_dict['총조회수'] = ('screenPageViews', 'sum')
    else:
        # 총조회수 컬럼이 없으면 기본값 0으로 생성
        df_work['총조회수'] = 0
        agg_dict['총조회수'] = ('총조회수', 'sum')
    
    # 좋아요 컬럼 확인 및 생성
    if '좋아요' in df_work.columns:
        agg_dict['좋아요'] = ('좋아요', 'sum')
    else:
        df_work['좋아요'] = 0
        agg_dict['좋아요'] = ('좋아요', 'sum')
    
    # 댓글 컬럼 확인 및 생성
    if '댓글' in df_work.columns:
        agg_dict['댓글'] = ('댓글', 'sum')
    else:
        df_work['댓글'] = 0
        agg_dict['댓글'] = ('댓글', 'sum')
    
    # agg_dict에 포함된 모든 컬럼이 실제로 존재하는지 최종 확인
    for key, (col, _) in agg_dict.items():
        if col not in df_work.columns:
            return pd.DataFrame(), pd.DataFrame()
    
    # 본명 기준 집계
    try:
        writers_df_real = df_work.groupby('본명').agg(agg_dict).reset_index()
    except (KeyError, ValueError) as e:
        return pd.DataFrame(), pd.DataFrame()
    writers_df_real = writers_df_real.rename(columns={'본명': '작성자'})
    writers_df_real = writers_df_real.sort_values('총조회수', ascending=False)
    writers_df_real['순위'] = range(1, len(writers_df_real) + 1)
    writers_df_real['평균조회수'] = (writers_df_real['총조회수'] / writers_df_real['기사수']).astype(int)
    
    # 필명 기준 집계
    try:
        writers_df_pen = df_work.groupby('작성자').agg(agg_dict).reset_index()
    except (KeyError, ValueError) as e:
        return pd.DataFrame(), pd.DataFrame()
    if '본명' in df_work.columns:
        writers_df_pen = writers_df_pen.merge(df_work[['작성자', '본명']].drop_duplicates(), on='작성자', how='left')
    else:
        writers_df_pen['본명'] = writers_df_pen['작성자'].map(pen_to_real_map).fillna(writers_df_pen['작성자'])
    writers_df_pen = writers_df_pen.rename(columns={'작성자': '필명'})
    writers_df_pen = writers_df_pen.sort_values('총조회수', ascending=False)
    writers_df_pen['순위'] = range(1, len(writers_df_pen) + 1)
    writers_df_pen['평균조회수'] = (writers_df_pen['총조회수'] / writers_df_pen['기사수']).astype(int)
    
    return writers_df_real, writers_df_pen
