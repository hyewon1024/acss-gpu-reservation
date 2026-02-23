import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("GSheets Connection Test")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    st.write("### Current Data in Sheet:")
    st.dataframe(df)

    if st.button("Add Test Row"):
        new_row = pd.DataFrame([{
            "User": "Test User",
            "GPU_ID": "Test-GPU",
            "GPU_Type": "Test-Type",
            "Start": "2024-01-01 10:00:00",
            "End": "2024-01-01 12:00:00",
            "Project": "Test project"
        }])
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(data=updated_df)
        st.success("Test row added!")
        st.rerun()

except Exception as e:
    st.error(f"Error: {e}")
