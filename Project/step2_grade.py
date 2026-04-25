"""
STEP 2 — Grade student answers by comparing with model answers
Usage:
    python step2_grade.py --student student_answers.txt --model model_answers.txt
Output:
    result_report.txt  — human-readable report
    result_report.csv  — spreadsheet-friendly
"""

import argparse
import re
import os
import sys

try:
    from rapidfuzz import fuzz
except ImportError:
    print("ERROR: rapidfuzz not installed. Run: pip install rapidfuzz")
    sys.exit(1)


# ── Thresholds ────────────────────────────────────────────────
CORRECT_THRESHOLD = 80   # fuzzy score >= this → correct
PARTIAL_THRESHOLD = 50   # fuzzy score >= this → partial credit
# ─────────────────────────────────────────────────────────────


def load_answers(filepath):
    """
    Load answers from a text file.
    Accepts formats:
        1. testing
        1) testing
        1: testing
        1 testing
    Returns dict {int: str}
    """
    answers = {}
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^(\d+)\s*[.):\-]?\s*(.+)$', line)
            if m:
                answers[int(m.group(1))] = m.group(2).strip()
    return answers


def normalize(text):
    """Lowercase, strip punctuation, collapse spaces."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def compute_score(student_ans, model_ans):
    """
    Return (fuzzy_score, verdict) for one answer pair.
    Uses multiple fuzzy strategies and takes the best.
    """
    s = normalize(student_ans)
    m = normalize(model_ans)

    if not s or s in ('?', '-', ''):
        return 0, "blank"

    # Try multiple fuzzy methods
    scores = [
        fuzz.ratio(s, m),
        fuzz.partial_ratio(s, m),
        fuzz.token_sort_ratio(s, m),
        fuzz.token_set_ratio(s, m),
    ]
    best = max(scores)

    if best >= CORRECT_THRESHOLD:
        return best, "correct"
    elif best >= PARTIAL_THRESHOLD:
        return best, "partial"
    else:
        return best, "wrong"


def grade(student_answers, model_answers):
    """Grade all answers. Returns list of result dicts."""
    all_nums = sorted(set(model_answers.keys()) | set(student_answers.keys()))
    results = []

    for num in all_nums:
        model_ans = model_answers.get(num, "")
        student_ans = student_answers.get(num, "(missing)")

        if not model_ans:
            continue  # skip if no model answer exists

        score, verdict = compute_score(student_ans, model_ans)

        results.append({
            "num": num,
            "student": student_ans,
            "model": model_ans,
            "fuzzy_score": round(score, 1),
            "verdict": verdict,
        })

    return results


def compute_summary(results):
    total = len(results)
    correct = sum(1 for r in results if r["verdict"] == "correct")
    partial = sum(1 for r in results if r["verdict"] == "partial")
    wrong   = sum(1 for r in results if r["verdict"] in ("wrong", "blank"))

    # Score: correct = 1pt, partial = 0.5pt
    score_pts = correct + (partial * 0.5)
    percent = round((score_pts / total) * 100, 1) if total else 0

    grade_letter = (
        "A+" if percent >= 95 else
        "A"  if percent >= 85 else
        "B"  if percent >= 75 else
        "C"  if percent >= 60 else
        "D"  if percent >= 45 else
        "F"
    )

    return {
        "total": total,
        "correct": correct,
        "partial": partial,
        "wrong": wrong,
        "score_pts": score_pts,
        "percent": percent,
        "grade": grade_letter,
    }


def save_txt_report(results, summary, output_path="result_report.txt"):
    VERDICT_ICON = {"correct": "[✓]", "partial": "[~]", "wrong": "[✗]", "blank": "[ ]"}

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  AI ANSWER SHEET EVALUATION REPORT\n")
        f.write("=" * 60 + "\n\n")

        f.write(f"  Score    : {summary['percent']}%   ({summary['score_pts']}/{summary['total']} pts)\n")
        f.write(f"  Grade    : {summary['grade']}\n")
        f.write(f"  Correct  : {summary['correct']}\n")
        f.write(f"  Partial  : {summary['partial']}\n")
        f.write(f"  Wrong    : {summary['wrong']}\n\n")
        f.write("-" * 60 + "\n")
        f.write(f"  {'Q':<4}  {'St':<3}  {'Fuzzy':<6}  {'Student Answer':<30}  {'Model Answer'}\n")
        f.write("-" * 60 + "\n")

        for r in results:
            icon = VERDICT_ICON.get(r["verdict"], "[ ]")
            f.write(
                f"  Q{r['num']:<3}  {icon}  {r['fuzzy_score']:<6}  "
                f"{r['student'][:30]:<30}  {r['model']}\n"
            )

        f.write("\n" + "=" * 60 + "\n")
        f.write("Legend: [✓] Correct  [~] Partial  [✗] Wrong  [ ] Blank\n")

    print(f"[REPORT] Saved → {output_path}")


def save_csv_report(results, summary, output_path="result_report.csv"):
    try:
        import pandas as pd
        rows = []
        for r in results:
            rows.append({
                "Question #": r["num"],
                "Student Answer": r["student"],
                "Model Answer": r["model"],
                "Fuzzy Score": r["fuzzy_score"],
                "Result": r["verdict"].upper(),
            })
        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        print(f"[REPORT] Saved → {output_path}")
    except ImportError:
        # Fallback: write CSV manually
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Question #,Student Answer,Model Answer,Fuzzy Score,Result\n")
            for r in results:
                sa = r['student'].replace(',', ';')
                ma = r['model'].replace(',', ';')
                f.write(f"{r['num']},{sa},{ma},{r['fuzzy_score']},{r['verdict'].upper()}\n")
        print(f"[REPORT] Saved → {output_path}")


def print_console_report(results, summary):
    COLORS = {
        "correct": "\033[92m",  # green
        "partial": "\033[93m",  # yellow
        "wrong":   "\033[91m",  # red
        "blank":   "\033[90m",  # gray
    }
    RESET = "\033[0m"
    ICONS = {"correct": "✓", "partial": "~", "wrong": "✗", "blank": " "}

    print("\n" + "=" * 65)
    print(f"  SCORE: {summary['percent']}%  |  Grade: {summary['grade']}  |  "
          f"Correct: {summary['correct']}  Partial: {summary['partial']}  Wrong: {summary['wrong']}")
    print("=" * 65)
    print(f"  {'Q':<4} {'':3} {'Fuzzy':>6}   {'Student Answer':<28}  Model Answer")
    print("-" * 65)

    for r in results:
        color = COLORS.get(r["verdict"], "")
        icon = ICONS.get(r["verdict"], " ")
        student_trunc = r["student"][:27] + "…" if len(r["student"]) > 28 else r["student"]
        print(
            f"  Q{r['num']:<3} {color}[{icon}]{RESET}  {r['fuzzy_score']:>5.1f}   "
            f"{student_trunc:<28}  {r['model']}"
        )

    print("=" * 65)
    print(f"\n  [✓] Correct  [~] Partial (≥{PARTIAL_THRESHOLD}%)  [✗] Wrong  [ ] Blank\n")


def main():
    parser = argparse.ArgumentParser(description="Grade student answers against model answers")
    parser.add_argument("--student", default="student_answers.txt",
                        help="Path to student answers file (default: student_answers.txt)")
    parser.add_argument("--model", required=True,
                        help="Path to model answers file")
    parser.add_argument("--correct-threshold", type=int, default=CORRECT_THRESHOLD,
                        help=f"Fuzzy score for CORRECT (default: {CORRECT_THRESHOLD})")
    parser.add_argument("--partial-threshold", type=int, default=PARTIAL_THRESHOLD,
                        help=f"Fuzzy score for PARTIAL (default: {PARTIAL_THRESHOLD})")
    args = parser.parse_args()

    global CORRECT_THRESHOLD, PARTIAL_THRESHOLD
    CORRECT_THRESHOLD = args.correct_threshold
    PARTIAL_THRESHOLD = args.partial_threshold

    print(f"[LOAD] Student answers: {args.student}")
    student_answers = load_answers(args.student)
    print(f"[LOAD] Model answers  : {args.model}")
    model_answers = load_answers(args.model)

    print(f"\n[GRADE] Comparing {len(student_answers)} student answers vs {len(model_answers)} model answers...")
    results = grade(student_answers, model_answers)
    summary = compute_summary(results)

    print_console_report(results, summary)
    save_txt_report(results, summary)
    save_csv_report(results, summary)

    print(f"\n[DONE] Files saved: result_report.txt, result_report.csv")


if __name__ == "__main__":
    main()