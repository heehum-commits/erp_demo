# -*- coding: utf-8 -*-
"""
Gemini 연동 점검 — 인사·총무 앱의 AI 기능이 실제로 동작하는지 5단계로 확인한다.

사용법
    python gemini_test.py

코딩을 모르면
    같은 폴더의  연결테스트.bat  을 더블클릭하세요.

확인하는 것
    1단계  .env 파일에서 API 키를 읽을 수 있는가
    2단계  google-genai 라이브러리가 깔려 있는가
    3단계  키로 실제 접속이 되는가 (모델 목록 받아오기)
    4단계  앱(index.html)이 쓰는 모델을 실제로 쓸 수 있는가
    5단계  진짜 질문 하나를 보내고 답을 받는가

주의
    이 프로그램은 무료 사용 횟수를 1회 정도 씁니다.
    API 키는 화면에 가려서(AQ.A********Gi4g) 나오며, 파일로 저장하지 않습니다.
"""

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
APP = HERE / "index.html"
TEST_PROMPT = "연결 확인용입니다. '연결 성공'이라고만 답해주세요."

results = []       # (단계이름, 통과여부, 한 줄 설명)


def step(no, title):
    print()
    print(f"[{no}단계] {title}")


def ok(name, msg):
    print(f"  통과   {msg}")
    results.append((name, True, msg))


def fail(name, msg, how):
    print(f"  실패   {msg}")
    print(f"         -> {how}")
    results.append((name, False, msg))
    return False


def app_models():
    """index.html 안에 적힌 AI_MODELS 목록을 그대로 읽어온다."""
    if not APP.exists():
        return []
    text = APP.read_text(encoding="utf-8", errors="ignore")
    mark = "var AI_MODELS = ["
    at = text.find(mark)
    if at < 0:
        return []
    body = text[at + len(mark): text.find("]", at)]
    return [p.strip().strip('"').strip("'") for p in body.split(",") if p.strip()]


def main():
    print("=" * 56)
    print(" 인사·총무 앱 — Gemini 연동 점검")
    print("=" * 56)

    # ---- 1단계: .env 에서 키 읽기 -------------------------------
    step(1, ".env 파일에서 API 키 읽기")
    try:
        from gemini_call import find_api_key, mask
    except Exception as e:
        return fail("키 읽기", f"gemini_call.py 를 불러오지 못했습니다 ({e})",
                    "gemini_call.py 가 같은 폴더에 있는지 확인하세요.")
    if not (HERE / ".env").exists():
        return fail("키 읽기", ".env 파일이 없습니다.",
                    ".env.example 을 복사해 .env 로 만들고 키를 넣으세요.")
    key = find_api_key()
    if not key:
        return fail("키 읽기", ".env 안에 gemini_api_key 값이 없습니다.",
                    ".env 파일에  gemini_api_key=발급받은키  한 줄을 넣으세요.")
    ok("키 읽기", f"키를 찾았습니다: {mask(key)} (길이 {len(key)}자)")

    # ---- 2단계: 라이브러리 확인 ----------------------------------
    step(2, "google-genai 라이브러리 확인")
    try:
        from google import genai
    except Exception:
        return fail("라이브러리", "google-genai 가 설치되어 있지 않습니다.",
                    "명령창에서  pip install google-genai  를 실행하세요.")
    ok("라이브러리", "설치되어 있습니다.")

    # ---- 3단계: 실제 접속 ---------------------------------------
    step(3, "키로 실제 접속 (모델 목록 받아오기)")
    try:
        client = genai.Client(api_key=key)
        usable = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            if "generateContent" in actions:
                usable.append(m.name.replace("models/", ""))
    except Exception as e:
        msg = str(e)
        if "API_KEY_INVALID" in msg or "API key not valid" in msg:
            return fail("접속", "키가 올바르지 않다고 거부당했습니다.",
                        "https://aistudio.google.com/apikey 에서 키를 다시 발급받아 .env 에 넣으세요.")
        return fail("접속", f"접속하지 못했습니다 ({msg[:120]})",
                    "인터넷 연결 또는 회사 방화벽을 확인하세요.")
    ok("접속", f"접속 성공. 쓸 수 있는 모델 {len(usable)}개")

    # ---- 4단계: 앱이 쓰는 모델과 대조 ----------------------------
    step(4, "앱(index.html)이 쓰는 모델을 실제로 쓸 수 있는지 대조")
    wanted = app_models()
    if not wanted:
        print("  건너뜀 index.html 에서 모델 목록을 찾지 못했습니다.")
        wanted = ["gemini-3.6-flash"]
    live = [m for m in wanted if m in usable]
    for m in wanted:
        print(f"         {'O' if m in usable else 'X'}  {m}")
    if not live:
        return fail("모델 대조", "앱이 쓰는 모델을 하나도 쓸 수 없습니다.",
                    "index.html 의 AI_MODELS 목록을 위 '쓸 수 있는 모델' 로 바꿔야 합니다.")
    ok("모델 대조", f"{len(live)}/{len(wanted)}개 사용 가능 (앱은 위에서부터 차례로 시도합니다)")

    # ---- 5단계: 실제 질문 한 번 ----------------------------------
    step(5, "진짜 질문을 보내고 답 받기")
    model = live[0]
    try:
        res = client.models.generate_content(model=model, contents=TEST_PROMPT)
        answer = (getattr(res, "text", "") or "").strip()
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
            return fail("질문", "오늘 무료 사용 횟수를 다 썼습니다.",
                        "내일 다시 시도하거나 다른 모델을 쓰세요. (키 자체는 정상입니다)")
        return fail("질문", f"답을 받지 못했습니다 ({msg[:120]})", "잠시 뒤 다시 실행해 보세요.")
    if not answer:
        return fail("질문", "빈 답이 왔습니다.", "잠시 뒤 다시 실행해 보세요.")
    ok("질문", f"'{model}' 응답: {answer[:60]}")
    return True


if __name__ == "__main__":
    good = False
    try:
        good = bool(main())
    except KeyboardInterrupt:
        print("\n중단했습니다.")
        sys.exit(1)

    print()
    print("=" * 56)
    passed = sum(1 for _, p, _ in results if p)
    if good:
        print(f" 결과: 정상 — {passed}단계 모두 통과했습니다.")
        print(" 앱의 AI 브리핑 / AI 에게 물어보기 기능을 쓸 수 있습니다.")
        print(" (앱에서는 .env 가 아니라 화면에서 키를 한 번 넣어야 합니다:")
        print("  홈 > AI 브리핑 > 키 설정 > 연결 테스트)")
    else:
        print(f" 결과: 문제 있음 — {passed}단계까지 통과. 위의 -> 안내를 따라주세요.")
    print("=" * 56)
    sys.exit(0 if good else 1)
