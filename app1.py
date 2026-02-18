import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ==========================================
# 1. GRADE POINT MAPPING
# ==========================================
GRADE_POINTS = {
    'A+': 10, 'A': 9, 'B+': 8, 'B': 7, 'C+': 6, 'C': 5, 'D': 4, 'D*': 4, 
    'F': 0, 'I': 0, 'Z': 0
}

# ==========================================
# 2. CORE GRADING LOGIC (Per Subject)
# ==========================================
class StrictUniversityGrading:
    def __init__(self, total_max_marks, ese_max_marks, course_type, protocol):
        self.M = total_max_marks       
        self.ESE_M = ese_max_marks     
        self.type = course_type
        self.protocol = protocol  
        self.ese_threshold = 0.20 * ese_max_marks
        
        if self.type == 'Practical':
            self.P = 0.50 * self.M 
        else:
            self.P = 0.40 * self.M 

    def process_results(self, df):
        results = df.copy()
        
        # 1. Attendance & Absentee Check
        results['Final_Grade'] = np.where(results['attendance'] < 75, 'I', None)
        mask_absent = results['ese_marks'].astype(str).str.upper() == 'AB'
        results.loc[mask_absent & (results['Final_Grade'].isnull()), 'Final_Grade'] = 'Z'

        # 2. Numeric Conversion
        results['ese_marks_numeric'] = pd.to_numeric(results['ese_marks'], errors='coerce').fillna(0)

        # 3. ESE Hurdle Check
        mask_ese_fail = (results['Final_Grade'].isnull()) & (results['ese_marks_numeric'] < self.ese_threshold)
        results.loc[mask_ese_fail, 'Final_Grade'] = 'F'

        # 4. Statistics Calculation
        if self.protocol == 'Protocol A (Strict)':
            stats_mask = (results['attendance'] >= 75) & (results['ese_marks_numeric'] >= self.ese_threshold)
        else:
            stats_mask = (results['attendance'] >= 75)

        regular_students = results.loc[stats_mask, 'marks'].values
        count = len(regular_students)
        
        if count >= 30:
            boundaries = self._calculate_relative_boundaries(regular_students)
        else:
            boundaries = self._get_absolute_boundaries()

        # 5. Preliminary Grade Assignment
        mask = results['Final_Grade'].isnull()
        results.loc[mask, 'Final_Grade'] = results.loc[mask, 'marks'].apply(
            lambda x: self._assign_grade(x, boundaries)
        )

        # Store boundary D for grace calculation later
        results['boundary_D'] = boundaries['D']
        results['min_ese_required'] = self.ese_threshold
        
        return results

    def _calculate_relative_boundaries(self, marks):
        X = np.mean(marks) 
        sigma = np.std(marks)
        raw_D_limit = X - 1.5 * sigma
        
        bounds = {'A+': X + 1.5 * sigma, 'A': X + 1.0 * sigma, 'B+': X + 0.5 * sigma, 
                  'B': X, 'C+': X - 0.5 * sigma, 'C': X - 1.0 * sigma, 'D': raw_D_limit}

        if raw_D_limit > self.P:
            bounds['D'] = float(self.P) 
        elif raw_D_limit < (0.30 * self.M):
            bounds['D'] = 0.30 * self.M
             
        return bounds

    def _get_absolute_boundaries(self):
        if self.type == 'Theory':
            return {'A+': 90, 'A': 80, 'B+': 72, 'B': 64, 'C+': 56, 'C': 48, 'D': 40}
        else: 
            return {'A+': 90, 'A': 80, 'B+': 70, 'B': 62, 'C+': 58, 'C': 54, 'D': 50}

    def _assign_grade(self, marks, bounds):
        for grade in ['A+', 'A', 'B+', 'B', 'C+', 'C', 'D']:
            if marks >= bounds[grade]: return grade
        return 'F'

