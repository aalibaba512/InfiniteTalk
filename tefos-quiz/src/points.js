'use strict';
/**
 * Points and rank engine.
 *
 * Design rules, deliberately:
 *   1. There is NEVER a negative score. A student who scans and does badly must
 *      never end up worse off than a student who ignored the notebook. A
 *      rewards programme that punishes participation kills participation.
 *   2. Only a first attempt can earn leaderboard credit. Retries still pay out,
 *      at a reduced rate, so a student can always recover - but nobody can farm
 *      the board by resubmitting.
 *   3. Every point is written to an append-only ledger with a reason.
 */

const FIRST_ATTEMPT_CORRECT = 10;
const RETRY_CORRECT = 3;
const PERFECT_BONUS = 25;
const MIN_QUESTIONS_FOR_PERFECT = 3;

const REASONS = {
  first: 'correct on first attempt',
  retry: 'correct on a retry',
  perfect: 'perfect chapter score',
};

/**
 * Rank tiers. Participation alone earns the first rank - that is deliberate,
 * because the whole programme dies if the bottom half of the school decides
 * there is nothing to play for.
 *
 * The gate is points earned / points available, NOT a raw average of
 * percentages, and NOT raw points. A student who sits one easy quiz and quits
 * must not out-rank a student who shows up every week.
 */
const TIERS = [
  { key: 'spark',     name: 'Spark',       icon: '✦', min: 0 },
  { key: 'rising',    name: 'Rising Star', icon: '✨', min: 0.30 },
  { key: 'star',      name: 'Star',        icon: '⭐', min: 0.50 },
  { key: 'bright',    name: 'Bright Star', icon: '🌟', min: 0.70 },
  { key: 'supernova', name: 'Supernova',   icon: '💫', min: 0.85 },
  { key: 'galaxy',    name: 'Galaxy',      icon: '🌌', min: 0.95 },
];

/** A student must attempt this many chapters before a tier is displayed. */
const ACTIVITY_FLOOR = 5;

function tierFor(rate) {
  let hit = TIERS[0];
  for (const t of TIERS) if (rate >= t.min) hit = t;
  return hit;
}

/** Has this student already banked a first attempt for this quiz? */
function hasFirstAttempt(db, studentId, quizId) {
  return Boolean(db
    .prepare('SELECT id FROM attempts WHERE student_id = ? AND quiz_id = ? AND is_first = 1')
    .get(studentId, quizId));
}

/** Grade a submitted quiz and write the result. */
function submitAttempt(db, { studentId, quizId, answers, startedAt }) {
  const questions = db
    .prepare('SELECT id, answer_index, explanation FROM questions WHERE quiz_id = ?')
    .all(quizId);
  if (questions.length === 0) throw new Error('This quiz has no questions yet.');

  const isFirst = !hasFirstAttempt(db, studentId, quizId);
  const now = new Date().toISOString();

  // What a perfect first attempt would have scored. Drives the rank tier.
  const possible = questions.length * FIRST_ATTEMPT_CORRECT
    + (questions.length >= MIN_QUESTIONS_FOR_PERFECT ? PERFECT_BONUS : 0);

  const info = db
    .prepare(
      `INSERT INTO attempts (student_id, quiz_id, started_at, submitted_at, is_first, correct_count, total, points, possible)
       VALUES (?, ?, ?, ?, ?, 0, ?, 0, ?)`
    )
    .run(studentId, quizId, startedAt || now, now, isFirst ? 1 : 0, questions.length,
      isFirst ? possible : 0);
  const attemptId = Number(info.lastInsertRowid);

  const insertAnswer = db.prepare(
    `INSERT INTO answers (attempt_id, question_id, chosen, is_correct, is_first_attempt)
     VALUES (?, ?, ?, ?, ?)`
  );
  const insertPoints = db.prepare(
    `INSERT INTO points_ledger (student_id, delta, reason, ref, board, created_at)
     VALUES (?, ?, ?, ?, ?, ?)`
  );

  let correct = 0;
  let points = 0;

  db.exec('BEGIN');
  try {
    for (const q of questions) {
      const chosen = answers.has(String(q.id)) ? answers.get(String(q.id)) : null;
      const isCorrect = chosen !== null && Number(chosen) === Number(q.answer_index);
      if (isCorrect) correct += 1;
      insertAnswer.run(attemptId, q.id, chosen, isCorrect ? 1 : 0, isFirst ? 1 : 0);

      if (isCorrect) {
        const delta = isFirst ? FIRST_ATTEMPT_CORRECT : RETRY_CORRECT;
        points += delta;
        insertPoints.run(studentId, delta, isFirst ? REASONS.first : REASONS.retry,
          `quiz:${quizId}`, isFirst ? 1 : 0, now);
      }
    }

    if (isFirst && correct === questions.length && questions.length >= MIN_QUESTIONS_FOR_PERFECT) {
      points += PERFECT_BONUS;
      insertPoints.run(studentId, PERFECT_BONUS, REASONS.perfect, `quiz:${quizId}`, 1, now);
    }

    db.prepare('UPDATE attempts SET correct_count = ?, points = ? WHERE id = ?')
      .run(correct, points, attemptId);
    db.exec('COMMIT');
  } catch (err) {
    db.exec('ROLLBACK');
    throw err;
  }

  // Explanations are revealed only after submission, so the answer key never
  // reaches the device before the student commits to an answer.
  return { attemptId, isFirst, correct, total: questions.length, points };
}

