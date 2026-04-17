import fitz
import re
import json
from pathlib import Path
from collections import Counter, defaultdict

PDF_PATH = "/Users/ijonghwan/Documents/test/정보처리기사실기_01_키워드찾기130문제.pdf"
OUTPUT_DIR = Path("/Users/ijonghwan/Documents/test/problems_output")
IMAGES_DIR = OUTPUT_DIR / "images"

OUTPUT_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

doc = fitz.open(PDF_PATH)

# ── 이미지 필터 ──────────────────────────────────────────────
_bbox_counter = Counter()
for _page in doc:
    for _b in _page.get_text("dict")["blocks"]:
        if _b.get("type") == 1:
            _bbox_counter[tuple(round(x) for x in _b["bbox"])] += 1

REPEATED_BBOXES = {bbox for bbox, cnt in _bbox_counter.items() if cnt >= 2}

def is_content_image(bbox):
    key = tuple(round(x) for x in bbox)
    if key in REPEATED_BBOXES:
        return False
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    return w >= 60 and h >= 50

# ── 텍스트 정제 ──────────────────────────────────────────────
# 완전히 공백뿐인 span만 제거 (구두점은 실제 내용이므로 보존)
WHITESPACE_ONLY_RE = re.compile(r'^\s+$')

def clean_text(text):
    """HWP 아티팩트 정제 (공백 정규화만)"""
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def spans_to_line_text(spans):
    """
    같은 y에 있는 span들을 텍스트로 합치기.
    x 좌표 순으로 정렬 후 스마트 공백 삽입:
    - 앞 span이 공백 없이 끝나고 뒤 span이 공백 없이 시작 → 붙임 (단어 연결)
    - 그 외 → 공백 삽입
    """
    sorted_spans = sorted(
        [s for s in spans if not WHITESPACE_ONLY_RE.fullmatch(s["text"])],
        key=lambda s: s["bbox"][0]
    )

    result = ""
    for s in sorted_spans:
        t = s["text"]
        if not result:
            result = t
        elif result[-1] in " \t\n" or t[0] in " \t\n":
            result += t  # 이미 공백 있음
        else:
            result += t  # 공백 없이 이어짐 (분리된 음절 복원)
    return result.strip()

# ── 표 감지 ──────────────────────────────────────────────────
def is_table_row(spans):
    """
    한 줄이 표의 행인지 판별:
    - span이 3개 이상
    - 모든 span이 짧은 값(최대 15자 이하) - 긴 문장 span이 하나라도 있으면 일반 텍스트
    """
    content_spans = [s for s in spans if not WHITESPACE_ONLY_RE.fullmatch(s["text"])]
    if len(content_spans) < 3:
        return False
    max_len = max(len(s["text"].strip()) for s in content_spans)
    return max_len <= 10

def spans_to_table_row(spans):
    """표 행: span을 x 순서로 정렬 후 | 구분자로 연결"""
    content_spans = sorted(
        [s for s in spans if not WHITESPACE_ONLY_RE.fullmatch(s["text"])],
        key=lambda s: s["bbox"][0]
    )
    return "| " + " | ".join(s["text"].strip() for s in content_spans) + " |"

# ── 블록 → 텍스트 변환 ───────────────────────────────────────
def block_to_text(block):
    """
    블록 내 lines를 텍스트로 변환.
    표 행으로 판별되는 줄은 | 구분자로, 일반 줄은 연결.
    """
    result_lines = []
    # y별로 span 그룹핑 (같은 y = 시각적으로 같은 줄)
    y_groups = defaultdict(list)
    for line in block["lines"]:
        y = round(line["bbox"][1])
        y_groups[y].extend(line["spans"])

    for y in sorted(y_groups):
        spans = y_groups[y]
        if is_table_row(spans):
            result_lines.append(spans_to_table_row(spans))
        else:
            t = spans_to_line_text(spans)
            if t:
                result_lines.append(t)

    return "\n".join(result_lines)