# ==========================================
# 3. GRACE CRITERIA ENGINE
# ==========================================
def apply_grace_criteria(df):
    """
    Applies grace marks across all subjects for each student.
    Criteria: 
    1. ESE cleared in ALL subjects (>20%).
    2. Needs <= 3 marks to reach 'D' boundary.
    3. Max 2 subjects allowed.
    """
    processed_students = []
    
    for student_id, group in df.groupby('student_id'):
        # Check if student cleared ESE in ALL subjects
        # Numeric ESE was dropped in process_results, so we re-convert
        group['ese_val'] = pd.to_numeric(group['ese_marks'], errors='coerce').fillna(0)
        cleared_all_ese = (group['ese_val'] >= group['min_ese_required']).all()
        
        if cleared_all_ese:
            # Identify candidates for grace: Currently Grade 'F' AND (Boundary D - Marks) <= 3
            grace_mask = (group['Final_Grade'] == 'F') & \
                         ((group['boundary_D'] - group['marks']) <= 3) & \
                         ((group['boundary_D'] - group['marks']) > 0)
            
            grace_count = grace_mask.sum()
            
            # Condition: Maximum 2 subjects allowed for grace
            if 0 < grace_count <= 2:
                group.loc[grace_mask, 'Final_Grade'] = 'D*'
                group.loc[grace_mask, 'is_graced'] = True
        
        processed_students.append(group)
    
    final_df = pd.concat(processed_students)
    # Assign Grade Points after grace is applied
    final_df['Grade_Point'] = final_df['Final_Grade'].map(GRADE_POINTS)
    return final_df

# ==========================================
# 4. AGGREGATION & SGPA
# ==========================================
def calculate_sgpa(student_df):
    total_credits = student_df['credits'].sum()
    passed_mask = ~student_df['Final_Grade'].isin(['F', 'I', 'Z'])
    earned_credits = student_df.loc[passed_mask, 'credits'].sum()
    
    total_points = (student_df['credits'] * student_df['Grade_Point']).sum()
    sgpa = total_points / total_credits if total_credits > 0 else 0
    
    failed_subs = student_df.loc[~passed_mask, 'subject_code'].tolist()
    failed_str = ", ".join(failed_subs) if failed_subs else "None"
    
    return pd.Series({
        'Earned_Credits': earned_credits,
        'SGPA': round(sgpa, 2),
        'Failed_Subjects': failed_str,
        'Graced_Count': student_df.get('is_graced', pd.Series([False]*len(student_df))).sum()
    })

# ==========================================
# 5. STREAMLIT INTERFACE
# ==========================================
def main():
    st.set_page_config(page_title="Semester Grading Engine", layout="wide")
    st.title("🎓 Multi-Subject Grading Engine with Grace Provision")
    st.markdown("**Developer:** Daipayan Mandal | **Compliance:** Tabulation Manual 2026")
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        protocol_choice = st.radio("Grading Logic:", ["Protocol A (Strict)", "Protocol B (Inclusive)"])
        uploaded_file = st.file_uploader("Upload Semester CSV", type=["csv"])

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        # Clean columns
        df.columns = df.columns.str.strip().str.lower()
        
        # 1. Subject-wise Preliminary Grading
        all_results = []
        for code, sub_df in df.groupby('subject_code'):
            engine = StrictUniversityGrading(sub_df['total_max'].iloc[0], 
                                            sub_df['ese_max'].iloc[0], 
                                            sub_df['course_type'].iloc[0], 
                                            protocol_choice)
            all_results.append(engine.process_results(sub_df))
        
        combined_df = pd.concat(all_results)
        
        # 2. Apply Grace Criteria (Semester Level)
        final_df = apply_grace_criteria(combined_df)
        
        # 3. Calculate SGPA
        summary_df = final_df.groupby('student_id').apply(calculate_sgpa).reset_index()
        
        # 4. Display Tabs
        t1, t2 = st.tabs(["📊 Master Result Sheet", "📝 Detailed Subject Analysis"])
        
        with t1:
            # Pivot for the Committee View
            pivot_grades = final_df.pivot(index='student_id', columns='subject_code', values='Final_Grade').reset_index()
            master_sheet = pd.merge(pivot_grades, summary_df, on='student_id')
            
            st.subheader("Final Master Sheet (with SGPA & Grace)")
            
            # Styling: Red for Fail, Blue for Grace
            def style_results(val):
                if val == 'D*': return 'color: blue; font-weight: bold'
                if val in ['F', 'I', 'Z']: return 'color: red'
                return ''
            
            st.dataframe(master_sheet.style.applymap(style_results), use_container_width=True)
            st.download_button("📥 Download Master Sheet", master_sheet.to_csv(index=False), "Master_Sheet.csv")

        with t2:
            st.subheader("Raw Data with Grade Points & Boundaries")
            st.write(final_df)

if __name__ == "__main__":
    main()
