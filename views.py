# views.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import re

# 모듈 임포트
import config
from config import COLOR_NAVY, COLOR_RED, COLOR_GREY, CHART_PALETTE, COLOR_GENDER

# ----------------- 차트 생성 헬퍼 함수 -----------------
def create_donut_chart_with_val(df, names, values, color_map=None, height=350, margin=None, rotation=90, show_legend=False, limit_labels=None):
    if df.empty: return go.Figure()
    final_margin = margin if margin else dict(t=30, b=80, l=40, r=40)
    
    if '구분' in df.columns and len(df) == 1 and df['구분'].iloc[0] == '기타':
        fig = go.Figure(data=[go.Pie(
            labels=['기타 100%'],
            values=[df[values].iloc[0]],
            hole=0.5,
            marker=dict(colors=[COLOR_GREY]),
            textinfo='label',
            textposition='outside',
            rotation=rotation
        )])
        fig.update_layout(showlegend=False, margin=final_margin, height=height)
        return fig
    
    if '구분' in df.columns:
        df_normal = df[df['구분'] != '기타'].sort_values(by=values, ascending=False)
        df_other = df[df['구분'] == '기타']
        df_sorted = pd.concat([df_normal, df_other])
    else: df_sorted = df

    if color_map: 
        fig = px.pie(df_sorted, names=names, values=values, hole=0.5, color=names, color_discrete_map=color_map)
    else: 
        fig = px.pie(df_sorted, names=names, values=values, hole=0.5, color_discrete_sequence=CHART_PALETTE)
    
    if limit_labels:
        total_val = df_sorted[values].sum()
        custom_text = []
        for i in range(len(df_sorted)):
            if i < limit_labels:
                row_val = df_sorted.iloc[i][values]
                row_name = df_sorted.iloc[i][names]
                pct = (row_val / total_val * 100) if total_val > 0 else 0
                custom_text.append(f"{row_name} {pct:.1f}%")
            else:
                custom_text.append("")
        fig.update_traces(text=custom_text, textinfo='text', textposition='outside', sort=False, rotation=rotation, automargin=True)
    else:
        fig.update_traces(textposition='outside', textinfo='label+percent', sort=False, rotation=rotation, automargin=True)
    
    layout_update = dict(showlegend=show_legend, margin=final_margin, height=height)
    if show_legend:
        layout_update['legend'] = dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02)
    fig.update_layout(**layout_update)
    return fig

