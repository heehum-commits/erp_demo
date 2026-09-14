# -*- coding: utf-8 -*-
"""
Gemini API 호출 예제 (간단 버전)

사용법
    python gemini_call.py "한국 물류 산업을 세 줄로 설명해줘"
    python gemini_call.py                    # 인자를 안 주면 기본 질문
    python gemini_call.py --models           # 쓸 수 있는 모델 목록 보기
    python gemini_call.py -m gemini-3.6-flash "질문"

붐빌 때
    기본 모델이 503(붐빔)을 내면 2초 간격으로 두 번 더 시도하고,
    그래도 안 되면 대체 모델(gemini-3.6-flash -> gemini-2.5-pro)로 자동으로 바꿔 시도합니다.

준비물
    1) .env 파일에 키 한 줄:  gemini_api_key=발급받은키
    2) pip install google-genai   (이미 설치되어 있음: 2.22.0)

주의
    .env 는 .gitignore 에 들어 있어 git 에 올라가지 않습니다.
    키를 남에게 보여주거나 코드 안에 직접 적지 마세요.
"""

import logging
import sys
import time
from pathlib import Path

# SDK 가 띄우는 참고용 경고를 화면에서 숨긴다 (동작에는 영향 없음)
logging.getLogger("google_genai").setLevel(logging.ERROR)

# 윈도우 명령창에서 한글이 깨지지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 'gemini-flash-latest' 는 늘 최신 flash 를 가리키는 별칭이라 이름이 낡지 않는다.
# 특정 버전을 고정하고 싶으면 -m 옵션으로 바꿔 쓴다. (2026-09-14 동작 확인: gemini-3.6-flash)
DEFAULT_MODEL = "gemini-3.6-flash"
DEFAULT_PROMPT = "안녕하세요. 한 문장으로 자기소개를 해주세요."

# 기본 모델이 붐벼서 503 이 나오면 순서대로 대신 써볼 모델 (2026-09-14 동작 확인)
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-2.5-pro"]
RETRY_COUNT = 2      # 같은 모델로 다시 시도할 횟수
RETRY_WAIT = 2       # 다시 시도하기 전 기다리는 초

# .env 에서 찾아볼 키 이름들 (대소문자 구분 없이)
KEY_NAMES = ("gemini_api_key", "google_api_key")


def load_env(filename=".env"):
    """.env 파일을 읽어 딕셔너리로 돌려준다. (외부 라이브러리 없이)"""
    env = {}
    path = Path(__file__).resolve().parent / filename
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        env[name.strip()] = value.strip().strip('"').strip("'")
    return env


def find_api_key():
    """.env 에서 API 키를 찾는다. 없으면 None."""
    env = load_env()
    lowered = {k.lower(): v for k, v in env.items()}
    for name in KEY_NAMES:
        value = lowered.get(name)
        if value:
            return value
    return None


def mask(key):
    """키를 화면에 보여줄 때 가운데를 가린다."""
    if not key or len(key) < 10:
        return "****"
    return key[:4] + "*" * 8 + key[-4:]


def list_models(client):
    """generateContent 를 지원하는 모델 이름을 출력한다."""
    print("쓸 수 있는 모델")
    count = 0
    for model in client.models.list():
        actions = getattr(model, "supported_actions", None) or []
        if actions and "generateContent" not in actions:
            continue
        name = (model.name or "").replace("models/", "")
        print("  -", name)
        count += 1
    print(f"\n총 {count}개")


def is_busy(error):
    """503 처럼 '잠시 붐빔' 오류인지 확인한다."""
    text = str(error)
    return "503" in text or "UNAVAILABLE" in text or "high demand" in text


def is_quota(error):
    """429 - 무료 사용 횟수를 다 썼을 때. 기다려도 안 풀리므로 다른 모델로 넘어간다."""
    text = str(error)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "exceeded your current quota" in text


def call_once(client, model, prompt):
    """한 모델로 한 번 호출한다. 실패하면 예외를 그대로 올린다."""
    return client.models.generate_content(model=model, contents=prompt)


