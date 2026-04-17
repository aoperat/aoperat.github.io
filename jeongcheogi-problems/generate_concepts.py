"""
정보처리기사 실기 문제별 개념 데이터 생성기
- 각 문제마다 핵심 개념, 상세 설명, 자주 틀리는 이유, 관련 개념 생성
- 중간에 중단되어도 이어서 진행 (progress 저장)
- 결과: problems_output/concepts.json
"""

import json
import time
import sys
from pathlib import Path

# ── Anthropic SDK 확인 ─────────────────────────────────────
try:
    import anthropic
except ImportError:
    print("Anthropic SDK를 설치합니다...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic"])
    import anthropic

# ── API 키 확인 ──────────────────────────────────────────────
import os
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("=" * 55)
    print("ANTHROPIC_API_KEY 환경변수가 설정되어 있지 않습니다.")
    print()
    print("설정 방법:")
    print("  export ANTHROPIC_API_KEY='sk-ant-...'")
    print("  python3 generate_concepts.py")
    print()
    print("Claude Code 내에서는:")
    print("  ! export ANTHROPIC_API_KEY='sk-ant-...' && python3 generate_concepts.py")
    print("=" * 55)
    sys.exit(1)

# ── 경로 설정 ────────────────────────────────────────────────
BASE = Path("/Users/ijonghwan/Documents/test")
PROBLEMS_PATH = BASE / "problems_output" / "problems.json"
CONCEPTS_PATH = BASE / "problems_output" / "concepts.json"
PROGRESS_PATH = BASE / "problems_output" / "concepts_progress.json"

# ── Claude 클라이언트 ────────────────────────────────────────
client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용

# ── 프롬프트 ─────────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 정보처리기사 실기 시험 전문 튜터입니다.
주어진 문제와 정답을 분석하여 학생이 깊이 이해하고 시험에 대비할 수 있도록 도와주는 학습 데이터를 생성합니다.
반드시 JSON 형식으로만 응답하세요."""

def make_user_prompt(problem):
    q = problem.get("question", "")[:500]
    a = problem.get("answer", "")[:300]
    return f"""다음 정보처리기사 실기 문제와 정답을 분석하여 학습 데이터를 JSON으로 생성하세요.

문제 번호: {problem['id']}
문제: {q}
정답: {a}

다음 JSON 형식으로 응답하세요:
{{
  "id": {problem['id']},
  "summary": "정답에 대한 1~2줄 핵심 요약 (학생이 답을 외울 때 도움이 되는 핵심 포인트)",
  "detail": "개념에 대한 3~5줄 상세 설명 (왜 이것이 답인지, 어떤 맥락에서 사용되는지)",
  "key_concepts": ["핵심개념1", "핵심개념2", "핵심개념3"],
  "common_mistakes": [
    "자주 틀리는 이유 또는 혼동하기 쉬운 유사 개념",
    "두 번째 자주 틀리는 이유"
  ],
  "related": ["관련개념1", "관련개념2", "관련개념3"]
}}

규칙:
- key_concepts: 이 문제에서 테스트하는 핵심 용어/개념 3~5개
- common_mistakes: 학생들이 자주 혼동하는 유사 개념이나 오개념 1~3개
- related: 함께 공부하면 좋은 관련 개념 3~5개
- 모든 내용은 한국어로 작성
- JSON만 응답 (다른 텍스트 없이)"""

# ── 메인 로직 ─────────────────────────────────────────────────
def generate_concept(problem, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",  # 빠르고 저렴한 모델 사용
                max_tokens=800,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": make_user_prompt(problem)}]
            )
            text = response.content[0].text.strip()
            # JSON 추출 (```json ... ``` 감싸진 경우 처리)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  JSON 파싱 실패 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
        except anthropic.RateLimitError:
            print(f"  Rate limit - 10초 대기...")
            time.sleep(10)
        except Exception as e:
            print(f"  오류 (시도 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    return None

def main():
    # 문제 로드
    with open(PROBLEMS_PATH, encoding="utf-8") as f:
        problems = json.load(f)

    # 기존 진행 상황 로드
    existing = {}
    if CONCEPTS_PATH.exists():
        with open(CONCEPTS_PATH, encoding="utf-8") as f:
            for item in json.load(f):
                existing[item["id"]] = item

    progress = {}
    if PROGRESS_PATH.exists():
        with open(PROGRESS_PATH, encoding="utf-8") as f:
            progress = json.load(f)

    total = len(problems)
    done = len(existing)
    print(f"총 {total}문제 중 {done}개 완료, {total - done}개 남음\n")

    for i, prob in enumerate(problems):
        pid = prob["id"]
        if pid in existing:
            continue  # 이미 완료

        print(f"[{i+1}/{total}] {pid}번 문제 생성 중...", end=" ", flush=True)
        start = time.time()

        concept = generate_concept(prob)

        if concept:
            existing[pid] = concept
            elapsed = time.time() - start
            print(f"✓ ({elapsed:.1f}s)")

            # 10개마다 중간 저장
            if len(existing) % 10 == 0:
                save(existing)
                print(f"  → {len(existing)}개 저장 완료")
        else:
            print(f"✗ 실패 (건너뜀)")

        # Rate limit 방지 (Haiku: 초당 50 req)
        time.sleep(0.3)

    # 최종 저장
    save(existing)
    print(f"\n완료! {len(existing)}개 개념 데이터 저장: {CONCEPTS_PATH}")

def save(existing):
    result = sorted(existing.values(), key=lambda x: x["id"])
    with open(CONCEPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
