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
def render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count=0):
    st.markdown('<div class="section-header-container first-section"><div class="section-header">1. 주간 전체 성과 요약</div></div>', unsafe_allow_html=True)
    pv_per_user = round(cur_pv/cur_uv, 1) if cur_uv > 0 else 0
    
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
        v_f = f"{v:,}" if isinstance(v, (int, np.integer, float)) and l not in ["방문자당 페이지뷰", "신규 방문자 비율", "검색 유입 비율"] else str(v)
        cols[i].markdown(f'<div class="kpi-container"><div class="kpi-label">{l}</div><div class="kpi-value">{v_f}<span class="kpi-unit">{u}</span></div></div>', unsafe_allow_html=True)
        
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sub-header">📊 주간 일별 방문 추이</div>', unsafe_allow_html=True)
        if not df_daily.empty:
            fig = px.bar(df_daily.melt(id_vars='날짜'), x='날짜', y='value', color='variable', barmode='group', color_discrete_map={'UV': COLOR_GREY, 'PV': COLOR_NAVY})
            fig.update_xaxes(type='category')
            fig.update_layout(legend_title_text=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True, key="summary_daily_chart")
    with c2:
        st.markdown('<div class="sub-header">📈 최근 3달 간 추이 분석</div>', unsafe_allow_html=True)
        if not df_weekly.empty:
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=df_weekly['주차'], y=df_weekly['UV'], name='UV', marker_color=COLOR_GREY))
            fig2.add_trace(go.Bar(x=df_weekly['주차'], y=df_weekly['PV'], name='PV', marker_color=COLOR_NAVY))
            
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
            
            fig2.update_layout(barmode='group', plot_bgcolor='white', margin=dict(t=30), yaxis=dict(tickformat=","), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
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
    
    st.dataframe(df_m[['유입경로', '이번주 비중', '지난주 비중', '비중 변화']].copy().assign(**{'비중 변화': lambda x: x['비중 변화'].apply(lambda v: f"{v:+.1f}%p")}), use_container_width=True, hide_index=True)

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
        st.dataframe(df_disp[['구분', '이번주(%)', '지난주(%)', '변화(%p)']], use_container_width=True, hide_index=True)

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
            st.dataframe(df_disp[['구분', '이번주(%)', '지난주(%)', '변화(%p)']], use_container_width=True, hide_index=True)
        st.markdown("<hr>", unsafe_allow_html=True)

# ----------------- 4. Top 10 상세 -----------------
def render_top10_detail(df_top10):
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
            '최다유입': '최다 유입경로'
        })
        cols = ['순위','카테고리','세부카테고리','제목','작성자','발행일시','최근 7일간 조회수','최근 7일간 방문자수','신규방문자비율','최다 유입경로','체류시간','좋아요','댓글']
        st.dataframe(df_p4_display[cols], use_container_width=True, hide_index=True)

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
            
        st.dataframe(df_p5[cols], use_container_width=True, hide_index=True)
        
        if df_top10_sources is not None and not df_top10_sources.empty:
            path_to_title = dict(zip(df_top10['경로'], df_top10['제목']))
            df_src = df_top10_sources.copy()
            df_src['기사제목'] = df_src['pagePath'].map(path_to_title).fillna('기타')
            
            df_src['기사제목_short'] = df_src['기사제목'].apply(lambda x: x[:10] + '...' if len(str(x)) > 10 else str(x))
            
            short_titles_ordered = [t[:10] + '...' if len(str(t)) > 10 else str(t) for t in df_top10['제목'].tolist()]
            short_titles_ordered.reverse()
            
            fig = px.bar(
                df_src, 
                x='screenPageViews',   
                y='기사제목_short',     
                color='유입경로',
                text='screenPageViews',
                title='기사별 유입경로 비중',
                orientation='h',       
                color_discrete_sequence=CHART_PALETTE,
                hover_data={'top_detail': True, 'screenPageViews': True, '기사제목': True, '기사제목_short': False}
            )
            
            fig.update_traces(hovertemplate='<b>%{y}</b><br>유입경로: %{legendgroup}<br>상세경로: %{customdata[0]}<br>조회수: %{x}<extra></extra>')
            
            fig.update_layout(
                plot_bgcolor='white',
                xaxis_title='조회수',
                yaxis_title='기사 (요약)',
                legend_title_text='유입경로'
            )
            fig.update_yaxes(categoryorder='array', categoryarray=short_titles_ordered)
            
            st.plotly_chart(fig, use_container_width=True, key="top10_source_distribution_chart")
        else:
            st.warning("기사별 유입경로 상세 데이터가 없습니다.")

# ----------------- 6. 카테고리 -----------------
def render_category(df_top10):
    st.markdown('<div class="section-header-container"><div class="section-header">6. 카테고리별 분석</div></div>', unsafe_allow_html=True)
    if not df_top10.empty:
        df_real = df_top10
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
        st.dataframe(cat_main[['카테고리', '기사수', '전체조회수', '평균조회수']], use_container_width=True, hide_index=True)

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
        st.dataframe(cat_sub[['카테고리', '세부카테고리', '기사수', '전체조회수', '평균조회수']], use_container_width=True, hide_index=True)
        
        # [수정] 각주 추가
        st.markdown("<div style='font-size: 0.85rem; color: #78909c; margin-top: 5px;'>* 평균조회수: 카테고리 전체 조회수 ÷ 카테고리 기사 수</div>", unsafe_allow_html=True)

# ----------------- 7. 기자 (본명) -----------------
def render_writer_real(writers_df):
    st.markdown('<div class="section-header-container"><div class="section-header">7. 이번주 기자별 분석 (본명 기준)</div></div>', unsafe_allow_html=True)
    if not writers_df.empty:
        disp_w = writers_df.copy()
        for c in ['총조회수','평균조회수','좋아요','댓글']: disp_w[c] = disp_w[c].apply(lambda x: f"{x:,}")
        disp_w = disp_w[['순위', '작성자', '필명', '기사수', '총조회수', '평균조회수', '좋아요', '댓글']]
        disp_w.columns = ['순위', '본명', '필명', '발행기사 수', '전체 조회 수', '기사 1건 당 평균 조회 수', '좋아요 개수', '댓글 개수']
        st.dataframe(disp_w, use_container_width=True, hide_index=True)

# ----------------- 8. 기자 (필명) -----------------
def render_writer_pen(writers_df):
    st.markdown('<div class="section-header-container"><div class="section-header">8. 이번주 기자별 분석 (필명 기준)</div></div>', unsafe_allow_html=True)
    if not writers_df.empty:
        df_pen = writers_df[writers_df['필명'] != ''].copy()
        if not df_pen.empty:
            df_pen['순위'] = df_pen['총조회수'].rank(method='min', ascending=False).astype(int)
            df_pen = df_pen.sort_values('순위')
            disp_w = df_pen.copy()
            for c in ['총조회수','평균조회수','좋아요','댓글']: disp_w[c] = disp_w[c].apply(lambda x: f"{x:,}")
            disp_w = disp_w[['순위', '필명', '작성자', '기사수', '총조회수', '평균조회수', '좋아요', '댓글']]
            disp_w.columns = ['순위', '필명', '본명', '발행기사 수', '전체 조회 수', '기사 1건 당 평균 조회 수', '좋아요 개수', '댓글 개수']
            st.dataframe(disp_w, use_container_width=True, hide_index=True)
        else: st.info("필명 기자 실적 없음")