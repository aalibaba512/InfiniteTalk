'use strict';
/**
 * End-to-end tests of the rules that matter. Server must be running.
 * Run: node test/e2e.js
 */
const http = require('node:http');
const { db } = require('../src/db');
const points = require('../src/points');

const BASE = `http://127.0.0.1:${process.env.PORT || 3000}`;
let pass = 0;
let fail = 0;

function check(name, cond, extra = '') {
  if (cond) { pass += 1; console.log(`  PASS  ${name}`); }
  else { fail += 1; console.log(`  FAIL  ${name} ${extra}`); }
}

function request(path, { method = 'GET', body, cookie } = {}) {
  return new Promise((resolve, reject) => {
    const data = body ? new URLSearchParams(body).toString() : null;
    const req = http.request(`${BASE}${path}`, {
      method,
      headers: {
        ...(data ? { 'content-type': 'application/x-www-form-urlencoded', 'content-length': Buffer.byteLength(data) } : {}),
        ...(cookie ? { cookie } : {}),
      },
    }, (res) => {
      let html = '';
      res.on('data', (c) => { html += c; });
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, html }));
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

function freshStudent(name) {
  const s = db.prepare('SELECT * FROM students WHERE first_name = ?').get(name);
  const c = db.prepare('SELECT code FROM access_codes WHERE student_id = ?').get(s.id);
  for (const a of db.prepare('SELECT id FROM attempts WHERE student_id = ?').all(s.id)) {
    db.prepare('DELETE FROM answers WHERE attempt_id = ?').run(a.id);
  }
  db.prepare('DELETE FROM attempts WHERE student_id = ?').run(s.id);
  db.prepare('DELETE FROM points_ledger WHERE student_id = ?').run(s.id);
  return { id: s.id, code: c.code };
}

async function loginAs(name) {
  const stu = freshStudent(name);
  const r = await request('/s/login', { method: 'POST', body: { code: stu.code } });
  return { ...stu, cookie: ((r.headers['set-cookie'] || [])[0] || '').split(';')[0] };
}

/** Answer every question in a quiz, either allCorrect or allWrong. */
async function take(stu, quizId, strategy) {
  const page = await request(`/s/quiz/${quizId}`, { cookie: stu.cookie });
  const startedAt = (page.html.match(/name="started_at" value="([^"]+)"/) || [])[1];
  const qs = db.prepare('SELECT id, answer_index, options FROM questions WHERE quiz_id = ? ORDER BY pos').all(quizId);
  const body = {};
  for (const q of qs) {
    const len = JSON.parse(q.options).length;
    body[`q${q.id}`] = String(strategy === 'allCorrect' ? q.answer_index : (q.answer_index + 1) % len);
  }
  const res = await request(`/s/quiz/${quizId}`, { method: 'POST', body: { ...body, started_at: startedAt }, cookie: stu.cookie });
  return { res, count: qs.length };
}

(async () => {
  const firstQuiz = db.prepare('SELECT id FROM quizzes ORDER BY id LIMIT 1').get();
  if (!firstQuiz) {
    console.log('\n  The database is empty. Run:  node src/seed.js --force\n');
    process.exit(1);
  }
  const quizId = firstQuiz.id;
  const allQuizIds = db.prepare('SELECT id FROM quizzes').all().map((r) => r.id);

  console.log('\n--- login ---');
  const stu = await loginAs('Zoya');
  check('login sets a session', stu.cookie.startsWith('tefos='));
  check('home page lists chapters', /Motion in One Dimension/.test((await request('/s/home', { cookie: stu.cookie })).html));

  console.log('\n--- the answer key must never reach the device ---');
  const qpage = await request(`/s/quiz/${quizId}`, { cookie: stu.cookie });
  const key = db.prepare('SELECT id, answer_index, prompt FROM questions WHERE quiz_id = ? ORDER BY pos LIMIT 1').get(quizId);
  check('no answer_index field in the HTML', !qpage.html.includes('answer_index'));
  check('no correctness marker in the HTML', !/is_correct|isCorrect|data-correct/.test(qpage.html));
  check('explanations are not sent before submission', !qpage.html.includes('Stair race with stopwatches'));

  const posOfCorrect = (html) => {
    const start = html.indexOf(key.prompt.replace(/'/g, '&#39;'));
    if (start === -1) return -1;
    const seg = html.slice(start, start + 900).split('</div>')[0];
    return [...seg.matchAll(/value="(\d+)"/g)].map((m) => Number(m[1])).indexOf(key.answer_index);
  };
  const positions = new Set();
  for (let i = 0; i < 12; i += 1) {
    positions.add(posOfCorrect((await request(`/s/quiz/${quizId}`, { cookie: stu.cookie })).html));
  }
  check('the correct option is re-shuffled on every load', positions.size > 1, `positions: ${[...positions]}`);

  console.log('\n--- first attempt: 10 a point, plus the perfect bonus ---');
  const { res: r1, count: n } = await take(stu, quizId, 'allCorrect');
  const perfect = n * 10 + 25;
  check('result page renders', r1.status === 200);
  check(`perfect score shows ${n}/${n}`, r1.html.includes(`${n}/${n}`));
  check(`pays +${perfect}`, r1.html.includes(`+${perfect} points`));
  check('ledger total is ' + perfect,
    Number(db.prepare('SELECT SUM(delta) t FROM points_ledger WHERE student_id = ?').get(stu.id).t) === perfect);
  check('points_possible recorded for the rank tier',
    Number(db.prepare('SELECT possible FROM attempts WHERE student_id = ? AND is_first = 1').get(stu.id).possible) === perfect);

  console.log('\n--- a retry pays less and cannot climb the board ---');
  const { res: r2 } = await take(stu, quizId, 'allCorrect');
  const retry = n * 3;
  check(`retry pays +${retry}, not +${perfect}`, r2.html.includes(`+${retry} points`));
  check('retry does not repeat the perfect bonus', !r2.html.includes(`+${retry + 25} points`));
  check('leaderboard points unchanged',
    Number(db.prepare('SELECT SUM(delta) t FROM points_ledger WHERE student_id = ? AND board = 1').get(stu.id).t) === perfect);
  check('exactly one first attempt exists',
    Number(db.prepare('SELECT COUNT(*) n FROM attempts WHERE student_id = ? AND is_first = 1').get(stu.id).n) === 1);

  console.log('\n--- trying can never be worse than not trying ---');
  const weak = await loginAs('Omar');
  const bad = await take(weak, quizId, 'allWrong');
  check('all-wrong attempt scores 0, never negative',
    Number(db.prepare('SELECT COALESCE(SUM(delta),0) t FROM points_ledger WHERE student_id = ?').get(weak.id).t) === 0);
  check(`all-wrong page shows 0/${bad.count}`, bad.res.html.includes(`0/${bad.count}`));
  check('all-wrong page still offers a retry', bad.res.html.includes('Try again'));

  console.log('\n--- the activity floor blocks the one-quiz exploit ---');
  const cheat = await loginAs('Bilal');
  await take(cheat, quizId, 'allCorrect');
  let st = points.standing(db, cheat.id);
  check('one perfect quiz does NOT make an eligible rank', st.eligible === false, `quizzes=${st.quizzes}`);
  check('but the student still has an identity', st.current === 'spark', st.current);
  for (const qid of allQuizIds.filter((x) => x !== quizId)) await take(cheat, qid, 'allCorrect');
  st = points.standing(db, cheat.id);
  check(`after ${st.quizzes} chapters the rank is eligible`, st.eligible === true);
  check('a perfect record reaches the top tier', st.name === 'Galaxy', st.name);
  check('a perfect record has a 100% rate', Math.round(st.rate * 100) === 100, `rate=${st.rate}`);

  console.log('\n--- the gap nudge is only shown when it is reachable ---');
  check('a far-off student gets NO gap', points.gapToBoard(db, weak.id) === null, `got ${points.gapToBoard(db, weak.id)}`);
  const board = await request('/board', { cookie: cheat.cookie });
  check('leaderboard renders', board.status === 200);
  check('leaderboard hides guardian names', !/Mr\.|Mrs\./.test(board.html));
  check('leaderboard hides student surnames', !/Khan|Malik|Chaudhry|Sheikh|Qureshi/.test(board.html));

  console.log('\n--- QR tracking ---');
  const before = Number(db.prepare('SELECT COUNT(*) n FROM scans').get().n);
  const t = await request('/t/phy-2026-01/PHY');
  check('QR link redirects to the code entry', t.status === 302 && t.headers.location === '/s');
  check('scan recorded against the print batch',
    Number(db.prepare('SELECT COUNT(*) n FROM scans').get().n) === before + 1);

  console.log('\n--- security ---');
  check('unauthenticated /s/home redirects', (await request('/s/home', {})).status === 302);
  check('forged cookie rejected', (await request('/s/home', { cookie: 'tefos=eyJzaWQiOjF9.x' })).status === 302);
  const me = await request('/s/me', { cookie: stu.cookie });
  check('my-points page renders', me.status === 200);
  check('my-points shows the total balance', me.html.includes(String(perfect + retry)));

  console.log(`\n${pass} passed, ${fail} failed\n`);
  process.exit(fail === 0 ? 0 : 1);
})().catch((e) => { console.error(e); process.exit(1); });
