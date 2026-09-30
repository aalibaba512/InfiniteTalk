'use strict';
/** Mobile-first views. Server-rendered, plain HTML forms, almost no JavaScript. */

const esc = (s) =>
  String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');

const LAYOUT = (title, body) => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f3d4a">
<title>${esc(title)}</title>
<style>${CSS}</style>
</head>
<body>
<header class="bar"><a href="/s/home" class="brand">TEFOS <span>Quiz</span></a><a class="pts" href="/s/me">My points</a></header>
<main>${body}</main>
<footer class="fine">
  <p>Need help? Ask the front office: <a href="tel:+9200511122334">051-11122334</a></p>
  <p class="muted">If a link does not work, the printed fallback inside the front cover of your notebook always works.</p>
</footer>
</body>
</html>`;

const CSS = `
*{box-sizing:border-box}
body{margin:0;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:#f6f7f8;color:#16232b}
a{color:#0b6b7d}
.bar{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;align-items:center;padding:.7rem 1rem;background:#0f3d4a;color:#fff}
.brand{color:#fff;font-weight:700;letter-spacing:.14em;font-size:.85rem;text-decoration:none}
.brand span{opacity:.55;font-weight:400}
.pts{color:#ffd98a;font-size:.85rem;text-decoration:none;font-weight:600}
main{max-width:640px;margin:0 auto;padding:1rem}
.card{background:#fff;border-radius:14px;padding:1rem 1.1rem;margin-bottom:.8rem;box-shadow:0 1px 3px rgba(16,40,50,.08)}
h1{font-size:1.5rem;margin:.2rem 0 .3rem}
h2{font-size:1.05rem;margin:0 0 .5rem}
.sub{color:#5c6b75;font-size:.9rem;margin:0 0 1rem}
input[type=text]{width:100%;padding:.85rem;font-size:1.15rem;letter-spacing:.28em;text-transform:uppercase;border:1.5px solid #c8d2d8;border-radius:10px;background:#fbfcfc}
input[type=text]:focus{outline:3px solid #7fd3e0;border-color:#0b6b7d}
button{width:100%;padding:.9rem;font-size:1rem;font-weight:700;border:0;border-radius:10px;background:#0b6b7d;color:#fff;margin-top:.8rem;cursor:pointer}
.subject{border-left:6px solid;padding-left:.8rem;margin-bottom:.9rem}
.subject b{display:block;font-size:1.2rem}
.chapter{display:flex;justify-content:space-between;align-items:center;gap:.6rem;padding:.75rem 0;border-top:1px solid #edf0f2}
.chapter:first-of-type{border-top:0}
.pill{font-size:.72rem;font-weight:700;padding:.25rem .55rem;border-radius:99px;background:#e7f3f5;color:#0b6b7d;white-space:nowrap}
.pill.done{background:#e3f6e9;color:#1a6b3c}
.opt{display:block;padding:.9rem 1rem;border:1.5px solid #dbe2e6;border-radius:10px;margin-bottom:.5rem;cursor:pointer;text-decoration:none;color:#16232b}
.opt:has(input:checked){border-color:#0b6b7d;background:#eff9fb}
.opt input{margin-right:.6rem}
.res{font-size:3rem;font-weight:800;line-height:1}
.res.good{color:#1a6b3c}.res.bad{color:#8a5a10}
.note{background:#fff8e6;border-left:4px solid #e8a33d;padding:.7rem .9rem;border-radius:8px;font-size:.9rem;margin-top:.8rem}
.ok{background:#eaf7ef;border-left:4px solid #3aa76d;padding:.7rem .9rem;border-radius:8px;font-size:.9rem;margin-top:.8rem}
.gold{border-left:4px solid #d9a441}
.up{background:#eaf7ef;border-left:4px solid #3aa76d;padding:.7rem .9rem;border-radius:8px;font-weight:700;color:#1a6b3c;margin-bottom:.8rem}
table{width:100%;border-collapse:collapse;font-size:.95rem}
td,th{padding:.5rem .3rem;border-bottom:1px solid #edf0f2;text-align:left}
th{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#5c6b75}
tr.me{background:#eff9fb;font-weight:700}
.big{font-size:2.4rem;font-weight:800;margin:.1rem 0;line-height:1}
.fine{max-width:640px;margin:0 auto;padding:1rem;color:#6b7a84;font-size:.8rem}
.muted{color:#8b98a1}
.tiny{font-size:.82rem;color:#5c6b75}
.cent{text-align:center}
.timer{position:sticky;top:3rem;z-index:4;background:#0f3d4a;color:#ffd98a;padding:.5rem 1rem;text-align:center;font-weight:700;font-size:.9rem}
.rankrow{display:flex;flex-wrap:wrap;gap:.4rem;margin:.6rem 0}
.rankpill{font-size:.75rem;font-weight:700;padding:.3rem .6rem;border-radius:99px;border:1.5px solid #dbe2e6;color:#9aa7b0;background:#fff}
.rankpill.got{border-color:#c8d2d8;color:#5c6b75}
.rankpill.here{border-color:#d9a441;background:#fdf6e6;color:#8a5a10}
`;

const home = (student, subjects) => `
  <h1>Assalam-o-alaikum, ${esc(student.first_name)}</h1>
  <p class="sub">Pick the chapter you have just finished. One attempt scores. You can always try again for fewer points.</p>
  ${subjects.map((s) => `
    <div class="card subject" style="border-color:${esc(s.colour)}">
      <b>${esc(s.name)}</b>
      <span class="tiny">${s.done_count} of ${s.chapters.length} chapters completed</span>
      ${s.chapters.map((c) => `
        <div class="chapter">
          <a href="/s/quiz/${c.quiz_id}" style="text-decoration:none;color:inherit;flex:1">
            <div>${esc(c.seq)}. ${esc(c.title)}</div>
            <div class="tiny">${c.kind === 'classroom' ? 'From our own class' : 'From the chapter'}</div>
          </a>
          <span class="pill ${c.state === 'done' ? 'done' : ''}">${esc(c.label)}</span>
        </div>`).join('')}
    </div>`).join('')}
  <p class="tiny">Nothing here yet? Your teacher has not published the quiz for that chapter. Check back after the next class.</p>
`;

const login = (error) => `
  <h1>Open your notebook</h1>
  <p class="sub">Type the 6-character code printed on the inside of your notebook cover. No name, no form, no signup.</p>
  <form method="post" action="/s/login">
    <input type="text" name="code" placeholder="A1B2C3" maxlength="6" autocapitalize="characters"
           autocomplete="off" autocorrect="off" spellcheck="false" required autofocus>
    ${error ? `<div class="note">${esc(error)}</div>` : ''}
    <button type="submit">Open my notebook</button>
  </form>
  <p class="tiny" style="margin-top:1rem">Lost your code? The code is also on your class list from your teacher. See the front office.</p>
  <p class="tiny">This works in your normal phone browser. Nothing to download.</p>
`;

const quizPage = ({ quiz, chapter, subject, questions, secondsLeft, isFirst }) => `
  <div class="timer" id="t">Time left: ${Math.ceil(secondsLeft / 60)} min</div>
  <h1>${esc(subject.name)}</h1>
  <p class="sub">Chapter ${chapter.seq} &middot; ${esc(chapter.title)} &middot; ${questions.length} questions</p>
  ${isFirst
    ? `<div class="ok">This is your first attempt. <b>10 points per correct answer</b>, and only a first attempt counts toward the leaderboard.</div>`
    : `<div class="note">You have already scored this chapter, so this attempt earns <b>3 points</b> per correct answer and does not move you up the leaderboard. Try anyway &mdash; there is no penalty for a wrong answer.</div>`}
  <form method="post" action="/s/quiz/${quiz.id}">
    <input type="hidden" name="started_at" value="${esc(quiz.startedAt)}">
    ${questions.map((q, i) => `
      <div class="card">
        <h2>${i + 1}. ${esc(q.prompt)}</h2>
        ${q.options.map((opt) => `
          <label class="opt"><input type="radio" name="q${q.id}" value="${opt.originalIndex}" required>
            <span>${esc(opt.text)}</span></label>`).join('')}
      </div>`).join('')}
    <button type="submit">Submit my answers</button>
    <p class="tiny">No penalty for a wrong answer. Submit once you are ready &mdash; your first submission is the one that counts.</p>
  </form>
  <script>
  (function(){
    var end = Date.now() + ${secondsLeft * 1000};
    var el = document.getElementById('t');
    setInterval(function(){
      var s = Math.max(0, Math.round((end - Date.now())/1000));
      el.textContent = 'Time left: ' + Math.floor(s/60) + ':' + String(s%60).padStart(2,'0');
      if (s === 0) { el.textContent = 'Time is up - submit what you have.'; }
    }, 1000);
  })();
  </script>
`;

const resultPage = ({ chapter, subject, res, balance, retryUrl, rank }) => {
  const pct = res.total ? Math.round((res.correct / res.total) * 100) : 0;
  return `
  <p class="sub" style="margin-bottom:.2rem">${esc(subject.name)} &middot; Chapter ${chapter.seq}</p>
  <h1>${esc(chapter.title)}</h1>
  <div class="card cent">
    <div class="res ${pct >= 70 ? 'good' : 'bad'}">${res.correct}/${res.total}</div>
    <p>You scored <b>${pct}%</b></p>
    <p><b style="font-size:1.7rem;color:${pct >= 70 ? '#1a6b3c' : '#16232b'}">+${res.points} points</b></p>
    <p class="tiny">${res.isFirst ? 'First attempt &mdash; this counts toward the leaderboard.' : 'Retry &mdash; points added, leaderboard unchanged.'}</p>
    ${pct === 100 ? `<p class="ok" style="text-align:left">Perfect score. That earns the +25 chapter bonus.</p>` : ''}
  </div>
  <div class="card">
    <h2>Answers</h2>
    <table>${res.details.map((d) => `<tr><td>${d.correct ? '&#10003;' : '&#10007;'}</td>
      <td>${d.correct ? '' : '<span class="tiny">Correct answer: ' + esc(d.answer) + '</span>'}
      ${d.explanation ? `<div class="tiny muted">${esc(d.explanation)}</div>` : ''}</td></tr>`).join('')}</table>
  </div>
  <div class="card cent">
    <p class="tiny" style="margin:0">My total points</p>
    <p class="big">${balance}</p>
    <p class="tiny">Merit bursaries are awarded monthly from points like these.</p>
  </div>
  <div class="card">
    <h2>Rank earned this month</h2>
    <div class="rankrow">${rank.earned.map((r) =>
      `<span class="rankpill ${r.key === rank.current ? 'here' : 'got'}">${esc(r.icon)} ${esc(r.name)}</span>`).join('')}</div>
    ${rank.growth > 0 ? `<p class="up">&#9650; You are ${rank.growth} points ahead of where you were last month.</p>` : ''}
    ${rank.gap !== null ? `<p class="tiny" style="margin:0">${rank.gap} more points puts you on the top 10 board.</p>` : ''}
  </div>
  ${res.isFirst && res.correct < res.total
    ? `<a class="opt" href="${esc(retryUrl)}"><b>Try again</b><br><span class="tiny">Worth 3 points per correct answer. No penalty for getting it wrong.</span></a>` : ''}
  <a class="opt" href="/board"><b>See the leaderboard</b></a>
  <a class="opt" href="/s/home"><b>Back to my chapters</b></a>`;
};

const mePage = ({ student, balance, board, recent, ranks, rank }) => `
  <h1>${esc(student.first_name)}</h1>
  <p class="sub">${esc(student.class_name)} &middot; ${esc(student.campus_name)} &middot; ${esc(student.house || 'No house')}</p>
  <div class="card cent">
    <p class="tiny" style="margin:0">Points available as tuition credit</p>
    <p class="big" style="font-size:3rem">${balance}</p>
    <p class="tiny">${board} of these count toward the leaderboard</p>
  </div>
  <div class="card">
    <h2>Where you stand</h2>
    <div class="rankrow">${rank.earned.map((r) =>
      `<span class="rankpill ${r.key === rank.current ? 'here' : 'got'}">${esc(r.icon)} ${esc(r.name)}</span>`).join('')}</div>
    <p>${esc(ranks.line)}</p>
    ${ranks.growth > 0 ? `<p class="up">&#9650; ${ranks.growth} points ahead of last month</p>` : ''}
  </div>
  <div class="card">
    <h2>Recent activity</h2>
    ${recent.length
      ? `<table>${recent.map((r) => `<tr><td>${r.correct_count}/${r.total}</td>
          <td>${esc(r.subject)} &middot; ${esc(r.chapter)}</td>
          <td style="text-align:right;font-weight:700;color:${r.points > 0 ? '#1a6b3c' : '#8b98a1'}">+${r.points}</td></tr>`).join('')}</table>`
      : '<p class="tiny">No attempts yet. Open a chapter from your notebook.</p>'}
  </div>
  <div class="card">
    <h2>How points work</h2>
    <p class="tiny">+10 for a correct answer on your first attempt. +3 on a retry. +25 for a perfect chapter. <b>Nothing is ever taken away for a wrong answer</b>, so trying always beats not trying.</p>
  </div>
  <p class="tiny">Your full name and your parent are never shown on any public board. Display name: ${esc(student.display_name || student.first_name)}</p>
`;

const boardPage = ({ rows, studentId, subline, growth, gap, meRow }) => `
  <h1>Leaderboard</h1>
  <p class="sub">${esc(subline)} &middot; this month &middot; first names only, by school policy</p>
  <div class="card">
    <table>
      <tr><th>#</th><th>Name</th><th style="text-align:right">Points</th></tr>
      ${rows.map((r) => `<tr class="${r.id === studentId ? 'me' : ''}">
        <td>${r.rnk}</td>
        <td>${esc(r.display_name)}${r.school ? `<div class="tiny muted">${esc(r.school)}</div>` : ''}</td>
        <td style="text-align:right;font-weight:700">${r.board_points}</td></tr>`).join('')}
    </table>
  </div>
  ${meRow ? `<div class="card"><b>${meRow}</b></div>` : ''}
  ${growth > 0 ? `<p class="up">&#9650; You gained ${growth} points this month</p>` : ''}
  ${gap !== null ? `<div class="card gold"><b>${gap} more points puts you on the top 10 board</b></div>` : ''}
  <p class="tiny">Only a first attempt counts here, so nobody can climb by resubmitting. No points are ever taken away for a wrong answer.</p>
`;

const landing = () => `
  <h1>Your notebook is a doorway</h1>
  <p class="sub">Scan the QR on the cover of any subject notebook, or open the code printed inside it.</p>
  <div class="card">
    <ol>
      <li>Finish a chapter.</li>
      <li>Open this page on your phone.</li>
      <li>Type your 6-character code.</li>
      <li>Answer the chapter quiz. Earn points toward your merit bursary.</li>
    </ol>
  </div>
  <a class="opt" href="/s"><b>Open my notebook</b></a>
  <p class="tiny">This page is a demonstration build. The production version opens straight from the QR code on your notebook.</p>
`;

const errorPage = (msg) => `
  <h1>Something went wrong</h1>
  <p class="sub">${esc(msg)}</p>
  <p class="tiny">Please tell your teacher, and try again. The front office number is printed inside the front cover of your notebook.</p>
  <a class="opt" href="/s/home"><b>Back to my chapters</b></a>
`;

module.exports = { home, login, quizPage, resultPage, mePage, boardPage, landing, errorPage, LAYOUT };
