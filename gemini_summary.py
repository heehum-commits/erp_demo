# -*- coding: utf-8 -*-
"""
인사·총무 앱 데이터를 읽어 Gemini 에게 요약을 맡기는 프로그램

사용법
    python gemini_summary.py            # 전체 브리핑
    python gemini_summary.py 휴가       # 휴가만
    python gemini_summary.py 자산
    python gemini_summary.py 카드
    python gemini_summary.py 급여

코딩을 모르면
    같은 폴더의  요약보기.bat  을 더블클릭하세요.

이 프로그램이 하는 일
    1) index.html 안의 가상 데이터를 읽는다
    2) 숫자는 파이썬이 직접 센다  <- Gemini 가 계산하지 않으므로 숫자가 틀리지 않는다
    3) 그 숫자만 주고 Gemini 에게 "보고서처럼 다듬어 달라"고 맡긴다
    4) 화면에 보여주고 요약결과/ 폴더에 파일로도 남긴다

주의
    모든 자료는 교육용 가상 데이터입니다. 실제 인사 자료가 아닙니다.
    API 키는 .env 에만 있고 앱 파일(index.html)에는 들어가지 않습니다.
"""

import json
import logging
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

logging.getLogger("google_genai").setLevel(logging.ERROR)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
APP_FILE = HERE / "index.html"
OUT_DIR = HERE / "요약결과"
TODAY = date(2026, 9, 14)          # 앱의 기준일과 맞춘다

DEFAULT_MODEL = "gemini-flash-latest"
FALLBACK_MODELS = ["gemini-3.6-flash", "gemini-2.5-pro"]
RETRY_COUNT = 2
RETRY_WAIT = 2


# ────────────────────────────────── 1. 앱 데이터 읽기

def extract_array(html, name):
    """index.html 안의 var NAME=[ ... ]; 를 찾아 파이썬 목록으로 바꾼다."""
    match = re.search(r"var\s+" + name + r"\s*=\s*\[", html)
    if not match:
        raise ValueError(f"{name} 을(를) 찾지 못했습니다.")
    start = match.end() - 1
    depth = 0
    end = None
    for i in range(start, len(html)):
        if html[i] == "[":
            depth += 1
        elif html[i] == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise ValueError(f"{name} 의 끝을 찾지 못했습니다.")
    body = re.sub(r"/\*.*?\*/", "", html[start:end], flags=re.S)
    return json.loads(body)


def load_app_data():
    if not APP_FILE.exists():
        raise FileNotFoundError(f"{APP_FILE.name} 을 찾지 못했습니다.")
    html = APP_FILE.read_text(encoding="utf-8")
    emp_rows = extract_array(html, "RAW_EMP")
    return {
        "emps": [
            {"id": r[0], "name": r[1], "dept": r[2], "rank": r[3],
             "etype": r[4], "hire": r[5], "status": r[6], "out": r[7]}
            for r in emp_rows
        ],
        "leaves": [
            {"id": r[0], "emp": r[1], "type": r[2], "s": r[3], "e": r[4],
             "days": r[5], "reason": r[6], "status": r[7]}
            for r in extract_array(html, "RAW_LEAVE")
        ],
        "assets": [
            {"id": r[0], "cat": r[1], "item": r[2], "model": r[3], "acq": r[4],
             "cost": r[5], "status": r[6], "holder": r[7], "out": r[8], "due": r[9]}
            for r in extract_array(html, "RAW_ASSET")
        ],
        "supplies": [
            {"name": r[0], "unit": r[1], "stock": r[2], "safe": r[3]}
            for r in extract_array(html, "RAW_SUPPLY")
        ],
        "spends": [
            {"id": r[0], "date": r[1], "card": r[2], "emp": r[3], "merchant": r[4],
             "acct": r[5], "amount": r[6], "proof": r[7]}
            for r in extract_array(html, "RAW_SPEND")
        ],
    }


def to_date(text):
    return datetime.strptime(text, "%Y-%m-%d").date() if text else None


def name_of(data, emp_id):
    for e in data["emps"]:
        if e["id"] == emp_id:
            return e["name"], e["dept"]
    return "(알 수 없음)", "-"


# ────────────────────────────────── 2. 숫자 세기 (파이썬이 직접)

