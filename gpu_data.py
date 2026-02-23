import pandas as pd
import os
from datetime import datetime, timedelta
import streamlit as st
from streamlit_gsheets import GSheetsConnection

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
    "Jeonghyeon Noh (노정현)",
    "Nakgyu Yang (양낙규)",
    "Jeongyong Yang (양정용)",
    "Sunmin Yoo (유선민)",
    "KwangBin Lee (이광빈)",
    "Yechan Lee (이예찬)",
    "Seunghwan 장승환",
    "Yejun Jang (장예준)",
    "Minseok Jeong (정민석)",
    "Jungyo Jung (정준교)",
    "Hyeongmin Choe (최형민)",
    "Hyewon Choi (최혜원)",
    "Doyoung Heo (허도영)"
]

# Initialize Google Sheets Connection
def get_connection():
    # Attempt to get configuration from secrets
    config = st.secrets.get("connections", {}).get("gsheets", {})
    url = config.get("spreadsheet") or config.get("url")
    
    if not url:
        st.error("Google Sheets URL not found in secrets.toml ([connections.gsheets])")
        return None
    
    try:
        # Try passing both to be absolutely sure
        return st.connection("gsheets", type=GSheetsConnection, spreadsheet=url, url=url)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return st.connection("gsheets", type=GSheetsConnection)

conn = get_connection()

def load_reservations():
    if conn is None:
        return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
    try:
        # TTL set to 0 to ensure we always get the latest data for reservations
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            # Ensure proper datetime conversion
            df['Start'] = pd.to_datetime(df['Start']).dt.tz_localize(None)
            df['End'] = pd.to_datetime(df['End']).dt.tz_localize(None)
        else:
            df = pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame(columns=["User", "GPU_ID", "GPU_Type", "Start", "End", "Project"])

def check_conflicts(gpu_id, start_time, end_time):
    df = load_reservations()
    if df.empty:
        return []
    
    gpu_res = df[df['GPU_ID'] == gpu_id]
    overlaps = gpu_res[
        (gpu_res['Start'] < pd.to_datetime(end_time).tz_localize(None)) & 
        (gpu_res['End'] > pd.to_datetime(start_time).tz_localize(None))
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
    
    new_entry = pd.DataFrame([{
        "User": user,
        "GPU_ID": gpu_id,
        "GPU_Type": gpu_type,
        "Start": start_time.strftime('%Y-%m-%d %H:%M:%S'),
        "End": end_time.strftime('%Y-%m-%d %H:%M:%S'),
        "Project": project
    }])
    
    try:
        # Read current data and append
        existing_df = load_reservations()
        updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
        conn.update(data=updated_df)
        return True, "Reservation successful!"
    except Exception as e:
        return False, f"Error saving to Google Sheets: {e}"

def delete_reservations(indices):
    try:
        df = load_reservations()
        if df.empty:
            return False, "No data to delete."
        
        # Drop the selected rows
        df = df.drop(indices).reset_index(drop=True)
        
        # update() will overwrite the entire sheet with the new dataframe
        conn.update(data=df)
        return True, "Selected reservations deleted."
    except Exception as e:
        return False, f"Error deleting from Google Sheets: {str(e)}"

def get_occupancy_stats(target_date):
    df = load_reservations()
    if df.empty:
        return {"RTX 4090": 0.0, "H100": 0.0}
        
    day_start = pd.to_datetime(target_date).replace(hour=0, minute=0, second=0).tz_localize(None)
    day_end = day_start + pd.Timedelta(days=1)
    
    todays_res = df[
        (df['Start'] < day_end) & 
        (df['End'] > day_start)
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
