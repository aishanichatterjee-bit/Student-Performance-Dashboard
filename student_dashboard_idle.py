"""
Student Performance and Study-Hours Dashboard
B.Tech Python End-Semester Project

Run in IDLE:
1. Open this file: student_dashboard_idle.py
2. Select Run > Run Module (or press F5).

Install required packages in Command Prompt:
py -m pip install numpy pandas matplotlib
"""

import csv
import random
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# --------------------------- DATA MODEL ---------------------------

def is_valid_score(score):
    """Return True when score is numeric and between 0 and 100."""
    try:
        value = float(score)
        return 0 <= value <= 100
    except (TypeError, ValueError):
        return False


def score_to_grade(score):
    """Convert a score into a letter grade."""
    value = float(score)
    if not is_valid_score(value):
        raise ValueError("Score must be between 0 and 100.")
    if value >= 70:
        return "A"
    if value >= 60:
        return "B"
    if value >= 50:
        return "C"
    if value >= 40:
        return "D"
    return "F"


class StudentRecord:
    """Represents one student's anonymised performance record."""

    def __init__(self, student_id, course, study_hours, score):
        self.student_id = str(student_id).strip()
        self.course = str(course).strip()
        self.study_hours = float(study_hours)
        self.score = float(score)

        if not self.student_id:
            raise ValueError("Student ID cannot be blank.")
        if not self.course:
            raise ValueError("Course cannot be blank.")
        if not 0 <= self.study_hours <= 168:
            raise ValueError("Study hours must be between 0 and 168.")
        if not is_valid_score(self.score):
            raise ValueError("Score must be between 0 and 100.")

    @classmethod
    def from_dict(cls, row):
        return cls(
            row["student_id"], row["course"],
            row["study_hours"], row["score"]
        )

    def to_dict(self):
        return {
            "student_id": self.student_id,
            "course": self.course,
            "study_hours": self.study_hours,
            "score": self.score,
            "grade": score_to_grade(self.score)
        }


# --------------------------- DATA HANDLING ---------------------------

CSV_FIELDS = ["student_id", "course", "study_hours", "score"]
COURSES = ["Mathematics", "Physics", "Electronics", "Programming"]


def generate_sample_data():
    """Create a repeatable synthetic dataset with two invalid rows."""
    rng = random.Random(42)
    rows = []

    for number in range(1, 124):
        hours = round(rng.uniform(2, 25), 1)
        # A gentle relationship plus random variation; values are synthetic.
        score = round(max(0, min(100, 42 + hours * 1.35 + rng.gauss(0, 13))), 1)
        rows.append({
            "student_id": f"S{number:03d}",
            "course": rng.choice(COURSES),
            "study_hours": hours,
            "score": score
        })

    # Deliberately unusual but valid observations for outlier demonstration.
    rows[64] = {"student_id": "S065", "course": "Programming",
                "study_hours": 40.0, "score": 99.0}
    rows[87] = {"student_id": "S088", "course": "Physics",
                "study_hours": 0.5, "score": 18.0}

    # Two deliberately invalid rows to demonstrate validation.
    rows.extend([
        {"student_id": "S901", "course": "Mathematics",
         "study_hours": 12, "score": 140},
        {"student_id": "S902", "course": "Physics",
         "study_hours": "", "score": 65}
    ])
    return rows


def validate_rows(rows):
    """Convert valid dictionaries into StudentRecord objects."""
    valid_records = []
    rejected = []

    for line_number, row in enumerate(rows, start=2):
        try:
            record = StudentRecord.from_dict(row)
            valid_records.append(record.to_dict())
        except (KeyError, TypeError, ValueError) as error:
            rejected.append((line_number, str(error)))

    return valid_records, rejected


