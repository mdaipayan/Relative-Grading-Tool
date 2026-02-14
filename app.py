import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ==========================================
# 1. CORE GRADING LOGIC
# ==========================================
class StrictUniversityGrading:
    def __init__(self, total_max_marks=100, ese_max_marks=60, course_type='Theory', protocol='Protocol A'):
        self.M = total_max_marks       
        self.ESE_M = ese_max_marks     
        self.type = course_type
        self.protocol = protocol  # Store the selected protocol
        
        # Define Pass Marks (P) based on Total Marks
        if self.type == 'Practical':
            self.P = 0.50 * self.M 
        else:
            self.P = 0.40 * self.M 

    def process_results(self, df):
        results = df.copy()
        debug_logs = []

        # 1. Attendance Verification
        results['Final_Grade'] = np.where(results['attendance'] < 75, 'I', None)

        # 2. Check for ABSENT (AB) in ESE
        # Create a mask for rows where ese_marks is 'AB' (case insensitive)
        mask_absent = results['ese_marks'].astype(str).str.upper() == 'AB'
        
        if mask_absent.any():
            count_absent = mask_absent.sum()
            debug_logs.append(f"⚠️ {count_absent} students marked 'AB' (Absent) in ESE. Assigned Grade 'Z'.")
            results.loc[mask_absent & (results['Final_Grade'].isnull()), 'Final_Grade'] = 'Z'

        # Convert ESE to numeric for checks (treat AB/Errors as 0)
        results['ese_marks_numeric'] = pd.to_numeric(results['ese_marks'], errors='coerce').fillna(0)

        # 3. ESE Minimum Marks Check
        # Rule: Fail if ESE marks < 20% of ESE MAXIMUM
        min_ese_threshold = 0.20 * self.ESE_M
        
        # Identify students who failed ESE (and aren't I or Z)
        mask_ese_fail = (results['Final_Grade'].isnull()) & (results['ese_marks_numeric'] < min_ese_threshold)
        
        if mask_ese_fail.any():
            count_ese_fail = mask_ese_fail.sum()
            debug_logs.append(f"⚠️ {count_ese_fail} students failed ESE (Scored < {min_ese_threshold:.1f}). Grade 'F' assigned.")
            results.loc[mask_ese_fail, 'Final_Grade'] = 'F'

        # 4. Filter Students for Statistics based on PROTOCOL
        # ---------------------------------------------------------
        if self.protocol == 'Protocol A (Exclusive)':
            # EXCLUDE ESE Failures and Absentees from Mean/SD
            # Only use students who passed the hurdles
            stats_mask = (
                (results['attendance'] >= 75) & 
                (results['ese_marks_numeric'] >= min_ese_threshold)
            )
            debug_logs.append(f"ℹ️ Protocol A Active: Statistics computed using ONLY students who passed ESE (>{min_ese_threshold}).")
            
        else:
            # Protocol B (Inclusive)
            # INCLUDE ESE Failures (0 marks) in Mean/SD
            # Only exclude Attendance defaulters ('I')
            stats_mask = (results['attendance'] >= 75)
            debug_logs.append(f"ℹ️ Protocol B Active: Statistics INCLUDE students who failed ESE (Zero-Inflation).")
        # ---------------------------------------------------------

        regular_students = results.loc[stats_mask, 'marks'].values
        count = len(regular_students)
        
        # 5. Formula Type Selection
        if count >= 30:
            method = "Relative Grading (Statistical)"
            boundaries, logs = self._calculate_relative_boundaries(regular_students)
            debug_logs.extend(logs)
        else:
            method = "Absolute Grading (Count < 30)"
            boundaries = self._get_absolute_boundaries()
            debug_logs.append("Batch size < 30. Switched to Absolute Grading.")

        # 6. Grade Assignment
        # Apply boundaries only to students who don't already have a grade (I, F, Z)
        mask = results['Final_Grade'].isnull()
        results.loc[mask, 'Final_Grade'] = results.loc[mask, 'marks'].apply(
            lambda x: self._assign_grade(x, boundaries)
        )

        results = results.drop(columns=['ese_marks_numeric'])
        return results, boundaries, method, debug_logs

    def _calculate_relative_boundaries(self, marks):
        X = np.mean(marks) 
        sigma = np.std(marks)
        logs = []
        
        logs.append(f"Batch Statistics: Mean (X)={X:.2f}, SD (sigma)={sigma:.2f}")

        # Base Formula
        raw_D_limit = X - 1.5 * sigma
        
        bounds = {
            'A+': X + 1.5 * sigma,
            'A':  X + 1.0 * sigma,
            'B+': X + 0.5 * sigma,
            'B':  X,
            'C+': X - 0.5 * sigma,
            'C':  X - 1.0 * sigma,
            'D':  raw_D_limit
        }

        # --- CONDITION 1: MODERATION RULE ---
        if raw_D_limit > self.P:
            logs.append(f"⚠️ Moderation Triggered: Raw D ({raw_D_limit:.2f}) > Pass Mark ({self.P}). Capping D at {self.P}.")
            bounds['C+'] = X - (1 * (X - self.P) / 3)
            bounds['C']  = X - (2 * (X - self.P) / 3)
            bounds['D']  = float(self.P) 
            
        # --- CONDITION 2: MIN CUT-OFF PROTECTION ---
        elif raw_D_limit < (0.30 * self.M):
            logs.append(f"🛡️ Min Cut-off Protection Triggered: Raw D ({raw_D_limit:.2f}) < 30%. Shifting curve up.")
            delta = (0.30 * self.M) - raw_D_limit
            for g in bounds:
                bounds[g] += delta
            bounds['D'] = 0.30 * self.M

        # --- CONDITION 3: MAX MARKS PROTECTION ---
        if bounds['A+'] > self.M:
             bounds['A+'] = self.M
             logs.append(f"Upper Bound Protection: A+ capped at {self.M}")
             
        return bounds, logs

    def _get_absolute_boundaries(self):
        if self.type == 'Theory':
            return {'A+': 90, 'A': 80, 'B+': 72, 'B': 64, 'C+': 56, 'C': 48, 'D': 40}
        else: 
            return {'A+': 90, 'A': 80, 'B+': 70, 'B': 62, 'C+': 58, 'C': 54, 'D': 50}

    def _assign_grade(self, marks, bounds):
        if marks >= bounds['A+']: return 'A+'
        if marks >= bounds['A']:  return 'A'
        if marks >= bounds['B+']: return 'B+'
        if marks >= bounds['B']:  return 'B'
        if marks >= bounds['C+']: return 'C+'
        if marks >= bounds['C']:  return 'C'
        if marks >= bounds['D']:  return 'D'
        return 'F'