def call_with_retry(client, model, prompt):
    """붐빌 때는 잠깐 기다렸다 다시, 그래도 안 되면 대체 모델로 넘어간다."""
    candidates = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_error = None

    for index, name in enumerate(candidates):
        for attempt in range(RETRY_COUNT + 1):
            try:
                response = call_once(client, name, prompt)
                if index > 0 or attempt > 0:
                    print(f"[알림] '{name}' 로 응답을 받았습니다.")
                return name, response
            except Exception as error:
                last_error = error
                if is_quota(error):
                    if index < len(candidates) - 1:
                        print(f"[전환] '{name}' 의 무료 횟수를 다 썼습니다. "
                              f"'{candidates[index + 1]}' 로 바꿔서 시도합니다.")
                    break                      # 같은 모델로 다시 해도 소용없다
                if not is_busy(error):
                    raise                      # 붐빔도 한도도 아니면 바로 알린다
                if attempt < RETRY_COUNT:
                    print(f"[재시도] '{name}' 가 붐빕니다. {RETRY_WAIT}초 뒤 다시 시도 "
                          f"({attempt + 1}/{RETRY_COUNT})")
                    time.sleep(RETRY_WAIT)
                elif index < len(candidates) - 1:
                    print(f"[전환] '{name}' 가 계속 붐빕니다. "
                          f"'{candidates[index + 1]}' 로 바꿔서 시도합니다.")

    raise last_error


def ask(client, model, prompt):
    """질문 하나를 보내고 답을 출력한다."""
    print(f"[모델] {model}")
    print(f"[질문] {prompt}")
    print("-" * 60)

    used_model, response = call_with_retry(client, model, prompt)
    if used_model != model:
        print(f"(실제로 답한 모델: {used_model})")

    text = getattr(response, "text", None)
    print(text if text else "(답변이 비어 있습니다)")

    usage = getattr(response, "usage_metadata", None)
    if usage:
        print("-" * 60)
        print(
            "[토큰] 질문 {} / 답변 {} / 합계 {}".format(
                getattr(usage, "prompt_token_count", "?"),
                getattr(usage, "candidates_token_count", "?"),
                getattr(usage, "total_token_count", "?"),
            )
        )


def main():
    args = sys.argv[1:]

    model = DEFAULT_MODEL
    if "-m" in args:
        i = args.index("-m")
        if i + 1 >= len(args):
            print("오류: -m 뒤에 모델 이름을 적어주세요.")
            return 1
        model = args[i + 1]
        del args[i : i + 2]

    want_models = "--models" in args
    if want_models:
        args.remove("--models")

    prompt = " ".join(args).strip() or DEFAULT_PROMPT

    api_key = find_api_key()
    if not api_key:
        print("오류: API 키를 찾지 못했습니다.")
        print()
        print("  이 파일과 같은 폴더에 .env 를 만들고 아래 한 줄을 넣어주세요.")
        print("      gemini_api_key=발급받은키")
        print()
        print("  키 발급: https://aistudio.google.com/apikey")
        return 1

    print(f"[키] {mask(api_key)} (.env 에서 읽음)")

    try:
        from google import genai
    except ImportError:
        print("오류: google-genai 가 설치되어 있지 않습니다.")
        print("      pip install google-genai")
        return 1

    client = genai.Client(api_key=api_key)

    try:
        if want_models:
            list_models(client)
        else:
            ask(client, model, prompt)
    except Exception as error:
        print()
        print("오류: 호출에 실패했습니다.")
        print("  ", type(error).__name__, "-", error)
        print()
        print("  자주 있는 원인")
        print("   - 404: 모델 이름이 틀렸거나 더 이상 제공되지 않음")
        print("          -> python gemini_call.py --models 로 목록 확인")
        print("   - 503: 그 모델에 사람이 몰림. 잠시 뒤 다시 하거나 다른 모델 사용")
        print("   - 401/403: 키가 틀렸거나 만료됨 -> .env 의 gemini_api_key 확인")
        print("   - 429: 무료 한도 초과")
        print("   - 그 밖: 인터넷 연결 / 방화벽 확인")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
