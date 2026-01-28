# views.py
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
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
        if limit_labels and len(df_normal) > limit_labels:
            top_df = df_normal.head(limit_labels)
            other_val = df_normal.iloc[limit_labels:][values].sum()
            other_df = pd.DataFrame([{'구분': '기타', values: other_val}])
            df_plot = pd.concat([top_df, other_df])
        else:
            df_plot = df
    else:
        df_plot = df

    fig = px.pie(df_plot, names=names, values=values, hole=0.5, color=names,
                 color_discrete_map=color_map if color_map else None,
                 color_discrete_sequence=CHART_PALETTE)
    
    fig.update_traces(textinfo='percent+label', textposition='outside', rotation=rotation)
    fig.update_layout(showlegend=show_legend, margin=final_margin, height=height)
    return fig

# ----------------- 1. 성과 요약 -----------------
def render_summary(df_weekly, cur_pv, cur_uv, new_ratio, search_ratio, df_daily, active_article_count, published_article_count):
    st.markdown('<div class="section-header-container"><div class="section-header">1. 주간 성과 요약</div></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("전체 조회수 (PV)", f"{cur_pv:,}")
    with c2: st.metric("순 방문자수 (UV)", f"{cur_uv:,}")
    with c3: st.metric("신규 방문자 비중", f"{new_ratio:.1f}%")
    with c4: st.metric("검색 유입 비중", f"{search_ratio:.1f}%")

    c5, c6 = st.columns(2)
    with c5: st.metric("운영 기사 수", f"{active_article_count:,}건")
    with c6: st.metric("금주 발행 기사 수", f"{published_article_count:,}건")

    if not df_daily.empty:
        fig = px.line(df_daily, x='날짜', y='조회수', title="일별 조회수 추이", markers=True)
        fig.update_traces(line_color=COLOR_NAVY)
        st.plotly_chart(fig, use_container_width=True)

# ----------------- 2. 접근 경로 -----------------
def render_traffic(df_curr, df_last):
    st.markdown('<div class="section-header-container"><div class="section-header">2. 채널별 접근 경로</div></div>', unsafe_allow_html=True)
    if not df_curr.empty:
        fig = create_donut_chart_with_val(df_curr, '구분', '조회수', show_legend=True)
        st.plotly_chart(fig, use_container_width=True)

# ----------------- 3. 방문자 특성 (지역) -----------------
def render_demo_region(df_curr, df_last):
    st.markdown('<div class="section-header-container"><div class="section-header">3. 방문자 특성 - 지역</div></div>', unsafe_allow_html=True)
    if not df_curr.empty:
        fig = px.bar(df_curr.head(10), x='조회수', y='구분', orientation='h', title="TOP 10 지역")
        fig.update_traces(marker_color=COLOR_NAVY)
        st.plotly_chart(fig, use_container_width=True)

# ----------------- 3. 방문자 특성 (성별/연령) -----------------
def render_demo_age_gender(df_age_curr, df_age_last, df_gender_curr, df_gender_last):
    st.markdown('<div class="section-header-container"><div class="section-header">3. 방문자 특성 - 연령 및 성별</div></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if not df_age_curr.empty:
            fig_age = px.bar(df_age_curr, x='구분', y='조회수', title="연령대별 분포")
            fig_age.update_traces(marker_color=COLOR_RED)
            st.plotly_chart(fig_age, use_container_width=True)
    with col2:
        if not df_gender_curr.empty:
            fig_gen = create_donut_chart_with_val(df_gender_curr, '구분', '조회수', color_map=COLOR_GENDER, show_legend=True)
            st.plotly_chart(fig_gen, use_container_width=True)

# ----------------- 4. Top 10 상세 -----------------
def render_top10_detail(df_top10, df_published_top10):
    st.markdown('<div class="section-header-container"><div class="section-header">4. 주간 콘텐츠 TOP 10 상세</div></div>', unsafe_allow_html=True)
    if not df_top10.empty:
        disp_df = df_top10.copy()
        for c in ['조회수', '사용자', '좋아요', '댓글']:
            if c in disp_df.columns:
                disp_df[c] = disp_df[c].apply(lambda x: f"{x:,}")
        st.dataframe(disp_df[['순위', '제목', '작성자', '카테고리', '조회수', '사용자']], use_container_width=True, hide_index=True)

# ----------------- 5. Top 10 추이 -----------------
def render_top10_trends(df_top10, df_top10_sources):
    st.markdown('<div class="section-header-container"><div class="section-header">5. TOP 10 콘텐츠 노출 추이</div></div>', unsafe_allow_html=True)
    if not df_top10.empty:
        fig = px.line(df_top10_sources, x='날짜', y='조회수', color='제목', markers=True)
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5))
        st.plotly_chart(fig, use_container_width=True)

