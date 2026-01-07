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
                return {'주차': week_label, 'UV': int(res['activeUsers'].iloc[0]), 'PV': int(res['screenPageViews'].iloc[0])}
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
        def sort_key(row): return 1000 + row['week_num'] if row['week_num'] == 1 else row['week_num']
        df_weekly['sort_key'] = df_weekly.apply(sort_key, axis=1)
        df_weekly = df_weekly.sort_values('sort_key').drop(columns=['sort_key'])
    
    active_article_count = 0 

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
        mask_article = df_raw_top['pagePath'].str.contains(r'article|news|view|story', case=False, regex=True, na=False)
        active_article_count = df_raw_top[mask_article].shape[0]
        if active_article_count == 0:
            active_article_count = df_raw_top[df_raw_top['pagePath'].str.len() > 1].shape[0]
        
        def is_excluded(row):
            t = str(row['pageTitle']).lower().replace(' ', '')
            if 'cook&chef' in t or '쿡앤셰프' in t: return True
            return False
        exclude_mask = df_raw_top.apply(is_excluded, axis=1)
        df_raw_all = df_raw_top[~exclude_mask].copy()
        
        df_sorted = df_raw_all.sort_values('screenPageViews', ascending=False).head(10)
        paths = df_sorted['pagePath'].tolist()
        
        if paths:
            # 6-1. 유입경로 데이터 수집 (Raw Data)
            filter_ex = FilterExpression(
                filter=Filter(
                    field_name="pagePath",
                    in_list_filter=Filter.InListFilter(values=paths, case_sensitive=False)
                )
            )
            df_sources_raw = run_ga4_report(
                s_dt, e_dt, 
                ["pagePath", "sessionSource"], 
                ["screenPageViews"], 
                limit=1000, 
                dimension_filter=filter_ex
            )
            
            if not df_sources_raw.empty:
                # category (네이버, 구글 등) 매핑
                df_sources_raw['category'] = df_sources_raw['sessionSource'].apply(map_source)
                
                # [A] 테이블용: 기사별로 가장 많이 유입된 경로 찾기
                # pagePath별로 조회수 내림차순 정렬 후 첫 번째 행 추출
                df_best_source = df_sources_raw.sort_values('screenPageViews', ascending=False).drop_duplicates('pagePath')
                # '기타'인 경우 구체적 경로 표시, 아니면 카테고리 표시
                df_best_source['best_source_display'] = df_best_source.apply(
                    lambda x: f"기타({x['sessionSource']})" if x['category'] == '기타' else x['category'], axis=1
                )
                best_source_map = dict(zip(df_best_source['pagePath'], df_best_source['best_source_display']))
                
                # [B] 차트용: (pagePath, category) 그룹핑 + 툴팁용 상세 경로(top_detail) 추출
                # B-1. 그룹별 최다 유입 raw source 찾기
                df_grp_best = df_sources_raw.sort_values('screenPageViews', ascending=False).drop_duplicates(['pagePath', 'category'])
                df_grp_best = df_grp_best[['pagePath', 'category', 'sessionSource']].rename(columns={'sessionSource': 'top_detail'})
                
                # B-2. 그룹별 조회수 합계
                df_grp_sum = df_sources_raw.groupby(['pagePath', 'category'], as_index=False)['screenPageViews'].sum()
                
                # B-3. 병합 (합계 + 상세경로)
                df_top10_sources = pd.merge(df_grp_sum, df_grp_best, on=['pagePath', 'category'], how='left')
                df_top10_sources = df_top10_sources.rename(columns={'category': '유입경로'})

            else:
                best_source_map = {}

        # 6-2. 크롤링 수행
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
        df_top10 = df_top10.rename(columns={'pageTitle': '제목', 'pagePath': '경로', 'screenPageViews': '전체조회수', 'activeUsers': '전체방문자수', 'userEngagementDuration': '평균체류시간', 'bounceRate': '이탈률'})
        
        df_raw_all = df_raw_top.copy()
        def format_duration(sec):
            try:
                sec_int = int(float(sec))
                m, s = divmod(sec_int, 60)
                return f"{m}분 {s}초"
            except: return "0분 0초"
        df_top10['체류시간_fmt'] = df_top10['평균체류시간'].apply(format_duration)
        df_top10['발행일시'] = df_top10['실발행일시']
        
        if 'newUsers' in df_top10.columns and '전체방문자수' in df_top10.columns:
            df_top10['신규방문자비율'] = df_top10.apply(
                lambda row: f"{round((float(row['newUsers']) / float(row['전체방문자수']) * 100), 1) if float(row['전체방문자수']) > 0 else 0}%",
                axis=1
            )
        else: df_top10['신규방문자비율'] = f"{new_visitor_ratio}%"
        
        # [테이블용] 유입경로 1순위 컬럼 추가
        if not df_sources_raw.empty:
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

    return (sel_uv, sel_pv, df_daily, df_weekly, df_traffic_curr, df_traffic_last, 
            df_region_curr, df_region_last, df_age_curr, df_age_last, df_gender_curr, df_gender_last, 
            df_top10, df_raw_all, new_visitor_ratio, search_inflow_ratio, active_article_count, df_top10_sources)

