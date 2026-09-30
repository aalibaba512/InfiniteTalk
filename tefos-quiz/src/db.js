'use strict';
/**
 * Schema + database handle.
 * Uses node:sqlite (built into Node 22+) so there is nothing to npm install.
 */
const { DatabaseSync } = require('node:sqlite');
const path = require('node:path');
const fs = require('node:fs');

const DATA_DIR = path.join(__dirname, '..', 'data');
fs.mkdirSync(DATA_DIR, { recursive: true });
const DB_PATH = process.env.DB_PATH || path.join(DATA_DIR, 'tefos.db');

const db = new DatabaseSync(DB_PATH);
db.exec('PRAGMA journal_mode = WAL;');
db.exec('PRAGMA foreign_keys = ON;');

db.exec(`
CREATE TABLE IF NOT EXISTS campuses (
  id    INTEGER PRIMARY KEY,
  name  TEXT NOT NULL,
  code  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS classes (
  id          INTEGER PRIMARY KEY,
  campus_id   INTEGER NOT NULL REFERENCES campuses(id),
  name        TEXT NOT NULL,
  year_group  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
  id            INTEGER PRIMARY KEY,
  student_no    TEXT NOT NULL UNIQUE,
  first_name    TEXT NOT NULL,
  display_name  TEXT,                 -- nickname shown on public leaderboards
  guardian_name TEXT,                 -- held by the school, never shown publicly
  class_id      INTEGER REFERENCES classes(id),
  campus_id     INTEGER REFERENCES campuses(id),
  house         TEXT,
  active        INTEGER NOT NULL DEFAULT 1
);

-- The login mechanism. Printed inside the front cover of the notebook.
-- A student types this instead of submitting personal details to a web form.
CREATE TABLE IF NOT EXISTS access_codes (
  code       TEXT PRIMARY KEY,
  student_id INTEGER NOT NULL REFERENCES students(id),
  rotated_at TEXT
);

CREATE TABLE IF NOT EXISTS subjects (
  id     INTEGER PRIMARY KEY,
  name   TEXT NOT NULL,
  code   TEXT NOT NULL UNIQUE,
  colour TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
  id         INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL REFERENCES subjects(id),
  title      TEXT NOT NULL,
  seq        INTEGER NOT NULL,
  UNIQUE(subject_id, seq)
);

CREATE TABLE IF NOT EXISTS quizzes (
  id             INTEGER PRIMARY KEY,
  chapter_id     INTEGER NOT NULL REFERENCES chapters(id),
  -- 'classroom' questions reference things that happened in THIS school and
  -- cannot be googled. 'textbook' questions test syllabus content.
  kind           TEXT NOT NULL,
  time_limit_sec INTEGER NOT NULL DEFAULT 150
);

CREATE TABLE IF NOT EXISTS questions (
  id           INTEGER PRIMARY KEY,
  quiz_id      INTEGER NOT NULL REFERENCES quizzes(id),
  prompt       TEXT NOT NULL,
  options      TEXT NOT NULL,          -- JSON array of strings
  answer_index INTEGER NOT NULL,
  explanation  TEXT,
  pos          INTEGER
);

CREATE TABLE IF NOT EXISTS attempts (
  id            INTEGER PRIMARY KEY,
  student_id    INTEGER NOT NULL REFERENCES students(id),
  quiz_id       INTEGER NOT NULL REFERENCES quizzes(id),
  started_at    TEXT,
  submitted_at  TEXT,
  is_first      INTEGER NOT NULL DEFAULT 0,
  correct_count INTEGER,
  total         INTEGER,
  points        INTEGER,
  -- Maximum points available on this quiz, used to compute the rank tier.
  -- Only meaningful on first attempts.
  possible      INTEGER
);

-- Only one first attempt per student per quiz, enforced at the database level
-- so a double-tap or refresh cannot farm points.
CREATE UNIQUE INDEX IF NOT EXISTS one_first_attempt
  ON attempts(student_id, quiz_id) WHERE is_first = 1;

CREATE TABLE IF NOT EXISTS answers (
  attempt_id       INTEGER NOT NULL REFERENCES attempts(id),
  question_id      INTEGER NOT NULL REFERENCES questions(id),
  chosen           INTEGER,
  is_correct       INTEGER NOT NULL,
  is_first_attempt INTEGER NOT NULL
);

-- Append-only. Never UPDATE or DELETE a row here: parents and auditors must be
-- able to trace every single point a student has ever been awarded.
CREATE TABLE IF NOT EXISTS points_ledger (
  id         INTEGER PRIMARY KEY,
  student_id INTEGER NOT NULL REFERENCES students(id),
  delta      INTEGER NOT NULL,
  reason     TEXT NOT NULL,
  ref        TEXT,
  board      INTEGER NOT NULL DEFAULT 1,  -- 1 = counts toward leaderboard
  created_at TEXT NOT NULL
);

-- Scan tracking. This is the marketing measurement: which printed batch of
-- notebooks actually drives engagement.
CREATE TABLE IF NOT EXISTS scans (
  id         INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL,
  batch      TEXT,
  subject    TEXT,
  campus     TEXT,
  user_agent TEXT
);

CREATE TABLE IF NOT EXISTS code_attempts (
  id         INTEGER PRIMARY KEY,
  ip         TEXT,
  created_at TEXT NOT NULL
);
`);

module.exports = { db, DB_PATH };