/** Total points a student can spend as tuition credit. */
function balance(db, studentId) {
  return Number(db
    .prepare('SELECT COALESCE(SUM(delta), 0) AS total FROM points_ledger WHERE student_id = ?')
    .get(studentId).total);
}

/** Leaderboard-eligible points only. Retries deliberately excluded. */
function boardPoints(db, studentId) {
  return Number(db
    .prepare('SELECT COALESCE(SUM(delta), 0) AS total FROM points_ledger WHERE student_id = ? AND board = 1')
    .get(studentId).total);
}

/** Full standing: tier, rate, and whether a formal tier may be shown. */
function standing(db, studentId) {
  const row = db
    .prepare(
      `SELECT COALESCE(SUM(points), 0) AS pts, COALESCE(SUM(possible), 0) AS poss, COUNT(*) AS quizzes
       FROM attempts WHERE student_id = ? AND is_first = 1`
    )
    .get(studentId);

  const pts = Number(row.pts);
  const poss = Number(row.poss);
  const quizzes = Number(row.quizzes);
  const rate = poss > 0 ? pts / poss : 0;
  const eligible = quizzes >= ACTIVITY_FLOOR;

  // Below the activity floor the DISPLAYED tier is clamped to Spark, not just
  // the displayed number. Otherwise a student who sits one easy quiz and quits
  // still reads as "Galaxy" on their own result screen, which is precisely the
  // exploit the floor exists to stop.
  const current = eligible ? tierFor(rate) : TIERS[0];

  return { earned: TIERS, current: current.key, name: current.name, rate,
    points: pts, quizzes, eligible, showRate: eligible };
}

/**
 * Show the "you need X more" nudge ONLY to students genuinely within reach.
 * Telling a child they are 2,000 points from the board is how you make them
 * stop opening the book.
 */
function gapToBoard(db, studentId, boardSize = 10) {
  const me = boardPoints(db, studentId);
  const cutoff = db
    .prepare(
      `SELECT SUM(delta) AS pts FROM points_ledger
       WHERE board = 1 AND created_at >= date('now','start of month')
       GROUP BY student_id ORDER BY pts DESC LIMIT 1 OFFSET ?`
    )
    .get(boardSize - 1);
  const target = cutoff && Number(cutoff.pts) > 0 ? Number(cutoff.pts) : 0;
  const gap = target - me;
  if (gap <= 0) return null;
  return gap <= me * 0.5 + 50 ? gap : null;
}

module.exports = {
  FIRST_ATTEMPT_CORRECT, RETRY_CORRECT, PERFECT_BONUS,
  TIERS, ACTIVITY_FLOOR,
  tierFor, standing, gapToBoard, submitAttempt, hasFirstAttempt, balance, boardPoints,
};
