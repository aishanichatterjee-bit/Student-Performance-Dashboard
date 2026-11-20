# Student Performance and Study-Hours Dashboard

A Python desktop dashboard for exploring anonymised student study hours and assessment scores.

## Features
- Tkinter desktop interface
- CSV import and export
- Input validation using a `StudentRecord` class
- Letter-grade conversion (A, B, C, D, F)
- NumPy statistics and trend line
- Pandas course summaries and correlations
- Matplotlib scatter plot, histogram and course comparison
- IQR outlier detection
- Pearson and Spearman correlation comparison
- Written interpretation with a correlation-is-not-causation warning

## Requirements
Python 3.9 or later is recommended. Tkinter is normally included with Python.

Install third-party libraries in Windows Command Prompt:
```bash
py -m pip install -r requirements.txt
```

## Run in Python IDLE
1. Extract this project folder.
2. Open `student_dashboard_idle.py` in IDLE.
3. Select **Run > Run Module** or press **F5**.

## CSV format
The required column names are:
`student_id, course, study_hours, score`

Example:
```csv
student_id,course,study_hours,score
S001,Mathematics,12,78
S002,Physics,8,62
S003,Electronics,15,85
```

## Dataset note
The built-in sample data and supplied CSV are synthetic demonstration data. They are not actual student records. Correlation does not establish causation.

## Project report
Refer to the submitted project report for the methodology, implementation details, results, testing, and conclusion. The dataset contains synthetic demonstration data and does not represent actual student records.