def facts_leave(data):
    waiting = [l for l in data["leaves"] if l["status"] == "대기"]
    lines = [f"승인 대기 휴가 {len(waiting)}건"]
    for l in sorted(waiting, key=lambda x: x["s"]):
        nm, dept = name_of(data, l["emp"])
        period = l["s"] if l["s"] == l["e"] else f'{l["s"]}~{l["e"]}'
        lines.append(f"  - {nm}({dept}) {l['type']} {period} {l['days']}일 / 사유 {l['reason']}")

    # 날짜별 부재 인원 (승인 + 대기, 반려 제외) — 많은 날 상위 5일
    counter = {}
    for l in data["leaves"]:
        if l["status"] == "반려":
            continue
        s, e = to_date(l["s"]), to_date(l["e"])
        day = s
        while day <= e:
            counter[day] = counter.get(day, 0) + 1
            day += timedelta(days=1)
    top = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    working = sum(1 for e in data["emps"] if e["status"] == "재직")
    lines.append(f"재직 인원 {working}명 기준, 사람이 가장 많이 빠지는 날")
    for day, n in top:
        lines.append(f"  - {day} {n}명 (재직 대비 {round(n / working * 100)}%)")
    return "\n".join(lines)


def facts_asset(data):
    late = [a for a in data["assets"]
            if a["status"] == "불출중" and a["due"] and to_date(a["due"]) < TODAY]
    short = [p for p in data["supplies"] if p["stock"] < p["safe"]]
    lines = [f"반납 지연 자산 {len(late)}점"]
    for a in late:
        nm, dept = name_of(data, a["holder"])
        overdue = (TODAY - to_date(a["due"])).days
        lines.append(f"  - {a['id']} {a['item']} / {nm}({dept}) / 반납예정 {a['due']} ({overdue}일 지남)")
    lines.append(f"안전재고보다 적은 소모품 {len(short)}품목")
    for p in short:
        lines.append(f"  - {p['name']} {p['stock']}{p['unit']} (안전재고 {p['safe']})")
    return "\n".join(lines)


def facts_card(data):
    overdue = [s for s in data["spends"]
               if s["proof"] == "미제출" and (TODAY - to_date(s["date"])).days >= 14]
    unsub = [s for s in data["spends"] if s["proof"] == "미제출"]
    month = TODAY.strftime("%Y-%m")
    this_month = [s for s in data["spends"] if s["date"][:7] == month]
    lines = [
        f"증빙 미제출 {len(unsub)}건, 그중 14일 지난 건 {len(overdue)}건",
        f"이번 달({month}) 카드 사용 {len(this_month)}건 / {sum(s['amount'] for s in this_month):,}원",
    ]
    for s in sorted(overdue, key=lambda x: x["date"]):
        nm, dept = name_of(data, s["emp"])
        days = (TODAY - to_date(s["date"])).days
        lines.append(f"  - {s['date']} {nm}({dept}) {s['merchant']} {s['amount']:,}원 "
                     f"/ {s['acct']} / {days}일 경과")
    return "\n".join(lines)


PAY_BASE = {"이사": 6000000, "부장": 5000000, "차장": 4500000, "과장": 4000000,
            "대리": 3300000, "주임": 2900000, "사원": 2500000}
PAY_DUTY = {"이사": 500000, "부장": 300000, "차장": 200000, "과장": 150000}


def facts_pay(data):
    """앱과 같은 기준으로 이번 달 인건비 대략치를 센다 (기본급+식대+직책수당)."""
    rows = []
    for e in data["emps"]:
        if e["status"] != "재직":
            continue
        base = PAY_BASE.get(e["rank"], 0)
        rows.append((e["dept"], base + 200000 + PAY_DUTY.get(e["rank"], 0)))
    by_dept = {}
    for dept, amount in rows:
        by_dept[dept] = by_dept.get(dept, 0) + amount
    lines = [f"재직 {len(rows)}명 기준 월 고정 인건비(기본급+식대+직책수당) 합계 "
             f"{sum(a for _, a in rows):,}원"]
    for dept, amount in sorted(by_dept.items(), key=lambda kv: -kv[1]):
        lines.append(f"  - {dept} {amount:,}원")
    lines.append("※ 연장근로수당·상여는 달마다 달라 여기에는 넣지 않았습니다.")
    return "\n".join(lines)


TOPICS = {
    "휴가": ("휴가 · 근태", facts_leave),
    "자산": ("비품 · 자산", facts_asset),
    "카드": ("법인카드 · 경비", facts_card),
    "급여": ("급여 · 인건비", facts_pay),
}


def facts_all(data):
    return "\n\n".join(f"[{title}]\n{fn(data)}" for title, fn in TOPICS.values())


# ────────────────────────────────── 3. Gemini 에게 다듬어 달라고 맡기기

def find_api_key():
    path = HERE / ".env"
    if not path.exists():
        return None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip().lower() in ("gemini_api_key", "google_api_key"):
            return value.strip().strip('"').strip("'")
    return None


