# auth.py
import streamlit as st
import json
import os
from google.oauth2 import service_account 
from google.analytics.data_v1beta import BetaAnalyticsDataClient

def check_password():
    """비밀번호 입력 및 검증"""
    if st.session_state.get("password_correct", False):
        return True

    login_placeholder = st.empty()
    with login_placeholder.container():
        st.markdown(
            """
            <style>
            .login-container { max-width: 400px; margin: 100px auto; padding: 40px; text-align: center; }
            .login-title { font-size: 24px; font-weight: 700; color: #1a237e; margin-bottom: 20px; text-align: center; }
            .powered-by { font-size: 12px; color: #90a4ae; margin-top: 50px; font-weight: 500; }
            .stTextInput > div > div > input { text-align: center; font-size: 18px; letter-spacing: 2px; }
            </style>
            """, unsafe_allow_html=True
        )
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.markdown('<div style="margin-top: 100px;"></div>', unsafe_allow_html=True)
            st.markdown('<div class="login-title">🔒 쿡앤셰프 주간 성과보고서</div>', unsafe_allow_html=True)
            password = st.text_input("Access Code", type="password", key="password_input", label_visibility="collapsed")
            if password:
                if password == "cncnews2026":
                    st.session_state["password_correct"] = True
                    login_placeholder.empty()
                    st.rerun()
                else:
                    st.error("🚫 코드가 올바르지 않습니다.")
            
            st.markdown('<div class="powered-by">Powered by DWG Inc.</div>', unsafe_allow_html=True)
            
    return False

@st.cache_resource
def get_ga4_client():
    """GA4 클라이언트 생성 (캐싱 적용)"""
    try:
        # 로컬 환경: JSON 파일에서 읽기
        json_path = "ga-key.json"
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                key_dict = json.load(f)
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return BetaAnalyticsDataClient(credentials=creds)
        
        # Streamlit Cloud: secrets에서 읽기
        try:
            key_dict = st.secrets["ga4_credentials"]
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return BetaAnalyticsDataClient(credentials=creds)
        except:
            pass
        
        # 환경 변수에서 읽기 (선택사항)
        ga4_creds_env = os.getenv("GA4_CREDENTIALS_JSON")
        if ga4_creds_env:
            key_dict = json.loads(ga4_creds_env)
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return BetaAnalyticsDataClient(credentials=creds)
        
        st.error("GA4 인증 정보를 찾을 수 없습니다. ga-key.json 파일을 확인하세요.")
        return None
    except Exception as e:
        st.error(f"GA4 클라이언트 연결 실패: {e}")
        return None