# ----------------- 6. 카테고리 분석 -----------------
def render_category(df):
    st.markdown('<div class="section-header-container"><div class="section-header">6. 카테고리별 분석</div></div>', unsafe_allow_html=True)
    if not df.empty:
        # 컬럼명 확인 및 매핑
        value_col = '전체조회수' if '전체조회수' in df.columns else ('screenPageViews' if 'screenPageViews' in df.columns else None)
        if value_col and '카테고리' in df.columns:
            # 메인 카테고리
            cat_main = df.groupby('카테고리').agg(기사수=('제목','count') if '제목' in df.columns else ('pageTitle','count'), 전체조회수=(value_col,'sum')).reset_index()
            total_main = cat_main['기사수'].sum()
            cat_main['기사수'] = cat_main.apply(lambda x: f"{x['기사수']} ({x['기사수']/total_main*100:.1f}%)", axis=1)
            cat_main['전체조회수'] = pd.to_numeric(cat_main['전체조회수'], errors='coerce').fillna(0)
            cat_main['기사수_num'] = cat_main['기사수'].apply(lambda x: int(x.split('(')[0]))
            cat_main['평균조회수'] = (cat_main['전체조회수'] / cat_main['기사수_num']).astype(int).map('{:,}'.format)
            cat_main['전체조회수'] = cat_main['전체조회수'].map('{:,}'.format)
            
            st.markdown('<div class="chart-header">1. 메인 카테고리별 기사 수</div>', unsafe_allow_html=True)
            st.plotly_chart(px.bar(cat_main, x='카테고리', y='기사수_num', text_auto=True, color='카테고리', color_discrete_sequence=CHART_PALETTE).update_layout(showlegend=False, plot_bgcolor='white', yaxis_title="기사수"), use_container_width=True, key="category_main_chart")
            st.dataframe(cat_main[['카테고리', '기사수', '전체조회수', '평균조회수']], use_container_width=True, hide_index=True)

            # 세부 카테고리
            if '세부카테고리' in df.columns:
                st.markdown('<div class="chart-header">2. 세부 카테고리별 기사 수</div>', unsafe_allow_html=True)
                cat_sub = df.groupby(['카테고리', '세부카테고리']).agg(기사수=('제목','count') if '제목' in df.columns else ('pageTitle','count'), 전체조회수=(value_col,'sum')).reset_index()
                total_sub = cat_sub['기사수'].sum()
                cat_sub['기사수'] = cat_sub.apply(lambda x: f"{x['기사수']} ({x['기사수']/total_sub*100:.1f}%)", axis=1)
                cat_sub['전체조회수'] = pd.to_numeric(cat_sub['전체조회수'], errors='coerce').fillna(0)
                cat_sub['기사수_num'] = cat_sub['기사수'].apply(lambda x: int(x.split('(')[0]))
                cat_sub['평균조회수'] = (cat_sub['전체조회수'] / cat_sub['기사수_num']).astype(int).map('{:,}'.format)
                cat_sub['전체조회수'] = cat_sub['전체조회수'].map('{:,}'.format)
                
                st.plotly_chart(px.bar(cat_sub, x='세부카테고리', y='기사수_num', text_auto=True, color='카테고리', color_discrete_sequence=CHART_PALETTE).update_layout(plot_bgcolor='white', yaxis_title="기사수"), use_container_width=True, key="category_sub_chart")
                st.dataframe(cat_sub[['카테고리', '세부카테고리', '기사수', '전체조회수', '평균조회수']], use_container_width=True, hide_index=True)

# ----------------- 7. 기자별 분석 (본명/필명 분리 렌더링) -----------------
def render_writer_analysis(writers_df_real, writers_df_pen):
    st.markdown('<div class="section-header-container"><div class="section-header">7. 기자별 분석</div></div>', unsafe_allow_html=True)
    
    # 공통 숫자 포맷팅 헬퍼
    def format_writer_table(df):
        if df.empty: return df
        df = df.copy()
        for c in ['총조회수','평균조회수','좋아요','댓글']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0).astype(int).apply(lambda x: f"{x:,}")
        return df

    # (1) 본명 기준 순위
    st.markdown('<div class="sub-header">1) 본명 기준 순위</div>', unsafe_allow_html=True)
    if not writers_df_real.empty:
        disp_real = format_writer_table(writers_df_real)
        mapping = {'순위': '순위', '작성자': '기자명(본명)', '기사수': '발행기사 수', '총조회수': '전체 조회수', '평균조회수': '기사당 평균 조회수', '좋아요': '좋아요', '댓글': '댓글'}
        available_cols = [c for c in mapping.keys() if c in disp_real.columns]
        disp_real = disp_real[available_cols]
        disp_real.columns = [mapping[c] for c in available_cols]
        st.dataframe(disp_real, use_container_width=True, hide_index=True)
    else:
        st.info("본명 기준 분석 데이터가 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    # (2) 필명 기준 순위
    st.markdown('<div class="sub-header">2) 필명 기준 순위</div>', unsafe_allow_html=True)
    if not writers_df_pen.empty:
        disp_pen = format_writer_table(writers_df_pen)
        mapping_pen = {'순위': '순위', '작성자': '필명', '기사수': '발행기사 수', '총조회수': '전체 조회수', '평균조회수': '기사당 평균 조회수', '좋아요': '좋아요', '댓글': '댓글'}
        available_cols_pen = [c for c in mapping_pen.keys() if c in disp_pen.columns]
        disp_pen = disp_pen[available_cols_pen]
        disp_pen.columns = [mapping_pen[c] for c in available_cols_pen]
        st.dataframe(disp_pen, use_container_width=True, hide_index=True)
    else:
        st.info("필명 기준 분석 데이터가 없습니다.")
