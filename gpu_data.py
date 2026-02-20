import pandas as pd
import os
from datetime import datetime, timedelta
import streamlit as st
import requests
import json

# --- Resource Definitions ---
GPUS = [
    {"id": "RTX-Server-0", "type": "RTX 4090"},
    {"id": "RTX-Server-1", "type": "RTX 4090"},
    {"id": "RTX-Server-2", "type": "RTX 4090"},
    {"id": "RTX-Server-3", "type": "RTX 4090"},
    {"id": "H100-01", "type": "H100"},
    {"id": "H100-02", "type": "H100"},
]

# --- User List (ACSS LAB) ---
USERS = [
    "Mincheol Kang (강민철)",
    "Donggyu Kim (김동규)",
    "Jeonghyeon Noh (노정현)",
    "Sanghun Park (박상훈)",
    "Eunwoo Sung (성은우)",
    "Nakgyu Yang (양낙규)",
    "Jeongyong Yang (양정용)",
    "Sunmin Yoo (유선민)",
    "KwangBin Lee (이광빈)",
    "Yechan Lee (이예찬)",
    "Seunghwan 장승환",
    "Yejun Jang (장예준)",
    "Minseok Jeong (정민석)",
    "Jungyo Jung (정준교)",
    "Hojin Ju (주호진)",
    "Hyeongmin Choe (최형민)",
    "Hyewon Choi (최혜원)",
    "SooJean Han (한수진)",
    "Doyoung Heo (허도영)"
]

# Get Web App URL from Streamlit Secrets
API_URL = st.secrets.get("GOOGLE_APPS_SCRIPT_URL", "")

def load_reservations():
    if not API_URL:
        st.warning("Google Apps Script URL is not set in Secrets.")
        return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
    
    try:
        # Using GET to fetch data from Apps Script
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            if not df.empty:
                df['Start'] = pd.to_datetime(df['Start']).dt.tz_localize(None)
                df['End'] = pd.to_datetime(df['End']).dt.tz_localize(None)
            else:
                df = pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
            return df
        else:
            st.error(f"Error loading data: {response.text}")
            return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
    except Exception as e:
        st.error(f"Error connection to Apps Script: {e}")
        return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])

def check_conflicts(gpu_id, start_time, end_time):
    df = load_reservations()
    if df.empty:
        return []
    
    gpu_res = df[df['GPU_ID'] == gpu_id]
    overlaps = gpu_res[
        (pd.to_datetime(gpu_res['Start']).dt.tz_localize(None) < pd.to_datetime(end_time).tz_localize(None)) & 
        (pd.to_datetime(gpu_res['End']).dt.tz_localize(None) > pd.to_datetime(start_time).tz_localize(None))
    ]
    
    conflicts = []
    for _, row in overlaps.iterrows():
        conflicts.append(f"{row['User']} ({row['Project']})")
        
    return conflicts

def add_reservation(user, gpu_id, start_time, end_time, project, force=False):
    if not force:
        conflicts = check_conflicts(gpu_id, start_time, end_time)
        if conflicts:
            return False, f"Conflict detected with: {', '.join(conflicts)}"
        
    gpu_type = next((g['type'] for g in GPUS if g['id'] == gpu_id), "Unknown")
    
    new_entry = {
        "action": "add",
        "User": user,
        "GPU_ID": gpu_id,
        "GPU_Type": gpu_type,
        "Start": start_time.strftime('%Y-%m-%d %H:%M:%S'),
        "End": end_time.strftime('%Y-%m-%d %H:%M:%S'),
        "Project": project
    }
    
    try:
        response = requests.post(API_URL, data=json.dumps(new_entry))
        if response.status_code == 200:
            return True, "Reservation successful!"
        else:
            return False, f"Error saving: {response.text}"
    except Exception as e:
        return False, f"Connection error: {e}"

def delete_reservations(indices):
    """
    Deletes reservations by row index in the sheet.
    (Wait, Apps Script will need to handle the index logic)
    For simplicity, let's pass a list of row numbers to delete.
    Actually, it's safer to pass the whole row data or a unique ID.
    But let's assume index + 2 (since headers are row 1 and 0-index)
    """
    try:
        # Convert 0-based DataFrame index to 1-based Google Sheet row index (skipping header)
        # Sheet Rows: 1 (Header), 2, 3...
        # DF index: 0, 1, 2...
        # So Row = index + 2
        rows_to_delete = [idx + 2 for idx in indices]
        
        # We should delete from bottom to top to preserve indices, 
        # but our Apps Script can handle the list.
        payload = {
            "action": "delete",
            "rows": rows_to_delete
        }
        
        response = requests.post(API_URL, data=json.dumps(payload))
        if response.status_code == 200:
            return True, "Selected reservations deleted."
        else:
            return False, f"Error deleting: {response.text}"
    except Exception as e:
        return False, f"Error deleting: {str(e)}"

def get_occupancy_stats(target_date):
    df = load_reservations()
    if df.empty:
        return {"RTX 4090": 0.0, "H100": 0.0}
        
    day_start = pd.to_datetime(target_date).replace(hour=0, minute=0, second=0).tz_localize(None)
    day_end = day_start + pd.Timedelta(days=1)
    
    todays_res = df[
        (pd.to_datetime(df['Start']).dt.tz_localize(None) < day_end) & 
        (pd.to_datetime(df['End']).dt.tz_localize(None) > day_start)
    ]
    
    if todays_res.empty:
        return {"RTX 4090": 0.0, "H100": 0.0}

    stats = {}
    
    # RTX 4090 occupancy: (Unique RTX servers with reservations / 4) * 100
    rtx_reserved_count = todays_res[todays_res['GPU_Type'] == 'RTX 4090']['GPU_ID'].nunique()
    stats['RTX 4090'] = (rtx_reserved_count / 4.0) * 100
    
    # H100 occupancy: (Unique H100 servers with reservations / 2) * 100
    h100_reserved_count = todays_res[todays_res['GPU_Type'] == 'H100']['GPU_ID'].nunique()
    stats['H100'] = (h100_reserved_count / 2.0) * 100
    
    return stats
