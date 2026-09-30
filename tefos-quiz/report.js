'use strict';
/**
 * Participation report. Run: node report.js
 *
 * The single number that decides whether this programme lives or dies is
 * MONTHLY PARTICIPATION: the share of students who took part at all this month.
 * Everything else is secondary.
 */
const { db } = require('./src/db');
const points = require('./src/points');

const monthStart = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString();
const one = (sql, ...p) => Number(Object.values(db.prepare(sql).get(...p))[0]);

const totalStudents = one('SELECT COUNT(*) AS n FROM students WHERE active = 1');
const activeThisMonth = one('SELECT COUNT(DISTINCT student_id) AS n FROM points_ledger WHERE created_at >= ?', monthStart);
const attempts = one('SELECT COUNT(*) AS n FROM attempts WHERE submitted_at >= ?', monthStart);
const firstAttempts = one('SELECT COUNT(*) AS n FROM attempts WHERE is_first = 1 AND submitted_at >= ?', monthStart);
const participation = totalStudents ? Math.round((activeThisMonth / totalStudents) * 100) : 0;

const byCampus = db.prepare(
  `SELECT cp.name AS campus, COUNT(DISTINCT a.student_id) AS participants, COUNT(DISTINCT s.id) AS roll,
          ROUND(AVG(1.0 * a.correct_count / a.total) * 100) AS avg_pct
   FROM campuses cp
   JOIN students s ON s.campus_id = cp.id
   LEFT JOIN attempts a ON a.student_id = s.id AND a.submitted_at >= ?
   GROUP BY cp.id ORDER BY participants DESC`
).all(monthStart);

const subjects = db.prepare(
  `SELECT sj.name AS subject, COUNT(DISTINCT a.student_id) AS students,
          ROUND(AVG(1.0 * a.correct_count / a.total) * 100) AS avg_pct
   FROM attempts a
   JOIN quizzes q   ON q.id = a.quiz_id
   JOIN chapters ch ON ch.id = q.chapter_id
   JOIN subjects sj ON sj.id = ch.subject_id
   WHERE a.submitted_at >= ? GROUP BY sj.name ORDER BY students DESC`
).all(monthStart);

const houses = db.prepare(
  `SELECT COALESCE(s.house,'No house') AS house, COUNT(DISTINCT l.student_id) AS students, SUM(l.delta) AS pts
   FROM points_ledger l JOIN students s ON s.id = l.student_id
   WHERE l.created_at >= ? AND l.board = 1 GROUP BY s.house ORDER BY pts DESC`
).all(monthStart);

// The teacher-facing report: which chapters a class actually struggles with.
const weak = db.prepare(
  `SELECT ch.title AS chapter, q.kind, ROUND(AVG(1.0 * a.correct_count / a.total) * 100) AS avg_pct, COUNT(*) AS attempts
   FROM attempts a
   JOIN quizzes q   ON q.id = a.quiz_id
   JOIN chapters ch ON ch.id = q.chapter_id
   WHERE a.submitted_at >= ? GROUP BY ch.title, q.kind ORDER BY avg_pct ASC LIMIT 6`
).all(monthStart);

const scans = db.prepare('SELECT batch, subject, COUNT(*) AS scans FROM scans GROUP BY batch, subject ORDER BY scans DESC').all();

const tiers = {};
for (const r of db.prepare('SELECT id FROM students WHERE active = 1').all()) {
  const st = points.standing(db, r.id);
  if (st.quizzes > 0) tiers[st.name] = (tiers[st.name] || 0) + 1;
}

const bar = (pct) => {
  const n = Math.round((pct / 100) * 20);
  return '#'.repeat(n) + '.'.repeat(20 - n);
};

console.log('\n============ TEFOS QUIZ - last 30 days ============\n');
console.log(`  PARTICIPATION    ${participation}%  ${bar(participation)}`);
console.log(`                   ${activeThisMonth} of ${totalStudents} students took part`);
console.log(`  ATTEMPTS         ${attempts}  (${firstAttempts} first attempts)`);
console.log(`  VERDICT          ${participation >= 50 ? 'ON TRACK' : participation >= 25 ? 'WATCH IT' : 'AT RISK - fix before scaling'}`);

if (Object.keys(tiers).length) {
  console.log('\n  RANK TIERS');
  for (const t of [...points.TIERS].reverse()) {
    if (tiers[t.name]) console.log(`    ${t.icon} ${t.name.padEnd(13)} ${String(tiers[t.name]).padStart(3)} students`);
  }
}

if (byCampus.length > 1) {
  console.log('\n  BY CAMPUS (participation is the award that matters, not scores)');
  for (const c of byCampus) {
    const pct = c.roll ? Math.round((c.participants / c.roll) * 100) : 0;
    console.log(`    ${c.campus.replace('Telecom Foundation College - ', '').padEnd(22)} ${String(pct + '%').padStart(5)} participation  ${c.avg_pct == null ? '  -' : c.avg_pct + '% avg'}`);
  }
}

if (houses.length) {
  console.log('\n  HOUSES');
  for (const h of houses) console.log(`    ${String(h.house).padEnd(10)} ${String(h.students).padStart(3)} students  ${String(h.pts).padStart(6)} pts`);
}

if (subjects.length) {
  console.log('\n  BY SUBJECT');
  for (const s of subjects) console.log(`    ${s.subject.padEnd(18)} ${String(s.students).padStart(3)} students  ${String(s.avg_pct + '%').padStart(5)} average`);
}

if (weak.length) {
  console.log('\n  WEAKEST CHAPTERS (this is the teacher-facing report)');
  for (const w of weak) console.log(`    ${w.chapter.padEnd(30)} ${String(w.avg_pct + '%').padStart(5)}  over ${w.attempts} attempts  (${w.kind})`);
}

if (scans.length) {
  console.log('\n  QR SCANS BY PRINT BATCH (the marketing measurement)');
  for (const s of scans) console.log(`    ${String(s.batch).padEnd(22)} ${String(s.subject).padEnd(6)} ${String(s.scans).padStart(5)} scans`);
}

console.log('\n==================================================\n');