def load_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        missing = [field for field in CSV_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("CSV is missing required columns: " + ", ".join(missing))
        return validate_rows(list(reader))


def save_csv(dataframe, path):
    dataframe[CSV_FIELDS].to_csv(path, index=False)


# --------------------------- ANALYSIS ---------------------------

def iqr_mask(dataframe, column, threshold=1.5):
    """Return a Boolean Series identifying outliers in one column."""
    q1 = dataframe[column].quantile(0.25)
    q3 = dataframe[column].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - threshold * iqr
    upper = q3 + threshold * iqr
    return (dataframe[column] < lower) | (dataframe[column] > upper)


def correlation(x, y, method="pearson"):
    """Calculate a correlation value, returning NaN if undefined."""
    if len(x) < 2 or x.nunique() < 2 or y.nunique() < 2:
        return float("nan")
    return x.corr(y, method=method)


def analysis_for(dataframe, threshold=1.5):
    """Add grade/outlier columns and calculate summary information."""
    result = dataframe.copy()
    result["grade"] = result["score"].apply(score_to_grade)
    result["hours_outlier"] = iqr_mask(result, "study_hours", threshold)
    result["score_outlier"] = iqr_mask(result, "score", threshold)
    result["outlier"] = result["hours_outlier"] | result["score_outlier"]

    clean = result.loc[~result["outlier"]]
    summary = {
        "count": len(result),
        "mean_score": result["score"].mean(),
        "median_score": result["score"].median(),
        "mean_hours": result["study_hours"].mean(),
        "outliers": int(result["outlier"].sum()),
        "pearson_all": correlation(result["study_hours"], result["score"], "pearson"),
        "spearman_all": correlation(result["study_hours"], result["score"], "spearman"),
        "pearson_clean": correlation(clean["study_hours"], clean["score"], "pearson"),
        "spearman_clean": correlation(clean["study_hours"], clean["score"], "spearman")
    }
    course_summary = result.groupby("course").agg(
        students=("student_id", "count"),
        mean_score=("score", "mean"),
        mean_hours=("study_hours", "mean")
    ).reset_index()
    return result, summary, course_summary


# --------------------------- DASHBOARD GUI ---------------------------

class Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Performance and Study-Hours Dashboard")
        self.root.geometry("1180x780")
        self.root.minsize(900, 620)

        self.rejected_count = 0
        self.data = pd.DataFrame()
        self.analysis = pd.DataFrame()
        self.summary = {}
        self.course_summary = pd.DataFrame()

        self.course_filter = tk.StringVar(value="All courses")
        self.threshold = tk.DoubleVar(value=1.5)
        self.hide_outliers = tk.BooleanVar(value=False)

        self._build()
        self.use_sample_data()

    def _build(self):
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Label(
            header, text="STUDENT PERFORMANCE DASHBOARD",
            font=("Arial", 18, "bold")
        ).pack(anchor="w")
        ttk.Label(
            header, text="Explore study hours, assessment scores and course performance",
            font=("Arial", 10)
        ).pack(anchor="w", pady=(3, 8))

        controls = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        controls.pack(fill="x")
        ttk.Button(controls, text="Use sample data", command=self.use_sample_data).pack(side="left", padx=3)
        ttk.Button(controls, text="Open CSV", command=self.open_csv).pack(side="left", padx=3)
        ttk.Button(controls, text="Export CSV", command=self.export_csv).pack(side="left", padx=3)

        ttk.Label(controls, text="Course:").pack(side="left", padx=(18, 4))
        self.course_box = ttk.Combobox(
            controls, textvariable=self.course_filter, state="readonly",
            width=17, values=["All courses"]
        )
        self.course_box.pack(side="left")
        self.course_box.bind("<<ComboboxSelected>>", lambda event: self.refresh())

        ttk.Label(controls, text="IQR k:").pack(side="left", padx=(12, 4))
        threshold_box = ttk.Spinbox(
            controls, from_=0.5, to=3.0, increment=0.25,
            textvariable=self.threshold, width=5, command=self.refresh
        )
        threshold_box.pack(side="left")
        ttk.Checkbutton(
            controls, text="Hide outliers in charts",
            variable=self.hide_outliers, command=self.refresh
        ).pack(side="left", padx=10)

        self.metrics_frame = ttk.Frame(self.root, padding=(10, 0, 10, 8))
        self.metrics_frame.pack(fill="x")
        self.metric_labels = {}
        metric_names = [
            ("Students", "count"), ("Mean score", "mean_score"),
            ("Median score", "median_score"), ("Mean hours/week", "mean_hours"),
            ("Outliers", "outliers")
        ]
        for title, key in metric_names:
            card = ttk.LabelFrame(self.metrics_frame, text=title, padding=8)
            card.pack(side="left", fill="both", expand=True, padx=3)
            label = ttk.Label(card, text="—", font=("Arial", 15, "bold"))
            label.pack()
            self.metric_labels[key] = label

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self.scatter_tab = ttk.Frame(self.notebook)
        self.scores_tab = ttk.Frame(self.notebook)
        self.courses_tab = ttk.Frame(self.notebook)
        self.records_tab = ttk.Frame(self.notebook)
        self.analysis_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.scatter_tab, text="Study hours vs scores")
        self.notebook.add(self.scores_tab, text="Scores & grades")
        self.notebook.add(self.courses_tab, text="Course comparison")
        self.notebook.add(self.records_tab, text="Outliers & records")
        self.notebook.add(self.analysis_tab, text="Written analysis")

        self.scatter_canvas = self._make_plot(self.scatter_tab)
        self.scores_canvas = self._make_plot(self.scores_tab)
        self.courses_canvas = self._make_plot(self.courses_tab)

        self.records_tree = ttk.Treeview(
            self.records_tab,
            columns=("id", "course", "hours", "score", "grade", "outlier"),
            show="headings", height=18
        )
        headings = [
            ("id", "Student ID", 100), ("course", "Course", 150),
            ("hours", "Study hours/week", 130), ("score", "Score", 90),
            ("grade", "Grade", 80), ("outlier", "Outlier?", 90)
        ]
        for column, title, width in headings:
            self.records_tree.heading(column, text=title)
            self.records_tree.column(column, width=width, anchor="center")
        self.records_tree.pack(fill="both", expand=True, padx=8, pady=8)

        self.analysis_text = tk.Text(self.analysis_tab, wrap="word", font=("Arial", 11), padx=12, pady=12)
        self.analysis_text.pack(fill="both", expand=True, padx=8, pady=8)

        self.status = ttk.Label(self.root, text="Ready", anchor="w", padding=5)
        self.status.pack(fill="x", side="bottom")

    def _make_plot(self, parent):
        figure = Figure(figsize=(7, 4.3), dpi=100)
        axis = figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(figure, master=parent)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        return canvas

    def use_sample_data(self):
        rows = generate_sample_data()
        valid, rejected = validate_rows(rows)
        self.rejected_count = len(rejected)
        self.data = pd.DataFrame(valid)
        self.course_filter.set("All courses")
        self._update_course_choices()
        self.refresh()
        self.status.config(
            text=f"Loaded synthetic sample: {len(rows)} input rows, "
                 f"{len(valid)} accepted, {len(rejected)} rejected."
        )

    def _update_course_choices(self):
        courses = sorted(self.data["course"].unique().tolist()) if not self.data.empty else []
        self.course_box["values"] = ["All courses"] + courses
        if self.course_filter.get() not in self.course_box["values"]:
            self.course_filter.set("All courses")

    def _filtered_data(self):
        if self.course_filter.get() == "All courses":
            return self.data.copy()
        return self.data[self.data["course"] == self.course_filter.get()].copy()

    def refresh(self):
        if self.data.empty:
            return
        try:
            threshold = float(self.threshold.get())
            if threshold <= 0:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showerror("Invalid IQR threshold", "Enter a positive number for IQR k.")
            self.threshold.set(1.5)
            threshold = 1.5

        selected = self._filtered_data()
        self.analysis, self.summary, self.course_summary = analysis_for(selected, threshold)

        self.metric_labels["count"].config(text=str(self.summary["count"]))
        self.metric_labels["mean_score"].config(text=f'{self.summary["mean_score"]:.2f}')
        self.metric_labels["median_score"].config(text=f'{self.summary["median_score"]:.2f}')
        self.metric_labels["mean_hours"].config(text=f'{self.summary["mean_hours"]:.2f}')
        self.metric_labels["outliers"].config(text=str(self.summary["outliers"]))

        self._draw_scatter()
        self._draw_scores()
        self._draw_courses()
        self._fill_records()
        self._write_interpretation()

    def _chart_data(self):
        if self.hide_outliers.get():
            return self.analysis.loc[~self.analysis["outlier"]]
        return self.analysis

    def _draw_scatter(self):
        figure = self.scatter_canvas.figure
        axis = figure.axes[0]
        axis.clear()
        shown = self._chart_data()
        flagged = self.analysis[self.analysis["outlier"]]
        axis.scatter(shown["study_hours"], shown["score"], alpha=0.7, label="Records")
        if not self.hide_outliers.get() and not flagged.empty:
            axis.scatter(flagged["study_hours"], flagged["score"],
                         marker="x", s=70, label="Flagged outliers")
        if len(shown) >= 2 and shown["study_hours"].nunique() > 1:
            slope, intercept = np.polyfit(shown["study_hours"], shown["score"], 1)
            x_values = np.linspace(shown["study_hours"].min(), shown["study_hours"].max(), 100)
            axis.plot(x_values, slope * x_values + intercept, label="Linear fit")
        axis.set_title("Study hours versus assessment score")
        axis.set_xlabel("Reported study hours per week")
        axis.set_ylabel("Assessment score (0–100)")
        axis.legend()
        axis.grid(alpha=0.25)
        figure.tight_layout()
        self.scatter_canvas.draw()

    def _draw_scores(self):
        figure = self.scores_canvas.figure
        axis = figure.axes[0]
        axis.clear()
        shown = self._chart_data()
        axis.hist(shown["score"], bins=10, edgecolor="black", alpha=0.75)
        axis.set_title("Distribution of student scores")
        axis.set_xlabel("Assessment score")
        axis.set_ylabel("Number of students")
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        self.scores_canvas.draw()

    def _draw_courses(self):
        figure = self.courses_canvas.figure
        axis = figure.axes[0]
        axis.clear()
        course_data = self.course_summary
        if not course_data.empty:
            axis.bar(course_data["course"], course_data["mean_score"])
        axis.set_title("Average score by course")
        axis.set_xlabel("Course")
        axis.set_ylabel("Mean assessment score")
        axis.tick_params(axis="x", rotation=15)
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        self.courses_canvas.draw()

    def _fill_records(self):
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)
        for _, row in self.analysis.iterrows():
            self.records_tree.insert(
                "", "end",
                values=(
                    row["student_id"], row["course"],
                    f'{row["study_hours"]:.1f}', f'{row["score"]:.1f}',
                    row["grade"], "Yes" if row["outlier"] else "No"
                )
            )

    def _write_interpretation(self):
        s = self.summary
        text = (
            "WRITTEN STATISTICAL ANALYSIS\n\n"
            f"Number of valid records: {s['count']}\n"
            f"Mean score: {s['mean_score']:.2f} / 100\n"
            f"Median score: {s['median_score']:.2f} / 100\n"
            f"Mean reported study time: {s['mean_hours']:.2f} hours per week\n"
            f"Outliers flagged using IQR k={self.threshold.get()}: {s['outliers']}\n\n"
            "CORRELATION COMPARISON\n"
            f"Pearson correlation (all selected records): {s['pearson_all']:.3f}\n"
            f"Spearman correlation (all selected records): {s['spearman_all']:.3f}\n"
            f"Pearson correlation (excluding flagged records): {s['pearson_clean']:.3f}\n"
            f"Spearman correlation (excluding flagged records): {s['spearman_clean']:.3f}\n\n"
            "INTERPRETATION\n"
        )
        if pd.notna(s["pearson_all"]):
            if s["pearson_all"] > 0:
                text += "The selected records show a positive linear association between reported study hours and scores. "
            elif s["pearson_all"] < 0:
                text += "The selected records show a negative linear association between reported study hours and scores. "
            else:
                text += "The selected records show little linear association between reported study hours and scores. "
        else:
            text += "There are not enough distinct observations to calculate a meaningful correlation. "
        text += (
            "Compare the correlation values before and after excluding IQR-flagged observations to see "
            "whether unusual values affect the result.\n\n"
            "IMPORTANT LIMITATION\n"
            "Correlation does not prove causation. The sample dataset is synthetically generated for "
            "demonstration and does not provide evidence about real students. Other factors such as prior "
            "knowledge, attendance, teaching methods and motivation may influence assessment scores."
        )
        self.analysis_text.config(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("1.0", text)
        self.analysis_text.config(state="disabled")

    def open_csv(self):
        path = filedialog.askopenfilename(
            title="Select student CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            valid, rejected = load_csv(path)
            if not valid:
                raise ValueError("The selected CSV contains no valid student records.")
            self.data = pd.DataFrame(valid)
            self.rejected_count = len(rejected)
            self.course_filter.set("All courses")
            self._update_course_choices()
            self.refresh()
            self.status.config(
                text=f"Imported {len(valid)} valid records; rejected {len(rejected)} rows."
            )
            if rejected:
                messagebox.showwarning(
                    "Some rows were rejected",
                    f"{len(rejected)} row(s) contained invalid data and were skipped."
                )
        except Exception as error:
            messagebox.showerror("CSV import error", str(error))

    def export_csv(self):
        if self.analysis.empty:
            messagebox.showinfo("No data", "There are no records to export.")
            return
        path = filedialog.asksaveasfilename(
            title="Export student records",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            save_csv(self.analysis, path)
            messagebox.showinfo("Export complete", "The selected records were exported successfully.")
        except Exception as error:
            messagebox.showerror("Export error", str(error))


def main():
    root = tk.Tk()
    Dashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
