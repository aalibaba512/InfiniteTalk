'use strict';
/**
 * TEFOS Quiz - chapter quiz engine for the notebook QR programme.
 * Zero dependencies: node:http + node:sqlite, both built into Node 22+.
 */
const http = require('node:http');
const crypto = require('node:crypto');
const zlib = require('node:zlib');
const { URL } = require('node:url');
const { db } = require('./db');
const points = require('./points');
const views = require('./views');

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';
const SECRET = process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex');
const COOKIE = 'tefos';

const nowIso = () => new Date().toISOString();

function send(res, status, html, type = 'text/html; charset=utf-8') {
  const base = {
    'content-type': type,
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
    'referrer-policy': 'no-referrer',
  };
  // Students are often on metered mobile data, so compress everything.
  const enc = (res.req && res.req.headers['accept-encoding']) || '';
  if (/\bgzip\b/.test(enc) && html.length > 512) {
    const body = zlib.gzipSync(Buffer.from(html, 'utf8'));
    res.writeHead(status, { ...base, 'content-encoding': 'gzip', vary: 'accept-encoding' });
    return res.end(body);
  }
  res.writeHead(status, base);
  res.end(html);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let raw = '';
    let tooBig = false;
    req.on('data', (c) => {
      raw += c;
      if (raw.length > 100000) { tooBig = true; req.destroy(); }
    });
    req.on('end', () => { if (tooBig) return reject(new Error('body too large')); resolve(new URLSearchParams(raw)); });
    req.on('error', reject);
  });
}

function parseCookies(req) {
  const out = {};
  const header = req.headers.cookie;
  if (!header) return out;
  for (const part of header.split(';')) {
    const i = part.indexOf('=');
    if (i > 0) out[part.slice(0, i).trim()] = decodeURIComponent(part.slice(i + 1).trim());
  }
  return out;
}

function sign(payload) {
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `${body}.${crypto.createHmac('sha256', SECRET).update(body).digest('base64url')}`;
}

function verify(token) {
  if (typeof token !== 'string' || !token.includes('.')) return null;
  const parts = token.split('.');
  if (parts.length !== 2) return null;
  const [body, sig] = parts;
  const expected = crypto.createHmac('sha256', SECRET).update(body).digest('base64url');
  const a = Buffer.from(sig);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
  try { return JSON.parse(Buffer.from(body, 'base64url').toString()); } catch { return null; }
}

function currentStudent(req) {
  const session = verify(parseCookies(req)[COOKIE]);
  if (!session || !session.sid) return null;
  return db.prepare(
    `SELECT s.*, c.name AS class_name, c.year_group, cp.name AS campus_name, cp.code AS campus_code
     FROM students s
     LEFT JOIN classes c  ON c.id  = s.class_id
     LEFT JOIN campuses cp ON cp.id = s.campus_id
     WHERE s.id = ? AND s.active = 1`
  ).get(session.sid) || null;
}

