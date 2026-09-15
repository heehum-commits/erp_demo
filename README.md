# 인사·총무 업무 앱 (교육용 가상 데모)

> ⚠️ **교육용 가상 자료입니다.** 회사·직원·급여·카드내역·자산번호는 전부 교육 목적으로 지어낸
> 가상 사례이며, 실재하는 인물·기업·거래와 무관합니다.

설치·서버 없이 **`index.html` 하나만 열면 동작하는 단일 파일 앱**입니다.
홈 + 5개 탭(인사기록 / 근태·휴가 / 급여 / 비품·자산 / 법인카드)으로 이루어져 있고,
입력한 내용은 그 브라우저에 저장됩니다.

## 쓰는 방법 3가지

| 방법 | 하는 법 | AI 기능 |
|---|---|---|
| **내 컴퓨터에서** | `index.html` 더블클릭 | ✅ (본인 키 입력) |
| **인터넷 주소로 공유** | Vercel 배포 (아래 참고) | ✅ (보는 사람이 자기 키 입력) |
| **claude.ai 링크로 공유** | `python build_artifact.py` → `dist/artifact.html` 업로드 | ❌ (보안 정책상 차단) |

## Vercel 배포

이 저장소는 **그대로 가져다 배포하면 됩니다.** 빌드가 필요 없습니다.

1. [vercel.com](https://vercel.com) 로그인 → **Add New… → Project**
2. 이 GitHub 저장소(`erp_demo`) 선택 → **Import**
3. 설정은 **손대지 않고** 그대로 **Deploy**
   - Framework Preset: `Other`, Build Command: 비움, Output Directory: `.`
   - 이 값은 `vercel.json`에 이미 들어 있어 자동으로 잡힙니다.
4. 몇 초 뒤 나오는 주소(`https://….vercel.app`)를 열면 앱이 뜹니다.

이후 `index.html`을 고쳐서 `git push` 하면 **자동으로 다시 배포**됩니다.

### 배포 전 알아둘 것

- 배포 주소는 **링크를 아는 사람 누구나 볼 수 있습니다.** 검색엔진에는 잡히지 않도록
  `robots.txt`와 `noindex` 태그를 넣어 두었지만, 링크 자체는 공개입니다.
- **API 키는 배포물에 들어가지 않습니다.** AI 기능을 쓰려면 보는 사람이 자기 키를
  한 번 입력하고, 그 키는 그 사람 브라우저에만 저장됩니다.

## 개발자용 명령

```bash
npm install        # 최초 1회 (검증 도구 jsdom)
npm run verify     # index.html 숫자·오류 자동 검사 — 수정했으면 반드시 실행
npm run serve      # http://127.0.0.1:8765 로 띄워 보기
python build_artifact.py   # claude.ai 링크 배포용 dist/artifact.html 생성
python gemini_test.py      # .env 의 API 키로 Gemini 연동이 되는지 5단계 점검
```

## AI(Gemini) 연동 확인하는 법

| 확인 위치 | 방법 | 쓰는 키 |
|---|---|---|
| **내 컴퓨터(개발용)** | `연결테스트.bat` 더블클릭 (= `python gemini_test.py`) | `.env` 의 `gemini_api_key` |
| **앱 화면** | 홈 > AI 브리핑 > **키 설정** > **연결 테스트** | 화면에서 넣은 키 (그 브라우저에만 저장) |

`.env` 의 키는 **파이썬 도구 전용**입니다. 앱(`index.html`)에는 키가 들어가지 않으므로,
앱에서 AI를 쓸 때는 화면에서 키를 한 번 넣어야 합니다.

## 문서

| 문서 | 내용 |
|---|---|
| `PRD.md` | 기획서 — **다른 문서와 어긋나면 이 문서가 우선** |
| `DESIGN.md` | 색·글꼴·여백 등 디자인 규칙 |
| `데이터안내.md` | 가상 데이터를 어떻게 만들고 이었는지 |
| `확인예시.md` | 한 사람을 끝까지 따라가 보는 테스트 시나리오 |
| `CLAUDE.md` | Claude Code 작업 규칙 |
