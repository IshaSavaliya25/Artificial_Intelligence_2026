"""
STEP 1 — Extract handwritten answers from image using EasyOCR
Usage:
    python step1_extract.py --image answer_sheet.jpg
    python step1_extract.py --image answer_sheet.pdf   (converts first page)
Output:
    extracted_raw.txt   — raw OCR output
    student_answers.txt — parsed numbered answers
"""

import argparse
import re
import os
import sys

def load_image(path):
    """Load image from file path. Supports JPG, PNG, PDF (first page)."""
    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
        except ImportError:
            print("ERROR: pdf2image not installed. Run: pip install pdf2image")
            print("Also install poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
            sys.exit(1)
        pages = convert_from_path(path, dpi=300, first_page=1, last_page=1)
        img = pages[0]
        # Save as temp PNG for EasyOCR
        temp_path = "temp_page.png"
        img.save(temp_path)
        return temp_path
    else:
        return path


def run_ocr(image_path):
    """Run EasyOCR on the image and return list of (text, confidence) tuples."""
    try:
        import easyocr
    except ImportError:
        print("ERROR: easyocr not installed. Run: pip install easyocr")
        sys.exit(1)

    print(f"[OCR] Loading EasyOCR model (first run downloads ~100MB)...")
    reader = easyocr.Reader(['en'], gpu=False)  # gpu=True if you have CUDA

    print(f"[OCR] Processing: {image_path}")
    results = reader.readtext(image_path, detail=1, paragraph=False)

    # results = list of [bbox, text, confidence]
    return results


def parse_numbered_answers(ocr_results, confidence_threshold=0.3):
    """
    Parse OCR results into a dict of {question_num: answer_text}.
    Handles formats like:
        1. testing
        2. unlabeled
        1) testing
        1: testing
    """
    # Sort results top-to-bottom by vertical position of bounding box
    sorted_results = sorted(ocr_results, key=lambda r: r[0][0][1])  # sort by top-left y

    lines = []
    for bbox, text, conf in sorted_results:
        if conf < confidence_threshold:
            continue
        lines.append(text.strip())

    # Join all lines
    full_text = "\n".join(lines)

    # Save raw output
    with open("extracted_raw.txt", "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"[OCR] Raw text saved to extracted_raw.txt")

    # Parse numbered answers
    answers = {}
    # Pattern: starts with number followed by . ) : or space
    pattern = re.compile(r'^(\d+)\s*[.):\-]\s*(.+)$', re.MULTILINE)
    matches = pattern.findall(full_text)

    for num_str, answer in matches:
        num = int(num_str)
        answers[num] = answer.strip()

    # If the above misses lines (OCR may split number and answer),
    # try a simpler approach: number alone on one line, answer on next
    if len(answers) < 5:
        answers = {}
        current_num = None
        for line in lines:
            line = line.strip()
            # Check if line is just a number
            just_num = re.match(r'^(\d+)\s*[.):\-]?\s*$', line)
            if just_num:
                current_num = int(just_num.group(1))
                continue
            # Check if line starts with a number
            starts_num = re.match(r'^(\d+)\s*[.):\-]\s*(.+)$', line)
            if starts_num:
                answers[int(starts_num.group(1))] = starts_num.group(2).strip()
                current_num = None
            elif current_num is not None and line:
                answers[current_num] = line
                current_num = None

    return answers, full_text


def save_student_answers(answers):
    with open("student_answers.txt", "w", encoding="utf-8") as f:
        for num in sorted(answers.keys()):
            f.write(f"{num}. {answers[num]}\n")
    print(f"[PARSE] Found {len(answers)} answers → student_answers.txt")


def main():
    parser = argparse.ArgumentParser(description="Extract handwritten answers from image")
    parser.add_argument("--image ", required=True, help="Path to answer sheet image or PDF")
    parser.add_argument("--confidence", type=float, default=0.3,
                        help="Minimum OCR confidence threshold (0.0-1.0, default 0.3)")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        print(f"ERROR: File not found: {args.image}")
        sys.exit(1)

    # Load image (converts PDF if needed)
    image_path = load_image(args.image)

    # Run OCR
    ocr_results = run_ocr(image_path)

    # Show all detected text with confidence
    print("\n[OCR] All detected text:")
    print("-" * 50)
    for bbox, text, conf in sorted(ocr_results, key=lambda r: r[0][0][1]):
        print(f"  conf={conf:.2f}  |  {text}")
    print("-" * 50)

    # Parse answers
    answers, raw_text = parse_numbered_answers(ocr_results, args.confidence)

    # Save outputs
    save_student_answers(answers)

    print("\n[DONE] Extracted answers:")
    for num in sorted(answers.keys()):
        print(f"  {num}. {answers[num]}")

    print("\nNext step: run  python step2_grade.py")


if __name__ == "__main__":
    main()