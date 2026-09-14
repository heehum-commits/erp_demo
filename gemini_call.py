# -*- coding: utf-8 -*-
"""
Gemini API 호출 예제 (간단 버전)

사용법
    python gemini_call.py "한국 물류 산업을 세 줄로 설명해줘"
    python gemini_call.py                    # 인자를 안 주면 기본 질문
    python gemini_call.py --models           # 쓸 수 있는 모델 목록 보기
    python gemini_call.py -m gemini-2.5-pro "질문"

준비물
    1) .env 파일에 키 한 줄:  gemini_api_key=발급받은키
    2) pip install google-genai   (이미 설치되어 있음: 2.22.0)

주의
    .env 는 .gitignore 에 들어 있어 git 에 올라가지 않습니다.
    키를 남에게 보여주거나 코드 안에 직접 적지 마세요.
"""

import sys
from pathlib import Path

# 윈도우 명령창에서 한글이 깨지지 않도록
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_PROMPT = "안녕하세요. 한 문장으로 자기소개를 해주세요."

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


def ask(client, model, prompt):
    """질문 하나를 보내고 답을 출력한다."""
    print(f"[모델] {model}")
    print(f"[질문] {prompt}")
    print("-" * 60)

    response = client.models.generate_content(model=model, contents=prompt)

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
        print("   - 키가 틀렸거나 만료됨 -> .env 의 gemini_api_key 확인")
        print("   - 모델 이름이 틀림    -> python gemini_call.py --models 로 확인")
        print("   - 인터넷 연결 / 방화벽")
        print("   - 무료 한도 초과")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
