import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from datetime import datetime, timedelta, timezone
from gpu_data import GPUS, USERS, load_reservations, add_reservation, delete_reservations, get_occupancy_stats, check_conflicts

# --- Timezone Setup ---
KST = timezone(timedelta(hours=9))
def get_now():
    return datetime.now(KST)

def get_today():
    return get_now().date()

st.set_page_config(page_title="ACSS GPUUsage", layout="wide", page_icon="⚙️")

# --- Custom CSS (Light/Standard Theme) ---
st.markdown("""
<style>
    /* Global Font Upgrade */
    html, body, [class*="st-"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 1.2rem !important;
    }
    
    /* Headers - Navy Blue */
    h1, h2, h3 {
        color: #0f3460 !important; /* Navy Blue */
    }
    
    /* Tabs - Rounded/Pill Style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        padding-bottom: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        border-radius: 20px; /* Rounded Pills */
        padding: 0px 20px;
        background-color: #f0f2f6;
        color: #31333F;
        font-weight: 600;
        border: 1px solid #d0d0d0;
        margin-bottom: 5px;
        font-size: 0.9rem !important; /* Smaller text for tabs */
    }
    .stTabs [aria-selected="true"] {
        background-color: #0f3460;
        color: white;
        border: 1px solid #0f3460;
    }
    
    /* Buttons */
    .stButton button {
        background-color: #0f3460;
        color: white;
        font-weight: bold;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("""
<div style='text-align: center; padding: 1rem 0 0.5rem 0;'>
    <h1 style='color: #0f3460; margin-bottom: 0.3rem; font-size: 2.5rem;'>🖥️ ACSS GPU Reservation System</h1>
    <p style='color: #666; font-size: 1.1rem; margin-top: 0;'>Autonomous Control for Stochastic Systems Lab</p>
    <p style='color: #888; font-size: 0.95rem; font-style: italic;'>Real-time GPU resource management and scheduling dashboard</p>
</div>
""", unsafe_allow_html=True)


# --- Tabs ---
# Container for tabs so they look nice
tab1, tab2, tab3, tab4 = st.tabs(["📅 Dashboard", "➕ Reserve GPU", "📚 Usage Guide", "🛠️ Management & Reservation Cancellation"])

# ==========================
# TAB 1: DASHBOARD
# ==========================
with tab1:
    # --- 1. Monthly Overview (Wall Calendar Style) ---
    st.subheader("Monthly Overview")
    
    col_date, col_cal = st.columns([1, 4])
    
    with col_date:
        if 'selected_date' not in st.session_state:
            st.session_state.selected_date = get_today()
            
        st.markdown(f"# {st.session_state.selected_date.strftime('%B %Y')}")
        st.caption("📅 Click on a day in the calendar to view details.")
        
        # Date selector
        selected_date_input = st.date_input(
            "Select date",
            value=st.session_state.selected_date,
            key="date_selector_left",
            label_visibility="collapsed"
        )
        if selected_date_input != st.session_state.selected_date:
            st.session_state.selected_date = selected_date_input
            st.rerun()

    with col_cal:
        df = load_reservations()
        
        # Prepare Calendar Data
        target_date = st.session_state.selected_date
        start_of_month = target_date.replace(day=1)
        next_month = (start_of_month + timedelta(days=32)).replace(day=1)
        
        dates_in_month = pd.date_range(start_of_month, next_month - timedelta(days=1))
        
        cal_data = []
        for d in dates_in_month:
            day_start = d
            day_end = d + timedelta(days=1)
            
            count = 0
            users = []
            if not df.empty:
                matches = df[
                    (df['Start'] < day_end) & (df['End'] > day_start)
                ]
                count = len(matches)
                users = matches['User'].unique().tolist()
            
            # Week of month calculation
            first_day_weekday = start_of_month.weekday() # 0=Mon
            day_of_month = d.day
            adjusted_day = day_of_month + first_day_weekday - 1
            week_of_month = adjusted_day // 7
            
            cal_data.append({
                'DateStr': d.strftime('%Y-%m-%d'),
                'Day': d.day,
                'Weekday_Str': d.strftime('%a'),
                'Week_Of_Month': week_of_month,
                'Count': count,
                'Users': "<br>".join(users) if users else ""
            })
            
        df_cal = pd.DataFrame(cal_data)
        weekday_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        # Heatmap
        fig_cal = go.Figure(data=go.Heatmap(
            x=df_cal['Weekday_Str'],
            y=df_cal['Week_Of_Month'],
            z=df_cal['Count'],
            text=df_cal['Day'],
            texttemplate="<b>%{text}</b>",
            hoverinfo='text',
            hovertemplate="<b>%{x} %{text}th</b><br>Reservations: %{z}<br>Users:<br>%{customdata[1]}<extra></extra>",
            customdata=df_cal[['DateStr', 'Users']].values.tolist(), 
            colorscale=[[0, 'white'], [1, '#e94560']],
            showscale=False,
            xgap=3,
            ygap=3
        ))
        
        fig_cal.update_layout(
            xaxis=dict(
                tickmode='array', tickvals=weekday_order, side='top', fixedrange=True
            ),
            yaxis=dict(
                visible=False, autorange="reversed", fixedrange=True
            ),
            margin=dict(t=30, b=10, l=10, r=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            clickmode='event+select' 
        )
        
        # Display clean heatmap only (no annotations)
        st.plotly_chart(
            fig_cal, 
            key="calendar_heatmap",
            use_container_width=True
        )

    st.divider()

    # --- 2. Daily Details (Vertical Timetable) ---
    target_date = st.session_state.selected_date
    st.subheader(f"⏱️ Timetable: {target_date.strftime('%Y-%m-%d')}")
    
    day_start = pd.Timestamp(target_date)
    day_end = day_start + timedelta(days=1)
    
    if not df.empty:
        day_df = df[
            (df['Start'] < day_end) & 
            (df['End'] > day_start)
        ].copy()
        
        if not day_df.empty:
            # Prepare Data for Bar Chart
            # Base = Start Hour (decimal)
            # Y = Duration (decimal hours)
            
            day_df['Clip_Start'] = day_df['Start'].clip(lower=day_start)
            day_df['Clip_End'] = day_df['End'].clip(upper=day_end)
            
            # Convert to decimal hours from midnight (0 to 24)
            def to_decimal_hours(dt):
                return dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            
            day_df['Start_Dec'] = day_df['Clip_Start'].apply(to_decimal_hours)
            day_df['End_Dec'] = day_df['Clip_End'].apply(to_decimal_hours)
            day_df['Duration_Dec'] = day_df['End_Dec'] - day_df['Start_Dec']
            
            # Create Figure
            fig_time = go.Figure()
            
            # Add bars for each reservation
            # Color by User? Or fixed color? Let's use User.
            # We iterate or use px? Go is more precise for 'base'.
            
            # Plotly Express Timeline is horizontal usually.
            # Go Bar with base is easiest for vertical.
            
            # Group by User to support legend if needed, or just add all traces.
            # Simple approach: one trace per row? No, too many traces.
            # One trace per User grouping?
            
            users_in_day = day_df['User'].unique()
            
            for u in users_in_day:
                u_data = day_df[day_df['User'] == u]
                fig_time.add_trace(go.Bar(
                    x=u_data['GPU_ID'],
                    y=u_data['Duration_Dec'],
                    base=u_data['Start_Dec'],
                    name=u,
                    text=u,
                    textposition="inside",
                    hovertemplate="<b>%{x}</b><br>Start: %{base:.2f}<br>Dur: %{y:.2f}h<br>Project: %{customdata}<extra></extra>",
                    customdata=u_data['Project']
                ))
                
            fig_time.update_layout(
                yaxis=dict(
                    range=[24, 0], # Reversed: 0 at top, 24 at bottom
                    tickmode='array',
                    tickvals=list(range(0, 25, 2)),
                    ticktext=[f"{h:02d}:00" for h in range(0, 25, 2)],
                    title="Time (00:00 - 24:00)",
                    showgrid=True,
                    gridcolor='lightgray',
                    ticklen=6,
                    tickwidth=1,
                    minor=dict(
                        ticklen=4,  
                        tick0=0,
                        dtick=1, # 1 hour minor grid
                        showgrid=True,
                        gridcolor='#f6f6f6'
                    )
                ),
                xaxis=dict(
                    title="Server",
                    categoryorder='array', 
                    categoryarray=[g['id'] for g in GPUS]
                ),
                barmode='overlay', # Or 'stack' if we handled conflicts? 'overlay' allows visual conflict detection.
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            c_chart, c_pie = st.columns([3, 1])
            with c_chart:
                st.plotly_chart(fig_time, use_container_width=True)
                
            with c_pie:
                st.markdown("#### Occupancy")
                stats = get_occupancy_stats(target_date)
                
                # Colors adapted for Light Theme
                colors_rtx = ['#e94560', '#f0f2f6'] 
                colors_h100 = ['#0f3460', '#f0f2f6'] 
                
                # RTX
                fig_rtx = go.Figure(data=[go.Pie(
                    labels=['Active', 'Idle'], 
                    values=[stats['RTX 4090'], 100 - stats['RTX 4090']], 
                    hole=.6, 
                    marker_colors=colors_rtx, 
                    textinfo='none'
                )])
                fig_rtx.update_layout(
                    title_text=f"RTX 4090<br><b>{stats['RTX 4090']:.0f}%</b>", 
                    title_x=0.5, title_y=0.5, showlegend=False, 
                    margin=dict(t=0,b=0,l=0,r=0), height=200
                )
                st.plotly_chart(fig_rtx, use_container_width=True)
                
                # H100
                fig_h = go.Figure(data=[go.Pie(
                    labels=['Active', 'Idle'], 
                    values=[stats['H100'], 100 - stats['H100']], 
                    hole=.6, 
                    marker_colors=colors_h100, 
                    textinfo='none'
                )])
                fig_h.update_layout(
                    title_text=f"H100<br><b>{stats['H100']:.0f}%</b>", 
                    title_x=0.5, title_y=0.5, showlegend=False, 
                    margin=dict(t=0,b=0,l=0,r=0), height=200
                )
                st.plotly_chart(fig_h, use_container_width=True)
        else:
            st.info("No reservations for this date.")
    else:
        st.info("No reservations in system.")

# ==========================
# TAB 2: RESERVE
# ==========================
with tab2:
    st.subheader("New Reservation")
    
    if 'booking_stage' not in st.session_state:
        st.session_state.booking_stage = 'input'
        
    with st.form("booking_form"):
        col1, col2 = st.columns(2)
        with col1:
            user = st.selectbox("User Name", USERS)
            project = st.text_input("Project Name")
        with col2:
            now_kst = get_now()
            start_d = st.date_input("Start Date", now_kst.date(), key="res_start_date")
            start_t = st.time_input("Start Time", now_kst.time(), key="res_start_time")
            end_d = st.date_input("End Date", now_kst.date(), key="res_end_date")
            end_t = st.time_input("End Time", (now_kst + timedelta(hours=2)).time(), key="res_end_time")
            
        st.divider()
        gpu_type = st.radio("Select GPU Type", ["RTX 4090", "H100"], horizontal=True)
        gpu_id_to_book = None
        
        if gpu_type == "RTX 4090":
            server_num = st.selectbox("Select Server Number", [0, 1, 2, 3])
            gpu_id_to_book = f"RTX-Server-{server_num}"
        else: 
            # H100 Selection: User wants 0, 1
            # Mapping 0 -> H100-01, 1 -> H100-02 (assuming 1-based internal IDs)
            unit_num = st.selectbox("Select Unit", [0, 1])
            gpu_id_to_book = f"H100-0{unit_num + 1}"
            
        submitted = st.form_submit_button("Check Availability")
        
    if submitted:
        start_dt = datetime.combine(start_d, start_t).replace(tzinfo=KST)
        end_dt = datetime.combine(end_d, end_t).replace(tzinfo=KST)
        now = get_now()
        
        if start_dt < now - timedelta(minutes=10):
            st.error(f"❌ Error: Start time must be in the future. (Current KST: {now.strftime('%H:%M')})")
        elif start_dt >= end_dt:
            st.error("❌ Error: End time must be after Start time.")
        else:
            conflicts = check_conflicts(gpu_id_to_book, start_dt, end_dt)
            if not conflicts:
                success, msg = add_reservation(user, gpu_id_to_book, start_dt, end_dt, project)
                if success:
                    st.success(msg)
                    st.cache_data.clear()
            else:
                st.session_state.conflicts = conflicts
                st.session_state.pending_booking = {
                    'user': user, 'gpu': gpu_id_to_book, 
                    'start': start_dt, 'end': end_dt, 'project': project
                }
                
    if 'conflicts' in st.session_state and st.session_state.conflicts:
        st.warning(f"⚠️ Conflict Detected! Slot occupied by:\n" + "\n".join([f"- {c}" for c in st.session_state.conflicts]))
        st.write("Force book this slot?")
        c1, c2 = st.columns(2)
        if c1.button("✅ Confirm"):
            d = st.session_state.pending_booking
            success, msg = add_reservation(d['user'], d['gpu'], d['start'], d['end'], d['project'], force=True)
            if success:
                st.success(f"Forced Booking Confirmed! {msg}")
                del st.session_state.conflicts
                del st.session_state.pending_booking
                st.cache_data.clear()
                st.rerun()
        if c2.button("❌ Cancel"):
            del st.session_state.conflicts
            del st.session_state.pending_booking
            st.rerun()

# ==========================
# FOOTER
# ==========================
st.divider()
st.markdown("<div style='text-align: center; color: gray;'>This is GPU reservation & status timetable for ACSS</div>", unsafe_allow_html=True)

# ==========================
# TAB 3: USAGE GUIDE
# ==========================
with tab3:
    st.header("📚 User Guide")
    col_h100, col_rtx = st.columns(2)
    with col_h100:
        st.subheader("☁️ H100 Server (KT Cloud)")
        st.markdown("""
        **User Info**: KAIST (Sujin Han)  
        **Specs**: H100 * 2 | CPU 16core | RAM 128GB | SSD 2TB
        
        ---
        **Access Information**
        - **URL**: [www.aitrain.ktcloud.com](http://www.aitrain.ktcloud.com)
        - **ID**: `nipa-gpu2025-124@ktcloud.com`
        - **Initial Password**: `acss1234@`
        
        **Contact**  
        Content Bridge Hybrid MSP Tech Team  
        T: 070-4291-7005
        """)
    with col_rtx:
        st.subheader("🖥️ RTX 4090 Server (Local)")
        st.markdown("""
        **Location**: N5, Room 2154  
        **Specs**: RTX 4090 * 4 | CPU 64core | RAM 256GB | SSD 4TB
        
        ---
        **How to Connect**
        ```bash
        ssh -p 22 compu@143.248.102.25
        ```
        **Password**: `!@#$`
        
        **Usage Tips**
        - Check GPU availability: `nvidia-smi`
        - Monitor GPU usage: `watch -n 1 nvidia-smi`
        - Use tmux for long-running jobs: `tmux new -s session_name`
        - Activate conda environment before running experiments
        
        **Important Notes**
        - Please respect other users' reserved time slots
        - Clean up temporary files after experiments
        - Report any hardware issues to the lab manager
        """)


# ==========================
# TAB 4: MANAGEMENT & RESERVATION CANCELLATION
# ==========================
with tab4:
    st.header("🛠️ Management & Reservation Cancellation")
    st.markdown("Select reservations to **Delete/Cancel**.")
    
    df_manage = load_reservations()
    if not df_manage.empty:
        # Sort by latest
        df_manage = df_manage.sort_values(by="Start", ascending=False).reset_index(drop=True)
        
        # Add Checkbox
        df_manage['Select'] = False
        
        # We need to map back to original indices if we sorted, or just use the filtered logic carefully.
        # Simpler approach: Display data_editor with full data, let user select.
        # But if we sort, the index changes.
        # Let's reload without sort for deletion safety, or include original ID if we had one.
        # For V1: Just show raw dataframe (it's safe enough for small team).
        
        edited_df = st.data_editor(
            df_manage, 
            column_config={
                "Select": st.column_config.CheckboxColumn("Delete?", default=False)
            },
            hide_index=False,
            use_container_width=True,
            num_rows="fixed" 
        )
        
        if st.button("🗑️ Delete Selected Rows"):
            # Identify rows where 'Select' is True
            to_delete = edited_df[edited_df['Select']].index.tolist()
            
            if to_delete:
                success, msg = delete_reservations(to_delete)
                if success:
                    st.success(f"Deleted {len(to_delete)} reservations.")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.info("No rows selected.")
            
    else:
        st.info("No reservations to manage.")