# ----------------- 1. 성과 요약 -----------------
def render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count=0, visitor_24h=0, visitor_48h=0):
    st.markdown('<div class="section-header-container first-section"><div class="section-header">1. 주간 전체 성과 요약</div></div>', unsafe_allow_html=True)
    pv_per_user = round(cur_pv/cur_uv, 1) if cur_uv > 0 else 0
    
    # 원래 지표 (24시간/48시간 제외)
    kpis = [
        ("활성 기사 수", active_article_count, "건"),
        ("발행 기사 수", published_article_count, "건"),
        ("지난 7일 간<br>조회수(PV)", cur_pv, "건"),
        ("지난 7일 간<br>방문자수(UV)", cur_uv, "명"), 
        ("방문자당 페이지뷰", pv_per_user, "건"),
        ("신규 방문자 비율", new_ratio, "%"),
        ("검색 유입 비율", search_ratio, "%")
    ]
    
    cols = st.columns(7)
    for i, (l, v, u) in enumerate(kpis):
        # 딕셔너리나 리스트인 경우 0으로 처리 (오류 방지)
        if isinstance(v, (dict, list)):
            v = 0
        # 숫자 타입 확인 및 포맷팅
        if isinstance(v, (int, np.integer, float)) and l not in ["방문자당 페이지뷰", "신규 방문자 비율", "검색 유입 비율"]:
            v_f = f"{v:,}"
        else:
            v_f = str(v)
        cols[i].markdown(f'<div class="kpi-container"><div class="kpi-label">{l}</div><div class="kpi-value">{v_f}<span class="kpi-unit">{u}</span></div></div>', unsafe_allow_html=True)
    
    # 각 지표 산식 각주 추가
    st.markdown("""
    <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f5; border-radius: 4px; font-size: 0.9rem; color: #546e7a;">
        <strong>※ 각 지표 산식:</strong><br>
        • 활성 기사 수: 해당 주차 기간 내 조회가 발생한 고유 기사 주소(pagePath) 수<br>
        • 발행 기사 수: 해당 주차에 처음으로 조회수(PV)가 발생한 기사 수 (GA4 기준)<br>
        • 지난 7일 간 조회수(PV): 해당 주차 기간 내 총 화면 조회수<br>
        • 지난 7일 간 방문자수(UV): 해당 주차 기간 내 총 활성 사용자 수<br>
        • 방문자당 페이지뷰: 총 조회수 ÷ 총 방문자수<br>
        • 신규 방문자 비율: 신규 사용자 수 ÷ 총 방문자수 × 100<br>
        • 검색 유입 비율: 검색 엔진을 통한 유입 세션 수 ÷ 총 세션 수 × 100
    </div>
    """, unsafe_allow_html=True)
        
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sub-header">📊 주간 일별 방문 추이</div>', unsafe_allow_html=True)
        if not df_daily.empty:
            df_melted = df_daily.melt(id_vars='날짜')
            fig = px.bar(df_melted, x='날짜', y='value', color='variable', barmode='group', color_discrete_map={'UV': COLOR_GREY, 'PV': COLOR_NAVY}, text='value')
            fig.update_traces(texttemplate='%{text:,}', textposition='outside')
            fig.update_xaxes(type='category')
            fig.update_layout(legend_title_text=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True, key="summary_daily_chart")
    with c2:
        st.markdown('<div class="sub-header">📈 최근 3달 간 추이 분석</div>', unsafe_allow_html=True)
        if not df_weekly.empty:
            # 최다 조회수 기사 제목이 있으면 hover 데이터로 추가
            uv_hover = []
            pv_hover = []
            if 'top_article' in df_weekly.columns:
                for idx, row in df_weekly.iterrows():
                    uv_hover.append(f"주차: {row['주차']}<br>UV: {row['UV']:,}<br>최다 조회 기사: {row['top_article']}")
                    pv_hover.append(f"주차: {row['주차']}<br>PV: {row['PV']:,}<br>최다 조회 기사: {row['top_article']}")
            else:
                uv_hover = [f"주차: {row['주차']}<br>UV: {row['UV']:,}" for idx, row in df_weekly.iterrows()]
                pv_hover = [f"주차: {row['주차']}<br>PV: {row['PV']:,}" for idx, row in df_weekly.iterrows()]
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=df_weekly['주차'], 
                y=df_weekly['UV'], 
                name='UV', 
                marker_color=COLOR_GREY,
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=uv_hover
            ))
            fig2.add_trace(go.Bar(
                x=df_weekly['주차'], 
                y=df_weekly['PV'], 
                name='PV', 
                marker_color=COLOR_NAVY,
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=pv_hover
            ))
            
            # 3달 간 평균 계산 및 붉은 점선 표시
            avg_uv = df_weekly['UV'].mean()
            avg_pv = df_weekly['PV'].mean()
            
            fig2.add_trace(go.Scatter(
                x=df_weekly['주차'], 
                y=[avg_uv] * len(df_weekly), 
                name='UV 평균', 
                mode='lines',
                line=dict(color='red', width=2, dash='dot'),
                hovertemplate='UV 평균: %{y:,.0f}<extra></extra>'
            ))
            
            fig2.add_trace(go.Scatter(
                x=df_weekly['주차'], 
                y=[avg_pv] * len(df_weekly), 
                name='PV 평균', 
                mode='lines',
                line=dict(color='red', width=2, dash='dot'),
                hovertemplate='PV 평균: %{y:,.0f}<extra></extra>'
            ))
            
            # UV, PV 최대값, 최소값 찾기
            max_uv_idx = df_weekly['UV'].idxmax()
            min_uv_idx = df_weekly['UV'].idxmin()
            max_pv_idx = df_weekly['PV'].idxmax()
            min_pv_idx = df_weekly['PV'].idxmin()
            
            max_uv_week = df_weekly.loc[max_uv_idx, '주차']
            min_uv_week = df_weekly.loc[min_uv_idx, '주차']
            max_pv_week = df_weekly.loc[max_pv_idx, '주차']
            min_pv_week = df_weekly.loc[min_pv_idx, '주차']
            
            max_uv_value = df_weekly.loc[max_uv_idx, 'UV']
            min_uv_value = df_weekly.loc[min_uv_idx, 'UV']
            max_pv_value = df_weekly.loc[max_pv_idx, 'PV']
            min_pv_value = df_weekly.loc[min_pv_idx, 'PV']
            
            # 최대값, 최소값에 주황색 주석 추가
            annotations = []
            
            # UV 최대값 (주황색)
            annotations.append(dict(
                x=max_uv_week, y=max_uv_value,
                text=f"{max_uv_value:,}",
                showarrow=True, arrowhead=2, arrowcolor='orange',
                font=dict(color='orange', size=11, family='Pretendard'),
                bgcolor='white', bordercolor='orange', borderwidth=1,
                ax=0, ay=-30
            ))
            
            # UV 최소값 (주황색)
            annotations.append(dict(
                x=min_uv_week, y=min_uv_value,
                text=f"{min_uv_value:,}",
                showarrow=True, arrowhead=2, arrowcolor='orange',
                font=dict(color='orange', size=11, family='Pretendard'),
                bgcolor='white', bordercolor='orange', borderwidth=1,
                ax=0, ay=30
            ))
            
            # PV 최대값 (주황색)
            annotations.append(dict(
                x=max_pv_week, y=max_pv_value,
                text=f"{max_pv_value:,}",
                showarrow=True, arrowhead=2, arrowcolor='orange',
                font=dict(color='orange', size=11, family='Pretendard'),
                bgcolor='white', bordercolor='orange', borderwidth=1,
                ax=0, ay=-30
            ))
            
            # PV 최소값 (주황색)
            annotations.append(dict(
                x=min_pv_week, y=min_pv_value,
                text=f"{min_pv_value:,}",
                showarrow=True, arrowhead=2, arrowcolor='orange',
                font=dict(color='orange', size=11, family='Pretendard'),
                bgcolor='white', bordercolor='orange', borderwidth=1,
                ax=0, ay=30
            ))
            
            week_labels = df_weekly['주차'].tolist()
            year_boundary_idx = None
            for i, label in enumerate(week_labels):
                week_num = int(re.search(r'\d+', str(label)).group()) if re.search(r'\d+', str(label)) else 0
                if week_num == 1 and i > 0:
                    prev_week_num = int(re.search(r'\d+', str(week_labels[i-1])).group()) if re.search(r'\d+', str(week_labels[i-1])) else 0
                    if prev_week_num == 52:
                        year_boundary_idx = i - 0.5
                        break
            
            if year_boundary_idx is not None:
                fig2.add_vline(x=year_boundary_idx, line_dash="dot", line_width=1, line_color="#78909c", opacity=0.7, annotation_text="2025/2026", annotation_position="top", annotation_font_size=10, annotation_font_color="#78909c")
            
            fig2.update_layout(
                barmode='group', 
                plot_bgcolor='white', 
                margin=dict(t=30), 
                yaxis=dict(tickformat=","), 
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                annotations=annotations
            )
            st.plotly_chart(fig2, use_container_width=True, key="summary_weekly_chart")

