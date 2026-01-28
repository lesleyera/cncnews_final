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
# URL 정규화 및 기자명 정제 함수
# -----------------------------------------------------------------------------
def normalize_page_path(page_path):
    if not page_path or pd.isna(page_path):
        return page_path
    page_path = str(page_path)
    if '?' in page_path:
        base_path, query = page_path.split('?', 1)
        idxno_match = re.search(r'idxno=(\d+)', query)
        if idxno_match:
            return f"{base_path}?idxno={idxno_match.group(1)}"
        else:
            return base_path
    return page_path

def extract_article_id(page_path):
    if not page_path or pd.isna(page_path):
        return None
    page_path = str(page_path)
    idxno_match = re.search(r'idxno=(\d+)', page_path)
    if idxno_match:
        return idxno_match.group(1)
    return None

def process_author_name(raw_name):
    """기자명에서 직함을 제거하고 순수 이름만 추출 (김성민 편집인 -> 김성민)"""
    if not raw_name: return "관리자"
    # 직함 제거 (편집인, 전문기자, 기자, 전문 등)
    clean_name = re.sub(r'(편집인|전문기자|기자|전문|#)', '', raw_name).strip()
    clean_name = ' '.join(clean_name.split())
    return clean_name if clean_name else "관리자"

# -----------------------------------------------------------------------------
# [설정] 본명-필명 매핑 데이터
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
                    row_dict[met] = float(val) if '.' in val else int(val)
                except:
                    row_dict[met] = 0
            data.append(row_dict)
        return pd.DataFrame(data)
    except: return pd.DataFrame(columns=dimensions + metrics)

@st.cache_data(ttl=86400)
def crawl_single_article_cached(url_path):
    """메타 태그(section, section2) 및 기자명 정밀 추출"""
    full_url = f"http://www.cooknchefnews.com{url_path}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(full_url, headers=headers, timeout=2.5)
        response.encoding = response.apparent_encoding 
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 카테고리 추출 (메타 태그 article:section)
        meta_cat = soup.find("meta", property="article:section")
        cat = meta_cat["content"] if meta_cat else "뉴스"
        meta_subcat = soup.find("meta", property="article:section2")
        subcat = meta_subcat["content"] if meta_subcat else "이슈"

        # 2. 기자명 추출 (ld+json 우선)
        author = "관리자"
        script_tag = soup.find("script", type="application/ld+json")
        if script_tag:
            try:
                json_data = json.loads(script_tag.string)
                if isinstance(json_data, dict):
                    author = json_data.get("author", {}).get("name", "관리자")
                elif isinstance(json_data, list):
                    author = json_data[0].get("author", {}).get("name", "관리자")
            except: pass
        if author == "관리자":
            dd_elem = soup.select_one('.viewTitle dl dd')
            if dd_elem: author = dd_elem.get_text().split("기사승인")[0].strip()
        
        # 직함 정제 적용
        author = process_author_name(author)

        # 3. 기타 정보
        reg_date = "-"
        meta_date = soup.find("meta", property="article:published_time")
        if meta_date: reg_date = meta_date["content"].split('T')[0]

        likes_elem = soup.select_one('.sns-like-count')
        likes = int(likes_elem.text.replace(',', '')) if likes_elem and likes_elem.text.strip().isdigit() else 0
        comments_elem = soup.select_one('.comment-count')
        comments = int(comments_elem.text.replace(',', '')) if comments_elem and comments_elem.text.strip().isdigit() else 0
        title_tag = soup.find("meta", property="og:title")
        title = title_tag["content"] if title_tag else ""

        return (author, likes, comments, cat, subcat, reg_date, title)
    except: 
        return ("관리자", 0, 0, "뉴스", "이슈", "-", "")

@st.cache_data(ttl=3600, show_spinner="데이터 불러오는 중...")
def load_all_dashboard_data(selected_week):
    # (기존 GA4 리포트 호출 로직 유지 - 생략 가능하나 전체 코드를 위해 포함)
    dr = WEEK_MAP[selected_week]
    s_dt, e_dt = dr.split(' ~ ')[0].replace('.', '-'), dr.split(' ~ ')[1].replace('.', '-')
    
    # KPI, 일별, 3개월 추이 데이터 수집 (기존과 동일)
    # ... (중략) ...

    # [중요] 상위 기사 크롤링 및 데이터 병합 부분
    df_raw_top = run_ga4_report(s_dt, e_dt, ["pageTitle", "pagePath"], ["screenPageViews", "activeUsers", "newUsers"], "screenPageViews", limit=100)
    if not df_raw_top.empty:
        df_raw_top['pagePath_normalized'] = df_raw_top['pagePath'].apply(normalize_page_path)
        df_top10 = df_raw_top.head(10).copy()
        paths = df_top10['pagePath_normalized'].tolist()
        
        scraped_data = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            scraped_data = list(executor.map(crawl_single_article_cached, paths))
        
        auths, lks, cmts, cats, subcats, regs, titles = zip(*scraped_data)
        df_top10['작성자'] = auths
        df_top10['좋아요'] = lks
        df_top10['댓글'] = cmts
        df_top10['카테고리'] = cats
        df_top10['세부카테고리'] = subcats
        df_top10['실발행일시'] = regs
        
        # 본명 매핑 적용
        mapping_dict = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
        df_top10['본명'] = df_top10['작성자'].map(mapping_dict).fillna(df_top10['작성자'])
        
        return df_top10 # 예시 반환값 (실제 구조에 맞춰 조절)
    return pd.DataFrame()
