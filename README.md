# 🎓 Relative Grading Automation Tool

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-red)
![Status](https://img.shields.io/badge/Status-Active-success)

A robust, web-based application designed to automate the calculation of Relative Grades for autonomous engineering institutions. This tool allows Examination Sections to switch between statistical protocols to analyze grade distribution and prevent grade inflation.

**Developed by:** Daipayan Mandal  
**Compliance:** Tabulation Manual 2026

## 🚀 Key Features

* **Dual Statistical Protocols:**
    * **Protocol A (Strict):** Excludes outliers (ESE failures) from the Mean/SD calculation to maintain high academic standards.
    * **Protocol B (Inclusive):** Includes all students in the statistical baseline (useful for comparison).
* **Automated Edge Case Handling:**
    * Automatically detects **Absent (AB)** students and assigns **Grade Z**.
    * Automatically detects **Failures** (<20% marks in End Sem Exam) and assigns **Grade F**.
* **Interactive Visualizations:** Generates real-time Bell Curves (Normal Distribution) to visualize class performance.
* **Safety Nets:** Includes built-in moderation logic (Min Cut-off Protection & Max Marks Protection).
* **CSV Support:** Easy upload of student data and download of processed results.

## 🛠️ Installation & Setup

### Prerequisites
* Python 3.8 or higher
* Git

### Step 1: Clone the Repository
```bash
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name
