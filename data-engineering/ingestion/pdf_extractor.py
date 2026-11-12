from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

import fitz  # PyMuPDF


MATH_PATTERN = re.compile(
    r"(\$\$?.+?\$\$?|\\frac\{.*?\}\{.*?\}|\\sqrt\{.*?\}|"
    r"(?:sin|cos|tan|cot|sec|cosec)\s*\^?\s*\d*\s*[θA-Za-z\(\)]+|"
    r"[A-Za-z0-9\)]+\s*[\^²³]\s*[0-9A-Za-z\+\-]+|"
    r"[A-Za-z0-9]+\s*[=<>≤≥]\s*[A-Za-z0-9\+\-\*/\^\(\)\s\.]+)"
)

QUESTION_START_RE = re.compile(
    r"(?m)^(?:Q\.?\s*(\d{1,3})[\.\):]|\s*(\d{1,3})\.\s+(?=[A-Z0-9\(])|\s*Question\s+(\d{1,3})\s*[:\.\-])"
)
SECTION_RE = re.compile(r"(?im)^\s*(Section\s*[-–:]?\s*[A-E])\b.*$")
MARKS_RE = re.compile(
    r"(?:\[(\d+(?:\.\d+)?)\s*(?:marks?|m)?\]|\((\d+(?:\.\d+)?)\s*(?:marks?|m)\)|(\d+(?:\.\d+)?)\s*Marks?\s*$)",
    re.IGNORECASE,
)
OPTION_RE = re.compile(
    r"(?m)^\s*\(?([A-Da-d])\)[\.\)]\s+(.+?)(?=\n\s*\(?[A-Da-d]\)[\.\)]|\n\s*(?:Ans|Answer|Q\.?\s*\d|\d+\.\s)|$)",
    re.DOTALL,
)
ANSWER_INLINE_RE = re.compile(r"(?im)^(?:Ans(?:wer)?|Key)\s*[:\-]\s*(.+)$")


@dataclass
class ExtractedPage:
    page_number: int
    raw_text: str
    used_ocr: bool = False
    char_count: int = 0


@dataclass
class ExtractedQuestionRecord:
    question_number: str
    section_name: str | None
    page_number: int
    question_text: str
    normalized_text: str
    math_expressions: list[str] = field(default_factory=list)
    question_type: str = "short_answer"
    marks: float = 1.0
    options: list[dict[str, Any]] = field(default_factory=list)
    answer_text: str | None = None
    content_hash: str = ""
    confidence_score: float = 0.88


@dataclass
class ExtractionResult:
    pages: list[ExtractedPage]
    questions: list[ExtractedQuestionRecord]
    used_ocr_pages: int
    overall_confidence: float
    warnings: list[str] = field(default_factory=list)


def normalize_question_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = cleaned.replace("−", "-").replace("×", "*").replace("÷", "/")
    return cleaned


def extract_math_expressions(text: str) -> list[str]:
    matches = []
    for m in MATH_PATTERN.finditer(text):
        expr = m.group(0).strip()
        if len(expr) >= 3 and expr not in matches:
            matches.append(expr)
    return matches[:15]


def infer_question_type(text: str, options: list[dict[str, Any]], marks: float) -> str:
    lower = text.lower()
    if "assertion" in lower and "reason" in lower:
        return "assertion_reason"
    if len(options) >= 2:
        return "mcq"
    if "read the following" in lower or "case study" in lower or "based on the above" in lower:
        return "case_study"
    if marks <= 1.0:
        return "very_short"
    if marks <= 2.0:
        return "short_answer"
    if marks >= 4.0:
        return "long_answer"
    return "short_answer"


def _try_ocr_page(page: fitz.Page) -> tuple[str, bool]:
    """Attempt OCR fallback if pytesseract & pillow are installed; fail gracefully otherwise."""
    try:
        import io
        from PIL import Image
        import pytesseract

        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img)
        return text or "", True
    except Exception:
        return "", False


def extract_pdf_questions(pdf_bytes: bytes) -> ExtractionResult:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[ExtractedPage] = []
    warnings: list[str] = []
    used_ocr_pages = 0

    for idx in range(len(doc)):
        page = doc[idx]
        text = page.get_text("text") or ""
        used_ocr = False
        if len(text.strip()) < 25:
            ocr_text, ok = _try_ocr_page(page)
            if ok and ocr_text.strip():
                text = ocr_text
                used_ocr = True
                used_ocr_pages += 1
            else:
                warnings.append(
                    f"Page {idx + 1} has low extractable text ({len(text.strip())} chars) and OCR engine is unavailable."
                )
        pages.append(
            ExtractedPage(
                page_number=idx + 1,
                raw_text=text,
                used_ocr=used_ocr,
                char_count=len(text),
            )
        )

    questions: list[ExtractedQuestionRecord] = []
    current_section: str | None = None

    for p in pages:
        sec_match = SECTION_RE.search(p.raw_text)
        if sec_match:
            current_section = sec_match.group(1).strip().title()

        matches = list(QUESTION_START_RE.finditer(p.raw_text))
        if not matches:
            continue

        for i, match in enumerate(matches):
            q_num = next((g for g in match.groups() if g is not None), str(len(questions) + 1))
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(p.raw_text)
            block = p.raw_text[start:end].strip()
            if len(block) < 12:
                continue

            # Extract marks if annotated
            marks = 1.0
            marks_match = MARKS_RE.search(block)
            if marks_match:
                val = next((g for g in marks_match.groups() if g is not None), None)
                if val:
                    marks = float(val)
                block = MARKS_RE.sub("", block).strip()

            # Extract inline answer if present
            answer_text = None
            ans_match = ANSWER_INLINE_RE.search(block)
            if ans_match:
                answer_text = ans_match.group(1).strip()
                block = ANSWER_INLINE_RE.sub("", block).strip()

            # Extract MCQ options
            options: list[dict[str, Any]] = []
            opt_matches = list(OPTION_RE.finditer(block))
            stem_text = block
            if len(opt_matches) >= 2:
                stem_text = block[: opt_matches[0].start()].strip()
                for om in opt_matches:
                    label = om.group(1).upper()
                    opt_txt = normalize_question_text(om.group(2))
                    is_corr = bool(answer_text and answer_text.strip().upper().startswith(label))
                    options.append(
                        {"option_label": label, "option_text": opt_txt, "is_correct": is_corr}
                    )

            clean_stem = normalize_question_text(stem_text)
            if len(clean_stem) < 10:
                continue

            math_exprs = extract_math_expressions(clean_stem)
            q_type = infer_question_type(clean_stem, options, marks)
            content_hash = hashlib.sha256(clean_stem.lower().encode("utf-8")).hexdigest()
            conf = 0.72 if p.used_ocr else 0.91
            if marks_match:
                conf = min(0.97, conf + 0.04)

            questions.append(
                ExtractedQuestionRecord(
                    question_number=q_num,
                    section_name=current_section,
                    page_number=p.page_number,
                    question_text=clean_stem,
                    normalized_text=clean_stem.lower(),
                    math_expressions=math_exprs,
                    question_type=q_type,
                    marks=marks,
                    options=options,
                    answer_text=answer_text,
                    content_hash=content_hash,
                    confidence_score=round(conf, 3),
                )
            )

    overall_conf = (
        round(sum(q.confidence_score for q in questions) / len(questions), 3)
        if questions
        else 0.0
    )
    return ExtractionResult(
        pages=pages,
        questions=questions,
        used_ocr_pages=used_ocr_pages,
        overall_confidence=overall_conf,
        warnings=warnings,
    )