# ==========================================
# 2. STREAMLIT WEB INTERFACE
# ==========================================
def main():
    st.set_page_config(page_title="Grading Automation Tool", layout="wide")
    
    st.title("🎓 Relative Grading Tool - developed by D Mandal")
    st.markdown("**Compliance:** *Tabulation Manual 2026*")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ Configuration")
        course_type = st.radio("Course Type", ["Theory", "Practical"])
        
        # PROTOCOL SELECTION
        st.subheader("📊 Statistical Protocol")
        protocol_choice = st.radio(
            "Select Grading Logic:",
            ["Protocol A (Exclusive)", "Protocol B (Inclusive)"],
            help="Protocol A: Excludes ESE failures from Mean/SD (Prevents inflation).\nProtocol B: Includes failures (Lowers Mean)."
        )
        
        # 1. Total Marks
        max_marks = st.number_input("Total Course Marks (Internal + ESE)", value=100)
        
        # 2. ESE Marks
        default_ese = int(0.60 * max_marks)
        ese_max_marks = st.number_input("ESE Maximum Marks (for 20% Rule)", value=default_ese)
        
        # Display Logic
        min_ese_pass = 0.20 * ese_max_marks
        pass_percent = 50 if course_type == 'Practical' else 40
        pass_marks = (pass_percent / 100) * max_marks
        
        st.info(f"**Rules Summary:**\n"
                f"• **Protocol:** {protocol_choice}\n"
                f"• **Course Pass:** {pass_marks:.0f} marks\n"
                f"• **ESE Fail Threshold:** < {min_ese_pass:.1f} marks\n"
                f"• **Min Cut-off Floor:** {0.30 * max_marks:.0f} marks")
        
        st.markdown("---")
        st.markdown("### Upload Data")
        uploaded_file = st.file_uploader("Upload Student CSV", type=["csv"])
        
        sample_data = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'marks': [82, 65, 45, 32, 91],
            'attendance': [90, 85, 80, 76, 95],
            'ese_marks': [40, 30, 'AB', 10, 50] 
        })
        csv = sample_data.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV Template", csv, "template.csv", "text/csv")

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = df.columns.str.strip().str.lower()
            
            required_cols = {'id', 'marks', 'attendance', 'ese_marks'}
            if not required_cols.issubset(df.columns):
                st.error(f"Error: CSV must contain columns: {list(required_cols)}")
            else:
                engine = StrictUniversityGrading(
                    total_max_marks=max_marks, 
                    ese_max_marks=ese_max_marks, 
                    course_type=course_type,
                    protocol=protocol_choice  # Pass user choice
                )
                processed_df, boundaries, method, logs = engine.process_results(df)

                # 1. METRICS
                col1, col2, col3, col4 = st.columns(4)
                valid_students = df[df['attendance']>=75]
                avg_score = valid_students['marks'].mean()
                pass_count = len(processed_df[~processed_df['Final_Grade'].isin(['F', 'I', 'Z'])])
                
                col1.metric("Total Students", len(df))
                col2.metric("Raw Average", f"{avg_score:.2f}")
                col3.metric("Method Used", "Relative" if "Relative" in method else "Absolute")
                col4.metric("Pass Percentage", f"{(pass_count / len(df) * 100):.1f}%")

                # 2. LOGS
                if logs:
                    with st.expander("📝 View Calculation Logs & Triggers", expanded=True):
                        for log in logs:
                            if "Triggered" in log: st.warning(log)
                            elif "Protocol" in log: st.info(log)
                            elif "failed ESE" in log: st.error(log)
                            elif "Absent" in log: st.error(log)
                            else: st.write(log)

                # 3. VISUALIZATION
                c1, c2 = st.columns([1, 2])
                
                with c1:
                    st.subheader("📊 Grade Distribution")
                    
                    grade_order = ['Z', 'F', 'D', 'C', 'C+', 'B', 'B+', 'A', 'A+', 'O']
                    grade_counts = processed_df['Final_Grade'].value_counts().reset_index()
                    grade_counts.columns = ['Grade', 'Count']
                    
                    chart = alt.Chart(grade_counts).mark_area(
                        interpolate='monotone', 
                        fillOpacity=0.6,
                        color='teal'
                    ).encode(
                        x=alt.X('Grade', sort=grade_order),
                        y='Count',
                        tooltip=['Grade', 'Count']
                    ).properties(height=300)
                    
                    # Updated to use width='stretch' instead of use_container_width=True
                    st.altair_chart(chart, theme="streamlit", width='stretch')
                    
                    st.subheader("Boundary Cut-offs")
                    bounds_df = pd.DataFrame(list(boundaries.items()), columns=['Grade', 'Min Marks'])
                    st.table(bounds_df)

                with c2:
                    st.subheader("📋 Student Results")
                    def highlight_fail(row):
                        if row['Final_Grade'] in ['F', 'I', 'Z']:
                            return ['background-color: #ffcccc'] * len(row)
                        return [''] * len(row)

                    st.dataframe(processed_df.style.apply(highlight_fail, axis=1), use_container_width=True)
                    
                    res_csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Download Final Result CSV", res_csv, 'final_grades.csv', 'text/csv')

        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.info("👋 Please upload a CSV file to begin.")

if __name__ == "__main__":
    main()
