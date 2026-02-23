import pandas as pd
import os
from datetime import datetime, timedelta
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Resource Definitions ---
GPUS = [
    {"id": "RTX-Server-0", "type": "RTX 4090"},
    {"id": "RTX-Server-1", "type": "RTX 4090"},
    {"id": "RTX-Server-2", "type": "RTX 4090"},
    {"id": "RTX-Server-3", "type": "RTX 4090"},
    {"id": "H100-01", "type": "H100"},
    {"id": "H100-02", "type": "H100"},
]

# --- User List ---
USERS = [
    "Mincheol Kang (강민철)", "Jeonghyeon Noh (노정현)", "Nakgyu Yang (양낙규)",
    "Jeongyong Yang (양정용)", "Sunmin Yoo (유선민)", "KwangBin Lee (이광빈)",
    "Yechan Lee (이예찬)", "Seunghwan 장승환", "Yejun Jang (장예준)",
    "Minseok Jeong (정민석)", "Jungyo Jung (정준교)", "Hyeongmin Choe (최형민)",
    "Hyewon Choi (최혜원)", "Doyoung Heo (허도영)"
]

# Initialize GSpread Connection
def get_gspread_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # Convert streamlit secrets to dict format expected by gspread
        creds_dict = {
            "type": st.secrets["connections"]["gsheets"]["type"],
            "project_id": st.secrets["connections"]["gsheets"]["project_id"],
            "private_key_id": st.secrets["connections"]["gsheets"]["private_key_id"],
            "private_key": st.secrets["connections"]["gsheets"]["private_key"].replace("\\n", "\n"),
            "client_email": st.secrets["connections"]["gsheets"]["client_email"],
            "client_id": st.secrets["connections"]["gsheets"]["client_id"],
            "auth_uri": st.secrets["connections"]["gsheets"]["auth_uri"],
            "token_uri": st.secrets["connections"]["gsheets"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["connections"]["gsheets"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["connections"]["gsheets"]["client_x509_cert_url"]
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Failed to authorize Google Sheets: {e}")
        return None

def get_worksheet():
    client = get_gspread_client()
    if not client: return None
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sh = client.open_by_url(url)
        return sh.get_worksheet(0) # First sheet
    except Exception as e:
        st.error(f"Failed to open spreadsheet: {e}")
        return None

def load_reservations():
    ws = get_worksheet()
    if ws is None:
        return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
    try:
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Start'] = pd.to_datetime(df['Start']).dt.tz_localize(None)
            df['End'] = pd.to_datetime(df['End']).dt.tz_localize(None)
        else:
            df = pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])

def check_conflicts(gpu_id, start_time, end_time, df=None):
    if df is None:
        df = load_reservations()
    if df.empty: return []
    
    gpu_res = df[df['GPU_ID'] == gpu_id]
    overlaps = gpu_res[
        (gpu_res['Start'] < pd.to_datetime(end_time).tz_localize(None)) & 
        (gpu_res['End'] > pd.to_datetime(start_time).tz_localize(None))
    ]
    return [f"{row['User']} ({row['Project']})" for _, row in overlaps.iterrows()]

def add_reservation(user, gpu_id, start_time, end_time, project, force=False):
    df = load_reservations()
    if not force:
        conflicts = check_conflicts(gpu_id, start_time, end_time, df=df)
        if conflicts: return False, f"Conflict detected: {', '.join(conflicts)}"
    
    gpu_type = next((g['type'] for g in GPUS if g['id'] == gpu_id), "Unknown")
    row = [
        user, gpu_id, gpu_type, 
        start_time.strftime('%Y-%m-%d %H:%M:%S'), 
        end_time.strftime('%Y-%m-%d %H:%M:%S'), 
        project
    ]
    
    try:
        ws = get_worksheet()
        if ws:
            ws.append_row(row)
            return True, "Reservation successful!"
        return False, "Could not access sheet for writing."
    except Exception as e:
        return False, f"Error saving to Sheet: {e}"

def delete_reservations(indices):
    try:
        ws = get_worksheet()
        if not ws: return False, "Could not access sheet."
        
        # indices are 0-based from dataframe, gspread rows are 1-based (and header is row 1)
        # So row to delete is index + 2
        # Delete in reverse to avoid index shifting
        for idx in sorted(indices, reverse=True):
            ws.delete_rows(idx + 2)
        return True, "Selected reservations deleted."
    except Exception as e:
        return False, f"Error deleting: {e}"

def get_occupancy_stats(target_date):
    df = load_reservations()
    if df.empty: return {"RTX 4090": 0.0, "H100": 0.0}
    
    day_start = pd.to_datetime(target_date).replace(hour=0, minute=0, second=0).tz_localize(None)
    day_end = day_start + pd.Timedelta(days=1)
    
    todays_res = df[(df['Start'] < day_end) & (df['End'] > day_start)]
    if todays_res.empty: return {"RTX 4090": 0.0, "H100": 0.0}

    rtx_count = todays_res[todays_res['GPU_Type'] == 'RTX 4090']['GPU_ID'].nunique()
    h100_count = todays_res[todays_res['GPU_Type'] == 'H100']['GPU_ID'].nunique()
    
    return {
        "RTX 4090": (rtx_count / 4.0) * 100,
        "H100": (h100_count / 2.0) * 100
    }