def get_writers_df_real(df_target):
    # 1. 엑셀 데이터로부터 매핑 딕셔너리 생성 (필명 -> 본명)
    #    동일한 필명이 여러 명에게 할당되지 않았다고 가정 (1:1 또는 N:1 구조)
    #    AUTHOR_MAPPING_DATA는 {'본명': ..., '필명': ...} 리스트
    pen_to_real_map = {item['필명']: item['본명'] for item in AUTHOR_MAPPING_DATA}
    
    if df_target.empty or '작성자' not in df_target.columns: return pd.DataFrame()

    # 2. 크롤링된 데이터(df_target)의 '작성자'(필명) 컬럼을 기준으로 본명 매핑
    #    매핑되지 않는 필명은 '미상' 대신 원래 필명을 본명으로 사용하거나 별도 처리가능. 
    #    여기서는 필명을 그대로 유지(혹은 '미상')하고 진행.
    df_work = df_target.copy()
    df_work['본명_mapped'] = df_work['작성자'].map(pen_to_real_map).fillna(df_work['작성자'])
    
    # 3. [기자별 집계]는 '필명(작성자)' 단위로 수행해야 views.py의 로직(필명 기준 필터링 등)과 호환됨.
    #    따라서 GroupBy는 '작성자'(필명)로 수행하되, '본명' 컬럼을 보존해야 함.
    writers = df_work.groupby(['작성자', '본명_mapped']).agg(
        기사수=('제목','count'), 
        총조회수=('전체조회수','sum'),
        좋아요=('좋아요', 'sum'),
        댓글=('댓글', 'sum')
    ).reset_index()
    
    # 4. 정렬 (총조회수 내림차순)
    writers = writers.sort_values('총조회수', ascending=False)
    writers['순위'] = range(1, len(writers)+1)
    
    # 5. 평균조회수 계산
    writers['평균조회수'] = (writers['총조회수']/writers['기사수']).astype(int)
    
    # 6. 컬럼명 조정 (views.py와의 호환성 유지)
    #    views.py의 render_writer_real는 '작성자'를 본명으로, '필명'을 필명으로 출력하려고 시도함.
    #    views.py의 render_writer_pen는 '필명'을 필명으로, '작성자'를 본명으로 출력하려고 시도함.
    #    
    #    따라서 반환하는 DataFrame의 컬럼을 다음과 같이 설정:
    #    - '작성자': 본명 (Real Name)
    #    - '필명': 필명 (Pen Name)
    #    이렇게 하면 views.py에서:
    #      - Tab 7(본명): 작성자(본명) | 필명(필명) -> OK
    #      - Tab 8(필명): 필명(필명) | 본명(작성자) -> OK
    
    writers = writers.rename(columns={'작성자': '필명', '본명_mapped': '작성자'})
    
    return writers