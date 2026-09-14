/* 인사·총무 교육용 가상 데모 — 자동 검증
   사용법:  npm run verify                (기본 앱 파일)
            node verify.js 다른파일.html   (다른 파일 검사)
   기존 숫자가 그대로인지, 실행 오류가 없는지 확인합니다. */
const fs = require("fs");
const path = require("path");
const { JSDOM } = require("jsdom");

const FILE = process.argv[2] || "인사총무_교육용가상데모.html";
const BASE = {                       // 기준값 (PRD.md 4-2절 / 3-1절)
  "직원": 28, "휴가": 50, "자산": 35, "소모품": 12, "카드내역": 60, "이력": 20,
  "승인 대기 휴가": 10, "증빙 미제출": 5, "반납 지연 자산": 3,
  "연차 촉진 처리": 5, "이번 달 인사 이벤트": 3,
};

const errs = [];
const html = fs.readFileSync(path.resolve(FILE), "utf8");
const dom = new JSDOM(html, {
  runScripts: "dangerously",
  url: "https://verify.local/app.html",
  beforeParse(w) {
    w.scrollTo = () => {};
    w.confirm = () => true;
    w.alert = () => {};
    w.print = () => {};
    w.onerror = (e) => errs.push(String(e));
  },
});

setTimeout(() => {
  const W = dom.window, D = W.document;
  const qa = (s) => [...D.querySelectorAll(s)];
  let bad = 0;
  const check = (name, got, want) => {
    const ok = got === want;
    if (!ok) bad++;
    console.log(`  ${ok ? "OK  " : "다름"} ${name.padEnd(16)} ${String(got).padStart(4)}  (기준 ${want})`);
  };

  console.log(`\n검사 대상: ${FILE}\n`);
  console.log("실행 오류:", errs.length ? errs : "없음");
  if (errs.length) bad++;

  console.log("\n[데이터 건수]");
  check("직원", W.DB.emps.length, BASE["직원"]);
  check("휴가", W.DB.leaves.length, BASE["휴가"]);
  check("자산", W.DB.assets.length, BASE["자산"]);
  check("소모품", W.DB.supplies.length, BASE["소모품"]);
  check("카드내역", W.DB.spends.length, BASE["카드내역"]);
  check("이력", W.DB.logs.length, BASE["이력"]);

  console.log("\n[처리할 것]");
  qa("#pane-home .todo").forEach((b) => {
    const lab = b.querySelector(".lab").textContent.replace(/\s*\(.*\)/, "").trim();
    const n = parseInt(b.querySelector(".num").textContent, 10);
    if (BASE[lab] !== undefined) check(lab, n, BASE[lab]);
    else console.log(`  --   ${lab.padEnd(16)} ${String(n).padStart(4)}  (기준 없음)`);
  });

  console.log("\n[무결성]");
  const ghost = W.DB.leaves.filter((l) => !W.empById(l.emp)).length
    + W.DB.assets.filter((a) => a.holder && !W.empById(a.holder)).length
    + W.DB.spends.filter((s) => !W.empById(s.emp)).length;
  check("주인 없는 기록", ghost, 0);
  const minus = W.DB.emps.filter((e) => e.status !== "퇴사"
    && W.grantDays(e) - W.usedDays(e.id) < 0).length;
  check("연차 마이너스", minus, 0);
  const edu = /교육용 가상 자료/.test(D.body.textContent) ? 1 : 0;
  check("교육용 표기", edu, 1);

  console.log(bad === 0 ? "\n=> 전부 통과\n" : `\n=> ${bad}건 확인 필요\n`);
  process.exit(bad === 0 ? 0 : 1);
}, 800);
