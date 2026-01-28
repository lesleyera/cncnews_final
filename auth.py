# auth.py
import json
import os
import streamlit as st
from google.oauth2 import service_account 
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from functools import lru_cache

def check_password():
    """사용자 인증 함수 (Streamlit Secrets 활용)"""
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input("비밀번호를 입력하세요", type="password", on_change=password_entered, key="password")
    if "password_correct" in st.session_state:
        st.error("😕 비밀번호가 일치하지 않습니다.")
    return False

@lru_cache(maxsize=1)
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
        
        # 환경 변수에서 읽기 (선택사항)
        ga4_creds_env = os.getenv("GA4_CREDENTIALS_JSON")
        if ga4_creds_env:
            key_dict = json.loads(ga4_creds_env)
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return BetaAnalyticsDataClient(credentials=creds)
        
        return None
    except Exception as e:
        return None