function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i -= 1) {
    const j = crypto.randomInt(i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function loginAllowed(ip) {
  return Number(db.prepare(
    'SELECT COUNT(*) AS n FROM code_attempts WHERE ip = ? AND created_at > ?'
  ).get(ip, new Date(Date.now() - 15 * 60 * 1000).toISOString()).n) < 10;
}

const clientIp = (req) =>
  (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || req.socket.remoteAddress || '?';

/* ------------------------------------------------------------- data reads */

function studentChapters(student) {
  const rows = db.prepare(
    `SELECT ch.seq, ch.title, q.id AS quiz_id, q.kind, sj.name AS subject, sj.colour,
            MAX(CASE WHEN a.is_first = 1 THEN 1 ELSE 0 END) AS scored
     FROM chapters ch
     JOIN subjects sj     ON sj.id = ch.subject_id
     LEFT JOIN quizzes q  ON q.chapter_id = ch.id
     LEFT JOIN attempts a ON a.quiz_id = q.id AND a.student_id = ?
     GROUP BY ch.id
     ORDER BY sj.name, ch.seq`
  ).all(student.id);

  const bySubject = new Map();
  for (const r of rows) {
    if (!r.quiz_id) continue;
    if (!bySubject.has(r.subject)) bySubject.set(r.subject, { name: r.subject, colour: r.colour, chapters: [], done_count: 0 });
    bySubject.get(r.subject).chapters.push({
      seq: r.seq, title: r.title, quiz_id: r.quiz_id, kind: r.kind,
      state: r.scored ? 'done' : 'new', label: r.scored ? 'Scored' : 'New',
    });
    if (r.scored) bySubject.get(r.subject).done_count += 1;
  }
  return [...bySubject.values()].sort((a, b) => a.name.localeCompare(b.name));
}

const loadQuiz = (quizId) => db.prepare(
  `SELECT q.*, ch.title, ch.seq, sj.name AS subject
   FROM quizzes q
   JOIN chapters ch ON ch.id = q.chapter_id
   JOIN subjects sj ON sj.id = ch.subject_id
   WHERE q.id = ?`
).get(quizId);

function loadQuestions(quizId) {
  // The answer key is stripped before the questions ever reach the device.
  return db.prepare('SELECT * FROM questions WHERE quiz_id = ? ORDER BY pos, id').all(quizId)
    .map((r) => ({
      id: r.id, prompt: r.prompt, explanation: r.explanation,
      options: shuffle(JSON.parse(r.options).map((text, originalIndex) => ({ text, originalIndex }))),
    }));
}

function monthPoints(db2, studentId, offsetMonths = 0) {
  const modifier = offsetMonths === 0 ? 'start of month' : `start of month, -${offsetMonths} month`;
  return Number(db2.prepare(
    `SELECT COALESCE(SUM(delta), 0) AS pts FROM points_ledger
     WHERE student_id = ? AND board = 1 AND created_at >= date('now', ?)`
  ).get(studentId, modifier).pts);
}

/* ----------------------------------------------------------------- routes */

const routes = [];
const route = (method, pattern, handler) => routes.push({ method, pattern, handler });

route('GET', '/', (req, res) => send(res, 200, views.landing()));
route('GET', '/health', (req, res) => send(res, 200, JSON.stringify({ ok: true, time: nowIso() }), 'application/json'));
route('GET', '/s', (req, res) => send(res, 200, views.login()));

route('POST', '/s/login', async (req, res) => {
  const ip = clientIp(req);
  if (!loginAllowed(ip)) return send(res, 429, views.login('Too many tries. Please wait 15 minutes or see the front office.'));
  const form = await readBody(req);
  const code = (form.get('code') || '').trim().toUpperCase();
  const match = db.prepare('SELECT student_id FROM access_codes WHERE code = ?').get(code);
  if (!match) {
    db.prepare('INSERT INTO code_attempts (ip, created_at) VALUES (?, ?)').run(ip, nowIso());
    return send(res, 200, views.login('That code is not right. Check the inside cover of your notebook, and try again.'));
  }
  res.setHeader('set-cookie', `${COOKIE}=${sign({ sid: match.student_id })}; Path=/; HttpOnly; SameSite=Lax; Max-Age=18000`);
  res.writeHead(302, { location: '/s/home' });
  res.end();
});

route('GET', '/s/home', (req, res) => {
  const student = currentStudent(req);
  if (!student) { res.writeHead(302, { location: '/s' }); return res.end(); }
  return send(res, 200, views.home(student, studentChapters(student)));
});

route('GET', '/s/quiz/:id', (req, res, params) => {
  const student = currentStudent(req);
  if (!student) { res.writeHead(302, { location: '/s' }); return res.end(); }
  const quiz = loadQuiz(Number(params.id));
  if (!quiz) return send(res, 404, views.errorPage('That chapter quiz is not available.'));
  const questions = loadQuestions(quiz.id);
  if (!questions.length) return send(res, 404, views.errorPage('Your teacher has not published questions for this chapter yet.'));
  return send(res, 200, views.quizPage({
    quiz: { ...quiz, startedAt: sign({ at: Date.now() }) },
    chapter: { seq: quiz.seq, title: quiz.title },
    subject: { name: quiz.subject },
    questions,
    secondsLeft: quiz.time_limit_sec,
    isFirst: !points.hasFirstAttempt(db, student.id, quiz.id),
  }));
});

route('POST', '/s/quiz/:id', async (req, res, params) => {
  const student = currentStudent(req);
  if (!student) { res.writeHead(302, { location: '/s' }); return res.end(); }
  const quizId = Number(params.id);
  const quiz = loadQuiz(quizId);
  if (!quiz) return send(res, 404, views.errorPage('That chapter quiz is not available.'));

  const form = await readBody(req);
  const answers = new Map();
  for (const [key, value] of form.entries()) {
    const m = /^q(\d+)$/.exec(key);
    if (m) answers.set(m[1], Number(value));
  }
  // The start time is signed so a student cannot backdate it to dodge the timer.
  const started = verify(form.get('started_at'));
  const startedAt = started && started.at ? new Date(started.at).toISOString() : nowIso();

  const result = points.submitAttempt(db, { studentId: student.id, quizId, answers, startedAt });

  const full = db.prepare(
    'SELECT id, options, answer_index, explanation FROM questions WHERE quiz_id = ? ORDER BY pos, id'
  ).all(quizId);
  const details = full.map((q) => ({
    correct: answers.get(String(q.id)) === q.answer_index,
    answer: JSON.parse(q.options)[q.answer_index],
    explanation: q.explanation,
  }));

  const st = points.standing(db, student.id);
  const growth = Math.max(0, monthPoints(db, student.id, 0) - monthPoints(db, student.id, 1));

  return send(res, 200, views.resultPage({
    chapter: { seq: quiz.seq, title: quiz.title },
    subject: { name: quiz.subject },
    res: { ...result, details },
    balance: points.balance(db, student.id),
    retryUrl: `/s/quiz/${quizId}`,
    rank: { ...st, growth, gap: points.gapToBoard(db, student.id) },
  }));
});

route('GET', '/s/me', (req, res) => {
  const student = currentStudent(req);
  if (!student) { res.writeHead(302, { location: '/s' }); return res.end(); }
  const recent = db.prepare(
    `SELECT a.correct_count, a.total, a.points, sj.name AS subject, ch.title AS chapter
     FROM attempts a
     JOIN quizzes q   ON q.id = a.quiz_id
     JOIN chapters ch ON ch.id = q.chapter_id
     JOIN subjects sj ON sj.id = ch.subject_id
     WHERE a.student_id = ? ORDER BY a.id DESC LIMIT 10`
  ).all(student.id);

  const st = points.standing(db, student.id);
  const growth = Math.max(0, monthPoints(db, student.id, 0) - monthPoints(db, student.id, 1));
  const line = st.eligible
    ? `You are a ${st.name} - ${Math.round(st.rate * 100)}% of the points available across ${st.quizzes} chapters.`
    : `You have taken ${st.quizzes} of ${points.ACTIVITY_FLOOR} chapters needed before a rank is shown. Keep going.`;

  return send(res, 200, views.mePage({
    student,
    balance: points.balance(db, student.id),
    board: points.boardPoints(db, student.id),
    recent, rank: st,
    ranks: { line, growth },
  }));
});

route('GET', '/board', (req, res) => {
  const student = currentStudent(req);
  const rows = db.prepare(
    `SELECT s.id, COALESCE(s.display_name, s.first_name) AS display_name, cp.name AS school,
            SUM(l.delta) AS board_points
     FROM points_ledger l
     JOIN students s ON s.id = l.student_id
     LEFT JOIN campuses cp ON cp.id = s.campus_id
     WHERE l.board = 1 AND l.created_at >= date('now','start of month') AND s.active = 1
     GROUP BY s.id ORDER BY board_points DESC, s.first_name LIMIT 25`
  ).all().map((r, i) => ({ ...r, rnk: i + 1 }));

  const idx = student ? rows.findIndex((r) => r.id === student.id) : -1;
  const growth = student ? Math.max(0, monthPoints(db, student.id, 0) - monthPoints(db, student.id, 1)) : 0;

  return send(res, 200, views.boardPage({
    rows,
    studentId: student ? student.id : -1,
    subline: student ? `${student.class_name} \u00b7 all 16 schools` : 'all 16 schools',
    growth,
    gap: student ? points.gapToBoard(db, student.id) : null,
    meRow: idx >= 0 ? `You are #${idx + 1} of ${rows.length} this month` : null,
  }));
});

/**
 * QR tracking. Each printed batch gets its own short link so the school can see
 * which notebook print run actually drove participation:
 *   https://<host>/t/physics-main-2026/PHY
 */
route('GET', '/t/:batch/:subject', (req, res, params) => {
  db.prepare('INSERT INTO scans (created_at, batch, subject, user_agent) VALUES (?, ?, ?, ?)')
    .run(nowIso(), params.batch, params.subject, String(req.headers['user-agent'] || '').slice(0, 200));
  res.writeHead(302, { location: '/s' });
  res.end();
});

/* ------------------------------------------------------------------ server */

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  for (const r of routes) {
    if (r.method !== req.method) continue;
    // Turn '/s/quiz/:id' into a real regex with one capture group per placeholder.
    const source = '^' + r.pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      .replace(/:(\w+)/g, '([^/]+)') + '$';
    const m = url.pathname.match(new RegExp(source));
    if (!m) continue;
    const keys = [...r.pattern.matchAll(/:(\w+)/g)].map((x) => x[1]);
    const params = {};
    keys.forEach((k, i) => { params[k] = decodeURIComponent(m[i + 1]); });
    try {
      return await r.handler(req, res, params);
    } catch (err) {
      console.error('handler error', url.pathname, err);
      if (!res.headersSent) return send(res, 500, views.errorPage('Please try that again in a moment.'));
      return res.end();
    }
  }
  send(res, 404, views.errorPage('That page does not exist.'));
});

server.listen(PORT, HOST, () => {
  console.log(`TEFOS Quiz listening on http://${HOST}:${PORT}`);
  console.log('Try: /s  (enter a seeded access code)');
});

module.exports = { server };