# ── 문제 번호 감지 ────────────────────────────────────────────
PROBLEM_SPAN_RE = re.compile(r'^(\d{1,3})\.\s')

def find_problem_num_in_block(block):
    for line in block.get("lines", []):
        for span in line["spans"]:
            m = PROBLEM_SPAN_RE.match(span["text"])
            if m:
                return int(m.group(1))
    return None

# ── 전체 블록 수집 ────────────────────────────────────────────
all_page_blocks = []
for page_num, page in enumerate(doc):
    for block in page.get_text("dict")["blocks"]:
        all_page_blocks.append((page_num, block))

# ── 문제 경계 탐지 ────────────────────────────────────────────
problem_starts = {}
for i, (page_num, block) in enumerate(all_page_blocks):
    if block.get("type") == 0:
        num = find_problem_num_in_block(block)
        if num is not None and 1 <= num <= 130:
            if num not in problem_starts:
                problem_starts[num] = i

sorted_nums = sorted(problem_starts.keys())
problem_ranges = {}
for i, num in enumerate(sorted_nums):
    start = problem_starts[num]
    end = problem_starts[sorted_nums[i + 1]] if i + 1 < len(sorted_nums) else len(all_page_blocks)
    problem_ranges[num] = (start, end)

# ── 이미지 저장 ───────────────────────────────────────────────
img_save_counter = [0]

def save_image(page_num, bbox):
    img_save_counter[0] += 1
    img_filename = f"img_{img_save_counter[0]:04d}.png"
    img_path = IMAGES_DIR / img_filename
    page = doc[page_num]
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat, clip=fitz.Rect(bbox))
    pix.save(str(img_path))
    return f"images/{img_filename}"

# ── 문제 추출 ─────────────────────────────────────────────────
problems = []

for num in sorted_nums:
    start, end = problem_ranges[num]
    blocks_in_range = all_page_blocks[start:end]

    question_parts = []
    answer_parts = []
    image_paths = []
    in_answer = False

    for page_num, block in blocks_in_range:
        btype = block.get("type")

        if btype == 1:
            if not is_content_image(block["bbox"]):
                continue
            img_path = save_image(page_num, block["bbox"])
            image_paths.append(img_path)

        elif btype == 0:
            text = block_to_text(block)
            if not text:
                continue

            if re.match(r'^답\s*[:\s]', text) or re.match(r'^\[?해설', text) or text.startswith('답\n') or text == '답':
                in_answer = True

            if in_answer:
                answer_parts.append(text)
            else:
                question_parts.append(text)

    # 문제 번호 prefix 제거 및 정제
    question_text = "\n".join(question_parts).strip()
    question_text = re.sub(r'(?m)^' + str(num) + r'\.\s*', '', question_text, count=1).strip()
    question_text = clean_text(question_text)

    answer_text = "\n".join(answer_parts).strip()
    answer_text = clean_text(answer_text)

    problems.append({
        "id": num,
        "question": question_text,
        "answer": answer_text,
        "images": image_paths
    })

# ── 저장 ──────────────────────────────────────────────────────
json_path = OUTPUT_DIR / "problems.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(problems, f, ensure_ascii=False, indent=2)

jsonl_path = OUTPUT_DIR / "problems.jsonl"
with open(jsonl_path, "w", encoding="utf-8") as f:
    for p in problems:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")

print(f"추출 완료!")
print(f"  - 문제 수: {len(problems)}")
print(f"  - 이미지 수: {img_save_counter[0]}")

print("\n=== 13번 (표 포함) ===")
p13 = next(p for p in problems if p["id"] == 13)
print(f"문제:\n{p13['question']}\n답: {p13['answer']}")

print("\n=== 1번 (텍스트 정제) ===")
p1 = next(p for p in problems if p["id"] == 1)
print(f"문제:\n{p1['question']}\n답: {p1['answer']}")

print("\n=== 이미지 포함 문제 ===")
for p in problems:
    if p["images"]:
        print(f"  [{p['id']}번] {p['images']}")
