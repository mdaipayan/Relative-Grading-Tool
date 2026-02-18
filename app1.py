import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime
import altair as alt

# ==========================================
# 1. DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect('semester_data.db')
    c = conn.cursor()
    # Table for raw mark entries
    c.execute('''CREATE TABLE IF NOT EXISTS marks_entry (
                    student_id TEXT,
                    subject_code TEXT,
                    subject_name TEXT,
                    credits INTEGER,
                    course_type TEXT,
                    total_max INTEGER,
                    ese_max INTEGER,
                    marks INTEGER,
                    ese_marks TEXT,
                    attendance INTEGER,
                    faculty_name TEXT,
                    timestamp TEXT,
                    PRIMARY KEY (student_id, subject_code)
                 )''')
    conn.commit()
    conn.close()

def save_mark_to_db(data):
    conn = sqlite3.connect('semester_data.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO marks_entry 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()

def get_all_marks_from_db():
    conn = sqlite3.connect('semester_data.db')
    df = pd.read_sql_query("SELECT * FROM marks_entry", conn)
    conn.close()
    return df

# Initialize DB on startup
init_db()

# ==========================================
# 2. GRADING ENGINE (Same logic as before)
# ==========================================
# [Include the StrictUniversityGrading and apply_grace_criteria classes/functions here]

# ==========================================
# 3. FACULTY ENTRY PORTAL
# ==========================================
def faculty_interface():
    st.title("📝 Faculty Mark Entry Portal")
    
    # Configuration for subjects (This could also be moved to a DB table)
    subjects_config = {
        "CE101": {"name": "Maths-III", "credits": 3, "type": "Theory", "total_max": 100, "ese_max": 60},
        "CE102": {"name": "Fluid Mechanics", "credits": 4, "type": "Theory", "total_max": 100, "ese_max": 60},
        "CE107": {"name": "Fluid Lab", "credits": 1, "type": "Practical", "total_max": 50, "ese_max": 30},
    }

    with st.expander("Submit Individual Marks", expanded=True):
        with st.form("single_entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            faculty_name = col1.text_input("Faculty Name / ID")
            sub_code = col2.selectbox("Subject Code", list(subjects_config.keys()))
            
            st.divider()
            
            c1, c2, c3, c4 = st.columns(4)
            student_id = c1.text_input("Student Roll No")
            total_marks = c2.number_input("Total Marks (IA + ESE)", min_value=0, max_value=100)
            ese_marks = c3.text_input("ESE Marks (Numeric or 'AB')")
            attendance = c4.slider("Attendance %", 0, 100, 75)
            
            if st.form_submit_button("Save Entry"):
                if not student_id or not faculty_name:
                    st.error("Please provide Student ID and Faculty Name.")
                else:
                    conf = subjects_config[sub_code]
                    data = (student_id, sub_code, conf['name'], conf['credits'], 
                            conf['type'], conf['total_max'], conf['ese_max'], 
                            total_marks, ese_marks, attendance, faculty_name, 
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    save_mark_to_db(data)
                    st.success(f"Record saved for {student_id} in {sub_code}")

    st.divider()
    st.subheader("Your Recent Submissions")
    current_data = get_all_marks_from_db()
    if not current_data.empty:
        st.dataframe(current_data.tail(10), use_container_width=True)

# ==========================================
# 4. ADMIN DASHBOARD
# ==========================================
def admin_interface():
    st.title("🛡️ Examination Admin Dashboard")
    
    data = get_all_marks_from_db()
    
    if data.empty:
        st.warning("No data found in the database. Awaiting faculty submissions.")
        return

    # Progress Tracking
    st.subheader("Subject-wise Submission Progress")
    progress = data.groupby('subject_code')['student_id'].count().reset_index()
    progress.columns = ['Subject', 'Entries Count']
    st.table(progress)

    

    if st.button("🚀 Process Final Semester Results", type="primary"):
        # Run the Grading Engine logic on 'data'
        st.info("Aggregating data and applying Protocol A logic...")
        # [Implementation of final grading and SGPA calculation]
        st.success("Semester Results Generated!")

# ==========================================
# 5. MAIN NAVIGATION
# ==========================================
def main():
    st.sidebar.title("University ERP")
    page = st.sidebar.radio("Navigate to:", ["Faculty Entry", "Admin Dashboard"])
    
    if page == "Faculty Entry":
        faculty_interface()
    else:
        admin_interface()

if __name__ == "__main__":
    main()