# ----------------- 2. 접근 경로 -----------------
def render_traffic(df_traffic_curr, df_traffic_last):
    st.markdown('<div class="section-header-container"><div class="section-header">2. 주간 접근 경로 분석</div></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    fig1 = px.pie(df_traffic_curr, names='유입경로', values='조회수', hole=0.5, color_discrete_sequence=CHART_PALETTE)
    fig1.update_layout(height=350, showlegend=True, margin=dict(t=30, b=80, l=40, r=40))
    with c1: st.plotly_chart(fig1, use_container_width=True, key="traffic_curr_chart")
    
    fig2 = px.pie(df_traffic_last, names='유입경로', values='조회수', hole=0.5, color_discrete_sequence=CHART_PALETTE)
    fig2.update_layout(height=280, showlegend=True, margin=dict(t=30, b=80, l=40, r=40))
    with c2: st.plotly_chart(fig2, use_container_width=True, key="traffic_last_chart")
    
    st.markdown('<div class="sub-header">주요 유입경로 비중 변화</div>', unsafe_allow_html=True)
    df_m = pd.merge(df_traffic_curr, df_traffic_last, on='유입경로', suffixes=('_이번', '_지난'))
    df_m['이번주 비중'] = (df_m['조회수_이번'] / df_m['조회수_이번'].sum() * 100).round(1)
    df_m['지난주 비중'] = (df_m['조회수_지난'] / df_m['조회수_지난'].sum() * 100).round(1)
    df_m['비중 변화'] = (df_m['이번주 비중'] - df_m['지난주 비중']).round(1)
    
    df_m.sort_values('이번주 비중', ascending=False, inplace=True)
    
    st.table(df_m[['유입경로', '이번주 비중', '지난주 비중', '비중 변화']].copy().assign(**{'비중 변화': lambda x: x['비중 변화'].apply(lambda v: f"{v:+.1f}%p")}))

# ----------------- 3. 방문자 특성 (지역) -----------------
def render_demo_region(df_region_curr, df_region_last):
    st.markdown('<div class="section-header-container"><div class="section-header">3. 주간 전체 방문자 특성 분석 (지역)</div></div>', unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>지역별 분석</div>", unsafe_allow_html=True)
    c_curr, c_last = st.columns(2)
    custom_margin = dict(t=20, b=20, l=0, r=0)
    
    with c_curr:
        st.markdown(f"**이번주**")
        fig_c = create_donut_chart_with_val(df_region_curr, '구분', 'activeUsers', None, height=350, margin=custom_margin, rotation=90, show_legend=True, limit_labels=5)
        fig_c.update_traces(textfont_size=11)
        st.plotly_chart(fig_c, use_container_width=True, key="region_curr_chart")
        
    with c_last:
        st.markdown(f"**지난주 (비교)**")
        fig_l = create_donut_chart_with_val(df_region_last, '구분', 'activeUsers', None, height=280, margin=custom_margin, rotation=90, show_legend=True, limit_labels=5)
        fig_l.update_traces(textfont_size=11)
        st.plotly_chart(fig_l, use_container_width=True, key="region_last_chart")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    if not df_region_curr.empty or not df_region_last.empty:
        df_change = pd.merge(df_region_curr, df_region_last, on='구분', suffixes=('_이번', '_지난'), how='outer').fillna(0)
        total_c = df_change['activeUsers_이번'].sum()
        total_l = df_change['activeUsers_지난'].sum()
        df_change['비율_이번'] = (df_change['activeUsers_이번'] / total_c * 100).round(1) if total_c > 0 else 0
        df_change['비율_지난'] = (df_change['activeUsers_지난'] / total_l * 100).round(1) if total_l > 0 else 0
        df_change['변화(%p)'] = df_change['비율_이번'] - df_change['비율_지난']
        
        df_norm = df_change[df_change['구분']!='기타'].sort_values('activeUsers_이번', ascending=False)
        df_oth = df_change[df_change['구분']=='기타']
        df_disp = pd.concat([df_norm, df_oth])
        
        df_disp['이번주(%)'] = df_disp['비율_이번'].astype(str) + '%'
        df_disp['지난주(%)'] = df_disp['비율_지난'].astype(str) + '%'
        df_disp['변화(%p)'] = df_disp['변화(%p)'].apply(lambda x: f"{x:+.1f}%p")
        # 스크롤 없이 전체 지역 나열
        st.table(df_disp[['구분', '이번주(%)', '지난주(%)', '변화(%p)']])

# ----------------- 3. 방문자 특성 (연령/성별) -----------------
def render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last):
    st.markdown('<div class="section-header-container"><div class="section-header">3. 주간 전체 방문자 특성 분석 (연령/성별)</div></div>', unsafe_allow_html=True)
    sub_titles = ['연령별', '성별']
    curr_data = [df_age_curr, df_gender_curr]
    last_data = [df_age_last, df_gender_last]
    color_maps = [None, COLOR_GENDER]
    
    for i in range(2):
        st.markdown(f"<div class='sub-header'>{sub_titles[i]} 분석</div>", unsafe_allow_html=True)
        c_curr, c_last = st.columns(2)
        d_c = curr_data[i]
        d_l = last_data[i]
        
        with c_curr:
            st.markdown(f"**이번주**")
            if d_c.empty or d_c['activeUsers'].sum() == 0:
                st.warning("⚠️ 이번주 데이터 없음 (GA4 비식별 처리)")
            else:
                st.plotly_chart(create_donut_chart_with_val(d_c, '구분', 'activeUsers', color_maps[i]), use_container_width=True, key=f"demo_curr_{i}_chart")
        with c_last:
            st.markdown(f"**지난주 (비교)**")
            if d_l.empty or d_l['activeUsers'].sum() == 0:
                st.info("지난주 데이터 없음")
            else:
                st.plotly_chart(create_donut_chart_with_val(d_l, '구분', 'activeUsers', color_maps[i], height=280), use_container_width=True, key=f"demo_last_{i}_chart")

        if not d_c.empty or not d_l.empty:
            df_change = pd.merge(d_c, d_l, on='구분', suffixes=('_이번', '_지난'), how='outer').fillna(0)
            total_c = df_change['activeUsers_이번'].sum()
            total_l = df_change['activeUsers_지난'].sum()
            df_change['비율_이번'] = (df_change['activeUsers_이번'] / total_c * 100).round(1) if total_c > 0 else 0
            df_change['비율_지난'] = (df_change['activeUsers_지난'] / total_l * 100).round(1) if total_l > 0 else 0
            df_change['변화(%p)'] = df_change['비율_이번'] - df_change['비율_지난']
            df_norm = df_change[df_change['구분']!='기타'].sort_values('activeUsers_이번', ascending=False)
            df_oth = df_change[df_change['구분']=='기타']
            df_disp = pd.concat([df_norm, df_oth])
            df_disp['이번주(%)'] = df_disp['비율_이번'].astype(str) + '%'
            df_disp['지난주(%)'] = df_disp['비율_지난'].astype(str) + '%'
            df_disp['변화(%p)'] = df_disp['변화(%p)'].apply(lambda x: f"{x:+.1f}%p")
            st.table(df_disp[['구분', '이번주(%)', '지난주(%)', '변화(%p)']])
        st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- 4. Top 10 상세 -----------------
def render_top10_detail(df_top10, df_published_top10=None):
    st.markdown('<div class="section-header-container"><div class="section-header">4. 최근 7일 조회수 TOP 10 기사 상세</div></div>', unsafe_allow_html=True)
    if not df_top10.empty:
        df_p4 = df_top10.copy()
        def safe_format_int(x):
            try: return f"{int(float(x)):,}"
            except: return str(x)
        for c in ['전체조회수','전체방문자수','좋아요','댓글']: 
            df_p4[c] = df_p4[c].apply(safe_format_int)
        df_p4_display = df_p4.copy()
        df_p4_display = df_p4_display.rename(columns={
            '전체조회수': '최근 7일간 조회수',
            '전체방문자수': '최근 7일간 방문자수',
            '체류시간_fmt': '체류시간',
            '최다유입': '최다 유입경로',
            '24시간방문자수': '24시간 방문자수',
            '48시간방문자수': '48시간 방문자수'
        })
        # 24시간, 48시간 방문자 수 포맷팅
        if '24시간 방문자수' in df_p4_display.columns:
            df_p4_display['24시간 방문자수'] = df_p4_display['24시간 방문자수'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        if '48시간 방문자수' in df_p4_display.columns:
            df_p4_display['48시간 방문자수'] = df_p4_display['48시간 방문자수'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        cols = ['순위','카테고리','세부카테고리','제목','작성자','발행일시','최근 7일간 조회수','최근 7일간 방문자수','신규방문자비율','최다 유입경로','체류시간','24시간 방문자수','48시간 방문자수','좋아요','댓글']
        # 존재하는 컬럼만 선택
        available_cols = [c for c in cols if c in df_p4_display.columns]
        st.table(df_p4_display[available_cols])
    
    # 4-1. 최근 발행기사 기준
    if df_published_top10 is not None and not df_published_top10.empty:
        st.markdown('<div class="section-header-container"><div class="section-header">4-1. 최근 발행기사 기준</div></div>', unsafe_allow_html=True)
        df_pub = df_published_top10.copy()
        def safe_format_int(x):
            try: return f"{int(float(x)):,}"
            except: return str(x)
        for c in ['전체조회수','전체방문자수','좋아요','댓글']: 
            if c in df_pub.columns:
                df_pub[c] = df_pub[c].apply(safe_format_int)
        df_pub_display = df_pub.copy()
        df_pub_display = df_pub_display.rename(columns={
            '전체조회수': '최근 7일간 조회수',
            '전체방문자수': '최근 7일간 방문자수',
            '체류시간_fmt': '체류시간',
            '최다유입': '최다 유입경로',
            '24시간방문자수': '24시간 방문자수',
            '48시간방문자수': '48시간 방문자수'
        })
        # 24시간, 48시간 방문자 수 포맷팅
        if '24시간 방문자수' in df_pub_display.columns:
            df_pub_display['24시간 방문자수'] = df_pub_display['24시간 방문자수'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        if '48시간 방문자수' in df_pub_display.columns:
            df_pub_display['48시간 방문자수'] = df_pub_display['48시간 방문자수'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")
        cols = ['순위','카테고리','세부카테고리','제목','작성자','발행일시','최근 7일간 조회수','최근 7일간 방문자수','신규방문자비율','최다 유입경로','체류시간','24시간 방문자수','48시간 방문자수','좋아요','댓글']
        # 존재하는 컬럼만 선택
        available_cols = [c for c in cols if c in df_pub_display.columns]
        st.table(df_pub_display[available_cols])

# ----------------- 5. Top 10 추이 -----------------
def render_top10_trends(df_top10, df_top10_sources=None):
    st.markdown('<div class="section-header-container"><div class="section-header">5. TOP 10 기사 유입경로(매체)별 조회수 분포</div></div>', unsafe_allow_html=True)
    
    if not df_top10.empty:
        df_p5 = df_top10.copy()
        def safe_format_int_col(x):
            try:
                val_str = str(x).replace(',', '')
                return f"{int(float(val_str)):,}"
            except: return str(x)
        
        df_p5['전체조회수_fmt'] = df_p5['전체조회수'].apply(safe_format_int_col)
        df_p5 = df_p5.rename(columns={'전체조회수_fmt': '지난 7일간 조회수'})
        
        cols = ['순위', '제목', '작성자', '발행일시', '지난 7일간 조회수', '유입경로 1순위']
        if '유입경로 1순위' not in df_p5.columns:
            df_p5['유입경로 1순위'] = "-"
            
        st.table(df_p5[cols])
        
        if df_top10_sources is not None and not df_top10_sources.empty:
            # df_top10의 순위 순서대로 정렬
            path_to_rank = dict(zip(df_top10['경로'], df_top10['순위']))
            path_to_total_pv = dict(zip(df_top10['경로'], df_top10['전체조회수']))
            
            df_src = df_top10_sources.copy()
            df_src['순위'] = df_src['pagePath'].map(path_to_rank).fillna(999)
            
            # 순위별로 정렬하고 top10만 필터링
            df_src = df_src[df_src['순위'] <= 10].sort_values('순위')
            
            # 각 기사별 유입경로 조회수 합계 계산
            df_src_sum_by_article = df_src.groupby('pagePath')['screenPageViews'].sum().reset_index()
            df_src_sum_by_article.columns = ['pagePath', 'source_total_pv']
            
            # df_top10의 전체조회수와 비교하여 비율 계산 및 정규화
            df_src = pd.merge(df_src, df_src_sum_by_article, on='pagePath', how='left')
            df_src['total_pv_from_top10'] = df_src['pagePath'].map(path_to_total_pv).fillna(0)
            
            # 유입경로별 조회수를 전체조회수에 맞게 정규화 (비율 유지)
            df_src['screenPageViews_normalized'] = df_src.apply(
                lambda row: int(row['screenPageViews'] * row['total_pv_from_top10'] / row['source_total_pv']) 
                if row['source_total_pv'] > 0 else 0, 
                axis=1
            )
            
            # df_top10의 정보를 df_src에 매핑 (제목, 발행일시 등)
            path_to_title = dict(zip(df_top10['경로'], df_top10['제목']))
            path_to_pubdate = dict(zip(df_top10['경로'], df_top10['발행일시']))
            path_to_author = dict(zip(df_top10['경로'], df_top10['작성자']))
            
            df_src['기사제목'] = df_src['pagePath'].map(path_to_title).fillna('기타')
            df_src['발행일시'] = df_src['pagePath'].map(path_to_pubdate).fillna('-')
            df_src['작성자'] = df_src['pagePath'].map(path_to_author).fillna('-')
            
            # 페이지 URL 매핑 (경로 -> 전체 URL) - 클릭 이벤트용
            df_src['page_url'] = df_src['pagePath'].apply(
                lambda x: f"https://cooknchefnews.com{x}" if x and not x.startswith('http') else x
            )
            
            # y축 레이블을 더 길게 표시 (30자까지) - 전체 제목이 더 잘 보이도록
            df_src['기사제목_short'] = df_src['기사제목'].apply(lambda x: x[:30] + '...' if len(str(x)) > 30 else str(x))
            
            # 순위 순서대로 정렬 (1위부터 10위까지) - 4페이지와 동일한 순서 보장
            # df_top10의 순위 순서를 그대로 사용하여 그래프 순서 일치
            df_top10_sorted = df_top10.sort_values('순위', ascending=True).reset_index(drop=True)
            short_titles_ordered = [t[:30] + '...' if len(str(t)) > 30 else str(t) for t in df_top10_sorted['제목'].tolist()]
            full_titles_ordered = df_top10_sorted['제목'].tolist()
            
            # df_src의 기사제목도 df_top10의 순위 순서에 맞춰 정렬
            # 경로 기준으로 순위 매핑하여 정렬
            df_src = df_src.sort_values(['순위', '유입경로']).reset_index(drop=True)
            
            # 정규화된 조회수 사용 (위의 표의 조회수 기준)
            # custom_data에 필요한 정보 포함 (클릭 이벤트용)
            custom_data_cols = ['top_detail', '기사제목', '순위', 'total_pv_from_top10', '발행일시', '작성자', 'page_url']
            # 존재하는 컬럼만 선택
            available_custom_cols = [col for col in custom_data_cols if col in df_src.columns]
            
            # 그래프 식별자를 제목이 아닌 정규화된 URL(경로)로 변경하여 동일 제목 기사 분리
            # 경로를 Y축 레이블로 사용하되, 표시는 제목으로
            df_src['y_axis_key'] = df_src['pagePath']  # 정규화된 경로를 식별자로 사용
            
            # df_top10의 순위 순서에 맞춰 Y축 순서 결정 (1위가 위, 10위가 아래)
            # df_top10_sorted의 경로 순서를 기준으로 Y축 순서 설정
            ordered_paths = df_top10_sorted['경로'].tolist()
            # df_src에서 순위별로 그룹화하여 경로 순서 유지
            df_src['y_order'] = df_src['pagePath'].map({path: idx for idx, path in enumerate(ordered_paths)}).fillna(999)
            df_src = df_src.sort_values(['y_order', '유입경로']).reset_index(drop=True)
            
            fig = px.bar(
                df_src, 
                x='screenPageViews_normalized',   
                y='y_axis_key',  # 정규화된 경로를 Y축 키로 사용 (제목이 아닌)
                color='유입경로',
                text='screenPageViews_normalized',
                title='기사별 유입경로 비중',
                orientation='h',       
                color_discrete_sequence=CHART_PALETTE,
                custom_data=available_custom_cols,
                category_orders={'y_axis_key': ordered_paths}  # 순위 순서대로 정렬
            )
            
            # Y축 레이블을 제목으로 표시 (하지만 식별자는 경로)
            # df_top10_sorted의 순서대로 제목 매핑
            path_to_title_map = dict(zip(df_top10_sorted['경로'], df_top10_sorted['제목']))
            y_tick_texts = []
            for path in ordered_paths:
                title = path_to_title_map.get(path, path)
                short_title = title[:30] + '...' if len(str(title)) > 30 else str(title)
                y_tick_texts.append(short_title)
            
            # Y축 레이블 업데이트 (순위 순서대로)
            fig.update_yaxes(
                tickmode='array',
                tickvals=ordered_paths,
                ticktext=y_tick_texts
            )
            
            # hover 템플릿 수정 - 전체 제목을 맨 위에 명확히 표시
            # customdata 인덱스: [top_detail(0), 기사제목(1), 순위(2), total_pv_from_top10(3), 발행일시(4), 작성자(5), page_url(6)]
            hover_template = '<b>전체 제목: %{customdata[1]}</b><br>순위: %{customdata[2]}위<br>작성자: %{customdata[5]}<br>발행일시: %{customdata[4]}<br>유입경로: %{legendgroup}<br>상세경로: %{customdata[0]}<br>조회수: %{x:,.0f}<br>전체조회수: %{customdata[3]:,.0f}<extra></extra>'
            
            fig.update_traces(
                hovertemplate=hover_template, 
                texttemplate='%{text:,}', 
                textposition='outside',
                hoverlabel=dict(bgcolor="white", font_size=12, font_family="Pretendard")
            )
            
            fig.update_layout(
                plot_bgcolor='white',
                xaxis_title='조회수',
                yaxis_title='기사 (요약)',
                legend_title_text='유입경로'
            )
            
            # y축 순서는 이미 category_orders로 설정됨 (위에서 ordered_paths 사용)
            
            # y축 레이블에 마우스를 올렸을 때 노란 배경의 커스텀 툴팁 표시
            full_titles_js = str(full_titles_ordered).replace("'", "\\'")
            short_titles_js = str(short_titles_ordered).replace("'", "\\'")
            
            yaxis_hover_script = f"""
            <style>
            .yaxis-tooltip {{
                position: absolute;
                background-color: #ffeb3b;
                color: #000;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                z-index: 10000;
                pointer-events: none;
                max-width: 400px;
                word-wrap: break-word;
                border: 1px solid #fbc02d;
                display: none;
            }}
            </style>
            <script>
            (function() {{
                let tooltip = null;
                
                function createTooltip() {{
                    if (!tooltip) {{
                        tooltip = document.createElement('div');
                        tooltip.className = 'yaxis-tooltip';
                        document.body.appendChild(tooltip);
                    }}
                    return tooltip;
                }}
                
                function showTooltip(e, text) {{
                    const tooltip = createTooltip();
                    tooltip.textContent = text;
                    tooltip.style.display = 'block';
                    
                    const x = e.clientX + 10;
                    const y = e.clientY + 10;
                    
                    tooltip.style.left = x + 'px';
                    tooltip.style.top = y + 'px';
                    
                    // 화면 밖으로 나가지 않도록 조정
                    setTimeout(() => {{
                        const rect = tooltip.getBoundingClientRect();
                        if (rect.right > window.innerWidth) {{
                            tooltip.style.left = (e.clientX - rect.width - 10) + 'px';
                        }}
                        if (rect.bottom > window.innerHeight) {{
                            tooltip.style.top = (e.clientY - rect.height - 10) + 'px';
                        }}
                    }}, 0);
                }}
                
                function hideTooltip() {{
                    if (tooltip) {{
                        tooltip.style.display = 'none';
                    }}
                }}
                
                function addHoverEvents() {{
                    const yAxisLabels = document.querySelectorAll('.ytick text');
                    const fullTitles = {full_titles_js};
                    const shortTitles = {short_titles_js};
                    
                    yAxisLabels.forEach(function(label) {{
                        const shortTitle = label.textContent.trim();
                        const titleIndex = shortTitles.indexOf(shortTitle);
                        if (titleIndex >= 0 && titleIndex < fullTitles.length) {{
                            const fullTitle = fullTitles[titleIndex];
                            
                            label.style.cursor = 'help';
                            
                            label.addEventListener('mouseenter', function(e) {{
                                showTooltip(e, fullTitle);
                            }});
                            
                            label.addEventListener('mouseleave', function() {{
                                hideTooltip();
                            }});
                            
                            label.addEventListener('mousemove', function(e) {{
                                if (tooltip && tooltip.style.display === 'block') {{
                                    const x = e.clientX + 10;
                                    const y = e.clientY + 10;
                                    tooltip.style.left = x + 'px';
                                    tooltip.style.top = y + 'px';
                                    
                                    setTimeout(() => {{
                                        const rect = tooltip.getBoundingClientRect();
                                        if (rect.right > window.innerWidth) {{
                                            tooltip.style.left = (e.clientX - rect.width - 10) + 'px';
                                        }}
                                        if (rect.bottom > window.innerHeight) {{
                                            tooltip.style.top = (e.clientY - rect.height - 10) + 'px';
                                        }}
                                    }}, 0);
                                }}
                            }});
                        }}
                    }});
                }}
                
                // 차트가 렌더링된 후 실행
                setTimeout(addHoverEvents, 1500);
                
                // Plotly 이벤트 리스너 추가
                const plotDiv = document.querySelector('[data-testid="stPlotlyChart"]');
                if (plotDiv) {{
                    plotDiv.addEventListener('plotly_afterplot', addHoverEvents);
                }}
                
                // 바 클릭 시 페이지 이동 기능
                function addClickEvents() {{
                    const plotDiv = document.querySelector('.js-plotly-plot');
                    if (plotDiv) {{
                        plotDiv.on('plotly_click', function(data) {{
                            if (data.points && data.points.length > 0) {{
                                const point = data.points[0];
                                // customdata에서 page_url 가져오기
                                if (point.customdata && point.customdata.length > 0) {{
                                    const customData = point.customdata;
                                    // customdata 배열에서 page_url 찾기 (마지막 요소)
                                    const pageUrl = customData[customData.length - 1];
                                    if (pageUrl) {{
                                        // 새 창에서 열기
                                        window.open(pageUrl, '_blank');
                                    }}
                                }}
                            }}
                        }});
                    }}
                }}
                
                // 차트가 렌더링된 후 클릭 이벤트 추가
                setTimeout(addClickEvents, 1500);
                
                // Plotly 이벤트 리스너 추가
                const plotDivForClick = document.querySelector('[data-testid="stPlotlyChart"]');
                if (plotDivForClick) {{
                    plotDivForClick.addEventListener('plotly_afterplot', addClickEvents);
                }}
            }})();
            </script>
            """
            st.markdown(yaxis_hover_script, unsafe_allow_html=True)
            
            # y축 레이블에 전체 제목을 툴팁으로 표시하기 위해 customdata 사용
            # y축 레이블 자체는 짧은 제목이지만, hover 시 전체 제목이 표시됨
            
            st.plotly_chart(fig, use_container_width=True, key="top10_source_distribution_chart")
        else:
            st.warning("기사별 유입경로 상세 데이터가 없습니다.")

# ----------------- 6. 카테고리 -----------------
def render_category(df_published_all):
    st.markdown('<div class="section-header-container"><div class="section-header">6. 카테고리별 분석</div></div>', unsafe_allow_html=True)
    if not df_published_all.empty:
        df_real = df_published_all
        # 메인 카테고리
        cat_main = df_real.groupby('카테고리').agg(기사수=('제목','count'), 전체조회수=('전체조회수','sum')).reset_index()
        total_main = cat_main['기사수'].sum()
        # [수정] 기사수 (비중%) 형태로 병합
        cat_main['기사수'] = cat_main.apply(lambda x: f"{x['기사수']} ({x['기사수']/total_main*100:.1f}%)", axis=1)
        
        cat_main['전체조회수'] = pd.to_numeric(cat_main['전체조회수'], errors='coerce').fillna(0)
        cat_main['기사수_num'] = cat_main['기사수'].apply(lambda x: int(x.split('(')[0])) # 차트용 숫자 추출
        
        # [수정] 컬럼명 변경: 기사1건당평균 -> 평균조회수
        cat_main['평균조회수'] = (cat_main['전체조회수'] / cat_main['기사수_num']).astype(int).map('{:,}'.format)
        cat_main['전체조회수'] = cat_main['전체조회수'].map('{:,}'.format)
        
        st.markdown('<div class="chart-header">1. 메인 카테고리별 기사 수</div>', unsafe_allow_html=True)
        st.plotly_chart(px.bar(cat_main, x='카테고리', y='기사수_num', text_auto=True, color='카테고리', color_discrete_sequence=CHART_PALETTE).update_layout(showlegend=False, plot_bgcolor='white', yaxis_title="기사수"), use_container_width=True, key="category_main_chart")
        st.table(cat_main[['카테고리', '기사수', '전체조회수', '평균조회수']])

        # 세부 카테고리
        st.markdown('<div class="chart-header">2. 세부 카테고리별 기사 수</div>', unsafe_allow_html=True)
        cat_sub = df_real.groupby(['카테고리', '세부카테고리']).agg(기사수=('제목','count'), 전체조회수=('전체조회수','sum')).reset_index()
        total_sub = cat_sub['기사수'].sum()
        # [수정] 기사수 (비중%) 형태로 병합
        cat_sub['기사수'] = cat_sub.apply(lambda x: f"{x['기사수']} ({x['기사수']/total_sub*100:.1f}%)", axis=1)
        
        cat_sub['전체조회수'] = pd.to_numeric(cat_sub['전체조회수'], errors='coerce').fillna(0)
        cat_sub['기사수_num'] = cat_sub['기사수'].apply(lambda x: int(x.split('(')[0]))
        
        # [수정] 컬럼명 변경: 기사1건당평균 -> 평균조회수
        cat_sub['평균조회수'] = (cat_sub['전체조회수'] / cat_sub['기사수_num']).astype(int).map('{:,}'.format)
        cat_sub['전체조회수'] = cat_sub['전체조회수'].map('{:,}'.format)
        
        st.plotly_chart(px.bar(cat_sub, x='세부카테고리', y='기사수_num', text_auto=True, color='카테고리', color_discrete_sequence=CHART_PALETTE).update_layout(plot_bgcolor='white', yaxis_title="기사수"), use_container_width=True, key="category_sub_chart")
        st.table(cat_sub[['카테고리', '세부카테고리', '기사수', '전체조회수', '평균조회수']])
        
        # [수정] 각주 추가
        st.markdown("<div style='font-size: 0.85rem; color: #78909c; margin-top: 5px;'>* 평균조회수: 카테고리 전체 조회수 ÷ 카테고리 기사 수</div>", unsafe_allow_html=True)
        
        # 발행기사 수 반환 (카테고리별 기사 수 합계)
        return total_main
    return 0

# ----------------- 7. 기자별 분석 -----------------
def render_writer_analysis(writers_df_real, writers_df_pen):
    st.markdown('<div class="section-header-container"><div class="section-header">7. 기자별 분석</div></div>', unsafe_allow_html=True)
    
    # 7-1. 이번주 기자별 분석 (본명 기준) - 본명으로 합산하여 순위 매김
    st.markdown('<div class="sub-header">7-1. 이번주 기자별 분석 (본명 기준)</div>', unsafe_allow_html=True)
    if not writers_df_real.empty:
        disp_w = writers_df_real.copy()
        for c in ['총조회수','평균조회수','좋아요','댓글']: disp_w[c] = disp_w[c].apply(lambda x: f"{x:,}")
        disp_w = disp_w[['순위', '작성자', '기사수', '총조회수', '평균조회수', '좋아요', '댓글']]
        disp_w.columns = ['순위', '본명', '발행기사 수', '전체 조회 수', '기사 1건 당 평균 조회 수', '좋아요 개수', '댓글 개수']
        st.table(disp_w)
    else:
        st.info("본명 기준 기자 실적 없음")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 7-2. 이번주 기자별 분석 (필명 기준) - 필명으로 합산하여 순위 매김
    st.markdown('<div class="sub-header">7-2. 이번주 기자별 분석 (필명 기준)</div>', unsafe_allow_html=True)
    if not writers_df_pen.empty:
        disp_w = writers_df_pen.copy()
        for c in ['총조회수','평균조회수','좋아요','댓글']: disp_w[c] = disp_w[c].apply(lambda x: f"{x:,}")
        disp_w = disp_w[['순위', '필명', '작성자', '기사수', '총조회수', '평균조회수', '좋아요', '댓글']]
        disp_w.columns = ['순위', '필명', '본명', '발행기사 수', '전체 조회 수', '기사 1건 당 평균 조회 수', '좋아요 개수', '댓글 개수']
        st.table(disp_w)
    else:
        st.info("필명 기준 기자 실적 없음")