PROMPT_TEMPLATE = """당신은 중소 물류회사의 인사·총무 담당자를 돕는 조수입니다.

아래는 오늘({today}) 기준으로 시스템이 직접 센 사실입니다.

{facts}

이 사실만 사용해서 담당자에게 보고하듯 정리해 주세요.

규칙
- 위에 없는 숫자나 사람 이름을 새로 만들지 마세요.
- 계산을 다시 하지 마세요. 숫자는 그대로 인용하세요.
- 5줄 이내로, 각 줄은 '무엇이 문제인지 + 무엇을 하면 되는지' 형태로 쓰세요.
- 가장 급한 것부터 쓰세요.
- 존댓말로, 전문용어는 쉽게 풀어서 쓰세요.
"""


def call_gemini(api_key, prompt):
    import time
    from google import genai
    client = genai.Client(api_key=api_key)
    for model in [DEFAULT_MODEL] + FALLBACK_MODELS:
        for attempt in range(RETRY_COUNT + 1):
            try:
                response = client.models.generate_content(model=model, contents=prompt)
                return model, (response.text or "").strip()
            except Exception as error:
                busy = "503" in str(error) or "UNAVAILABLE" in str(error)
                if not busy:
                    raise
                if attempt < RETRY_COUNT:
                    print(f"[재시도] '{model}' 가 붐빕니다. {RETRY_WAIT}초 뒤 다시 시도")
                    time.sleep(RETRY_WAIT)
                else:
                    print(f"[전환] '{model}' 가 계속 붐빕니다. 다른 모델로 시도합니다.")
    raise RuntimeError("모든 모델이 응답하지 않았습니다.")


# ────────────────────────────────── 4. 실행

MENU = [
    ("1", "전체", "전체 브리핑   (오늘 처리할 것 모두)"),
    ("2", "휴가", "휴가 · 근태"),
    ("3", "자산", "비품 · 자산"),
    ("4", "카드", "법인카드 · 경비"),
    ("5", "급여", "급여 · 인건비"),
]


def choose_topic():
    """번호를 골라 주제를 정한다. (더블클릭으로 실행했을 때)"""
    print()
    print("  " + "=" * 56)
    print("   인사·총무 요약   -   교육용 가상 자료")
    print("  " + "=" * 56)
    print()
    for number, _, label in MENU:
        print(f"    {number}. {label}")
    print("    0. 끝내기")
    print()
    try:
        answer = input("  번호를 누르고 엔터 (그냥 엔터 = 1) : ").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if answer == "0":
        return None
    if answer == "":
        answer = "1"
    for number, topic, _ in MENU:
        if answer == number:
            return topic
    print()
    print(f"  '{answer}' 는 없는 번호입니다. 1~5 중에서 골라주세요.")
    return choose_topic()


def main():
    args = sys.argv[1:]
    if args and args[0] == "--menu":
        topic = choose_topic()
        if topic is None:
            print()
            print("  끝냅니다.")
            return 0
    else:
        topic = (args[0] if args else "전체").strip()

    print("=" * 64)
    print("  인사·총무 요약  (교육용 가상 자료 — 실제 인사 자료가 아닙니다)")
    print("=" * 64)

    try:
        data = load_app_data()
    except Exception as error:
        print("오류: 앱 데이터를 읽지 못했습니다.")
        print("  ", error)
        return 1

    if topic in TOPICS:
        title, fn = TOPICS[topic]
        facts = fn(data)
    elif topic in ("전체", "all"):
        title, facts = "전체 브리핑", facts_all(data)
    else:
        print(f"'{topic}' 는 모르는 항목입니다.")
        print("  쓸 수 있는 값:", " / ".join(TOPICS), "/ 전체")
        return 1

    print(f"\n[{title}] 시스템이 센 사실\n")
    print(facts)
    print("\n" + "-" * 64)

    api_key = find_api_key()
    if not api_key:
        print("\nAPI 키가 없어 위 사실만 보여드렸습니다.")
        print(".env 파일에  gemini_api_key=발급받은키  를 넣으면 요약까지 해 드립니다.")
        return 0

    print("\nGemini 에게 정리를 맡기는 중...\n")
    try:
        model, text = call_gemini(api_key, PROMPT_TEMPLATE.format(today=TODAY, facts=facts))
    except Exception as error:
        print("오류: Gemini 호출에 실패했습니다.")
        print("  ", type(error).__name__, "-", error)
        print("\n위에 나온 '시스템이 센 사실' 은 그대로 쓰실 수 있습니다.")
        return 1

    print(f"[{title}] 요약   (모델: {model})\n")
    print(text)

    OUT_DIR.mkdir(exist_ok=True)
    out_file = OUT_DIR / f"{TODAY}_{topic}.txt"
    out_file.write_text(
        f"[교육용 가상 자료] {title} — 기준일 {TODAY}\n\n"
        f"■ 시스템이 센 사실\n{facts}\n\n"
        f"■ 요약 (Gemini {model})\n{text}\n",
        encoding="utf-8",
    )
    print(f"\n저장됨: 요약결과\\{out_file.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
