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

# [설정] 본명-필명 매핑 데이터
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

def run_ga4_report(start_date, end_date, dimensions, metrics, order_by_metric=None, limit=None, dimension_filter=None):
    client = get_ga4_client()
    if not client: return pd.DataFrame()
    order_bys = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_by_metric), desc=True)] if order_by_metric else []
    request_params = {
        "property": f"properties/{config.PROPERTY_ID}",
        "dimensions": [Dimension(name=d) for d in dimensions],
        "metrics": [Metric(name=m) for m in metrics],
        "date_ranges": [DateRange(start_date=start_date, end_date=end_date)],
        "order_bys": order_bys, "limit": limit if limit else 10000
    }
    if dimension_filter: request_params["dimension_filter"] = dimension_filter
    try:
        response = client.run_report(RunReportRequest(**request_params))
        data = []
        for row in response.rows:
            row_dict = {dimensions[i]: row.dimension_values[i].value for i in range(len(dimensions))}
            for i, met in enumerate(metrics):
                val = row.metric_values[i].value
                row_dict[met] = int(val) if val.isdigit() else val
            data.append(row_dict)
        return pd.DataFrame(data)
    except: return pd.DataFrame()

@st.cache_data(ttl=86400)
def crawl_single_article_cached(url_path):
    full_url = f"http://www.cooknchefnews.com{url_path}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(full_url, headers=headers, timeout=5)
        res.encoding = res.apparent_encoding
        soup = BeautifulSoup(res.text, 'html.parser')
        author, likes, comments, cat, subcat, reg_date = "관리자", 0, 0, "뉴스", "이슈", "-"
        vt = soup.select_one('.viewTitle dl dd')
        if vt:
            txt = vt.get_text(separator=' ', strip=True)
            if "기사승인" in txt:
                ps = txt.split("기사승인")
                author = ps[0].replace('/', '').replace('|', '').replace('기자', '').strip()
                dm = re.search(r'\d{4}-\d{2}-\d{2}', ps[1])
                if dm: reg_date = dm.group()
        author = clean_author_name(author)
        return (author, likes, comments, cat, subcat, reg_date)
    except: return ("관리자", 0, 0, "뉴스", "이슈", "-")

@st.cache_data(ttl=3600)
def load_all_dashboard_data(selected_week):
    dr = WEEK_MAP[selected_week]
    s_dt = dr.split(' ~ ')[0].replace('.', '-')
    e_dt = dr.split(' ~ ')[1].replace('.', '-')

    # 1. KPI & 2. 일별 데이터 (기존 로직 동일)
    summary = run_ga4_report(s_dt, e_dt, [], ["activeUsers", "screenPageViews", "newUsers"])
    sel_uv = int(summary['activeUsers'].iloc[0]) if not summary.empty else 0
    sel_pv = int(summary['screenPageViews'].iloc[0]) if not summary.empty else 0
    sel_new = int(summary['newUsers'].iloc[0]) if not summary.empty else 0
    new_ratio = round((sel_new/sel_uv*100), 1) if sel_uv > 0 else 0

    df_daily = run_ga4_report(s_dt, e_dt, ["date"], ["activeUsers", "screenPageViews"])
    if not df_daily.empty:
        df_daily = df_daily.rename(columns={'date':'날짜', 'activeUsers':'UV', 'screenPageViews':'PV'})
        df_daily = df_daily.sort_values('날짜')
        df_daily['날짜'] = df_daily['날짜'].apply(lambda x: f"{x[4:6]}-{x[6:8]}")

    # 3. 3개월 추이 (정렬 수정 반영)
    def fetch_week_data(wl, dstr):
        ws, we = dstr.split(' ~ ')[0].replace('.', '-'), dstr.split(' ~ ')[1].replace('.', '-')
        yr = int(dstr.split('.')[0])
        res = run_ga4_report(ws, we, [], ["activeUsers", "screenPageViews"])
        if not res.empty:
            return {'주차': wl, 'UV': int(res['activeUsers'].iloc[0]), 'PV': int(res['screenPageViews'].iloc[0]), 'year': yr}
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(fetch_week_data, wl, dstr) for wl, dstr in list(WEEK_MAP.items())[:12]]
        results = [f.result() for f in concurrent.futures.as_completed(futures) if f.result()]
    
    df_weekly = pd.DataFrame(results)
    if not df_weekly.empty:
        df_weekly['wnum'] = df_weekly['주차'].apply(lambda x: int(re.search(r'\d+', x).group()))
        df_weekly = df_weekly.sort_values(['year', 'wnum'], ascending=[True, True]).drop(columns=['year', 'wnum'])

    # 4. 유입경로 (생략 없이 복구)
    df_t_raw = run_ga4_report(s_dt, e_dt, ["sessionSource"], ["screenPageViews"])
    def map_s(s):
        s = s.lower()
        if 'naver' in s: return '네이버'
        if 'daum' in s: return '다음'
        if 'google' in s: return '구글'
        return '기타'
    df_t_raw['유입경로'] = df_t_raw['sessionSource'].apply(map_s)
    df_traffic_curr = df_t_raw.groupby('유입경로')['screenPageViews'].sum().reset_index().rename(columns={'screenPageViews':'조회수'})
    search_ratio = round((df_traffic_curr[df_traffic_curr['유입경로']!='기타']['조회수'].sum()/sel_pv*100),1) if sel_pv > 0 else 0

    # 6. TOP 10 및 기사 집계 (누락되었던 핵심 로직 복구)
    df_pages = run_ga4_report(s_dt, e_dt, ["pageTitle", "pagePath"], ["screenPageViews"], "screenPageViews", 100)
    df_raw_all = pd.DataFrame()
    published_article_count = 0
    
    if not df_pages.empty:
        df_art = df_pages[df_pages['pagePath'].str.contains('idxno=', na=False)].copy()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
            c_res = list(ex.map(crawl_single_article_cached, df_art['pagePath']))
        
        df_art['작성자'] = [r[0] for r in c_res]
        df_art['좋아요'] = [r[1] for r in c_res]
        df_art['댓글'] = [r[2] for r in c_res]
        df_art['카테고리'] = [r[3] for r in c_res]
        df_art['날짜'] = [r[5] for r in c_res]
        df_art = df_art.rename(columns={'pageTitle':'제목', 'screenPageViews':'전체조회수'})
        
        df_raw_all = df_art
        published_article_count = len(df_art[df_art['날짜'].between(s_dt, e_dt)])

    return (sel_uv, sel_pv, df_daily, df_weekly, df_traffic_curr, pd.DataFrame(), 
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), 
            df_raw_all.head(10), df_raw_all, new_ratio, search_ratio, len(df_raw_all), pd.DataFrame(), published_article_count)

def get_writers_df_real(df_target):
    if df_target.empty: return pd.DataFrame()
    p2r = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
    df_w = df_target.copy()
    df_w['본명_mapped'] = df_w['작성자'].map(p2r).fillna(df_w['작성자'])
    res = df_w.groupby(['작성자', '본명_mapped']).agg(제목=('제목','count'), 전체조회수=('전체조회수','sum'), 좋아요=('좋아요','sum'), 댓글=('댓글','sum')).reset_index()
    res = res.sort_values('전체조회수', ascending=False).rename(columns={'작성자':'필명', '본명_mapped':'작성자', '제목':'기사수', '전체조회수':'총조회수'})
    res['순위'] = range(1, len(res)+1)
    res['평균조회수'] = (res['총조회수']/res['기사수']).astype(int)
    return res
