# -*- coding: utf-8 -*-
"""
index.html 을 claude.ai 링크 배포용 파일로 바꾼다.

    python build_artifact.py    ->  dist/artifact.html 생성

왜 필요한가
    링크 배포판은 <!doctype>·<html>·<head>·<body> 껍데기를 서비스가 직접 씌운다.
    그래서 우리 파일에서는 그 껍데기를 벗기고 <title> + <style> + 내용만 남긴다.

주의
    dist/artifact.html 은 자동 생성물이다. 직접 고치지 말고 index.html 을 고친 뒤 다시 돌린다.
"""
import io
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
SRC = HERE / "index.html"
OUT_DIR = HERE / "dist"
OUT = OUT_DIR / "artifact.html"

# 링크 배포판 제목 — 갤러리와 브라우저 탭에 이름으로 뜬다 (설명은 배포 시 description 으로)
ARTIFACT_TITLE = "인사·총무 실습 데모"


def main():
    if not SRC.exists():
        print("오류: index.html 이 없습니다.")
        return 1
    html = SRC.read_text(encoding="utf-8")

    title = re.search(r"<title>(.*?)</title>", html, re.S)
    style = re.search(r"<style>(.*?)</style>", html, re.S)
    body = re.search(r"<body>(.*?)</body>", html, re.S)
    if not (title and style and body):
        print("오류: title / style / body 를 찾지 못했습니다.")
        return 1

    parts = [
        "<title>" + ARTIFACT_TITLE + "</title>",
        "<style>" + style.group(1) + "</style>",
        body.group(1).strip(),
    ]
    out = "\n".join(parts) + "\n"

    OUT_DIR.mkdir(exist_ok=True)
    OUT.write_text(out, encoding="utf-8")

    low = out.lower()
    for tag in ("<!doctype", "<html>", "<html ", "<head>", "<head ",
                "<body>", "<body ", "</html>", "</head>", "</body>"):
        if tag in low:
            print(f"경고: 결과물에 {tag} 가 남아 있습니다.")

    print(f"만들어짐: dist/{OUT.name}")
    print(f"  원본 {len(html):,} 바이트  ->  배포용 {len(out):,} 바이트")
    print(f"  제목: {ARTIFACT_TITLE}  (앱 파일 제목: {title.group(1).strip()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
