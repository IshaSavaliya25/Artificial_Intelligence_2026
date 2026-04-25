"""
ONE-SHOT RUNNER — Extract + Grade in a single command
Usage:
    python run_evaluate.py --image answer_sheet.jpg --model model_answers.txt
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(
        description="AI Answer Sheet Evaluator — extract handwriting + grade in one step"
    )
    parser.add_argument("--image",  required=True, help="Student answer sheet image (JPG/PNG/PDF)")
    parser.add_argument("--model",  required=True, help="Model answers text file")
    parser.add_argument("--confidence", type=float, default=0.3, help="OCR confidence threshold")
    parser.add_argument("--correct-threshold", type=int, default=80)
    parser.add_argument("--partial-threshold", type=int, default=50)
    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  AI Answer Sheet Evaluator  (Offline / No API)")
    print("=" * 55)

    # ── Step 1: Extract ──────────────────────────────────────
    print("\n[STEP 1] Extracting handwritten answers...\n")
    import step1_extract as s1
    image_path = s1.load_image(args.image)
    ocr_results = s1.run_ocr(image_path)
    answers, raw_text = s1.parse_numbered_answers(ocr_results, args.confidence)
    s1.save_student_answers(answers)

    if len(answers) == 0:
        print("\nWARNING: No numbered answers found in the image.")
        print("Tips:")
        print("  - Make sure the image is clear and well-lit")
        print("  - Check extracted_raw.txt to see what OCR detected")
        print("  - Lower confidence threshold: --confidence 0.1")
        sys.exit(1)

    # ── Step 2: Grade ────────────────────────────────────────
    print(f"\n[STEP 2] Grading {len(answers)} extracted answers...\n")
    import step2_grade as s2
    s2.CORRECT_THRESHOLD = args.correct_threshold
    s2.PARTIAL_THRESHOLD = args.partial_threshold

    model_answers = s2.load_answers(args.model)
    results = s2.grade(answers, model_answers)
    summary = s2.compute_summary(results)

    s2.print_console_report(results, summary)
    s2.save_txt_report(results, summary)
    s2.save_csv_report(results, summary)

    print(f"\n[DONE] All files saved.")
    print(f"  extracted_raw.txt    — raw OCR output")
    print(f"  student_answers.txt  — parsed student answers")
    print(f"  result_report.txt    — grading report")
    print(f"  result_report.csv    — spreadsheet export")


if __name__ == "__main__":
    main()