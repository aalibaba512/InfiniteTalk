'use strict';
/**
 * Demo seed. Mirrors the real shape: campuses in Islamabad, year 9-11 classes,
 * four houses, one subject (Physics) fully built out and three more partially.
 *
 * Run: node src/seed.js --force
 */
const { db } = require('./db');

const force = process.argv.includes('--force');
if (Number(db.prepare('SELECT COUNT(*) AS n FROM students').get().n) > 0 && !force) {
  console.log('Database already seeded. Use --force to wipe and reseed.');
  process.exit(0);
}
if (force) {
  for (const t of ['scans', 'code_attempts', 'points_ledger', 'answers', 'attempts',
    'questions', 'quizzes', 'chapters', 'subjects', 'access_codes', 'students',
    'classes', 'campuses']) {
    db.exec(`DELETE FROM ${t};`);
  }
  console.log('Cleared existing data.');
}

db.exec('BEGIN');

const campus = db.prepare('INSERT INTO campuses (name, code) VALUES (?, ?)');
const cMain = Number(campus.run('Telecom Foundation College - Main Campus Islamabad', 'MAIN').lastInsertRowid);
const cCap = Number(campus.run('Telecom Foundation College - Capital Campus Islamabad', 'CAP').lastInsertRowid);
const cSat = Number(campus.run('Telecom Foundation College - Satellite Campus Islamabad', 'SAT').lastInsertRowid);

const klass = db.prepare('INSERT INTO classes (campus_id, name, year_group) VALUES (?, ?, ?)');
const classes = [[cMain, '9-A', 'Year 9'], [cMain, '9-B', 'Year 9'], [cCap, '9-A', 'Year 9'], [cSat, '9-A', 'Year 9']];

const student = db.prepare(
  `INSERT INTO students (student_no, first_name, display_name, guardian_name, class_id, campus_id, house)
   VALUES (?, ?, ?, ?, ?, ?, ?)`
);
const codeRow = db.prepare('INSERT INTO access_codes (code, student_id) VALUES (?, ?)');

const NAMES = ['Ayesha', 'Hamza', 'Zoya', 'Bilal', 'Mariam', 'Usman', 'Fatima', 'Ali',
  'Hira', 'Osama', 'Sana', 'Danish', 'Areeba', 'Fahad', 'Noor', 'Talha',
  'Mahnoor', 'Shahzeb', 'Iqra', 'Rayyan', 'Sumaiya', 'Adeel', 'Komal', 'Omar'];
const HOUSES = ['Indus', 'Kabul', 'Chenab', 'Jhelum'];
const GUARDIAN = ['Mr', 'Mrs'];
const SURNAME = ['Khan', 'Malik', 'Sheikh', 'Chaudhry', 'Qureshi', 'Aslam', 'Farooq', 'Butt'];

// 32-character alphabet with no lookalike glyphs, so a code can be read aloud
// or copied off a slip that has been smudged.
const ALPHA = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789';
let n = 0;
NAMES.forEach((name, i) => {
  const cls = classes[i % classes.length];
  const classId = Number(klass.run(cls[0], cls[1], cls[2]).lastInsertRowid);
  n += 1;
  const sid = Number(student.run(
    `TFC-${2400 + n}`, name, name,
    `${GUARDIAN[i % 2]} ${SURNAME[i % SURNAME.length]}`,
    classId, cls[0], HOUSES[i % HOUSES.length]
  ).lastInsertRowid);
  let out = '';
  for (let k = 0; k < 6; k += 1) out += ALPHA[Math.floor(Math.random() * ALPHA.length)];
  codeRow.run(out, sid);
  if (i < 4) console.log(`  demo access code: ${out}  ->  ${name}`);
});

const subject = db.prepare('INSERT INTO subjects (name, code, colour) VALUES (?, ?, ?)');
const chapter = db.prepare('INSERT INTO chapters (subject_id, title, seq) VALUES (?, ?, ?)');
const quiz = db.prepare('INSERT INTO quizzes (chapter_id, kind, time_limit_sec) VALUES (?, ?, ?)');
const question = db.prepare(
  'INSERT INTO questions (quiz_id, prompt, options, answer_index, explanation, pos) VALUES (?, ?, ?, ?, ?, ?)'
);

const addSubject = (name, sCode, colour, chapters) => {
  const sid = Number(subject.run(name, sCode, colour).lastInsertRowid);
  let pos = 0;
  for (const ch of chapters) {
    const chId = Number(chapter.run(sid, ch.title, ch.seq).lastInsertRowid);
    for (const [kind, qs] of Object.entries(ch.questions)) {
      const qId = Number(quiz.run(chId, kind, kind === 'classroom' ? 90 : 150).lastInsertRowid);
      for (const q of qs) question.run(qId, q.p, JSON.stringify(q.o), q.a, q.e || null, (pos += 1));
    }
  }
};

addSubject('Physics', 'PHY', '#0b6b7d', [
  {
    title: 'Motion in One Dimension', seq: 1,
    questions: {
      classroom: [
        { p: 'On the first day of the Motion unit, which classroom activity did we do?',
          o: ['A race up the stairs with stopwatches', 'A film reel on a projector', 'A water-balloon experiment', 'A debate about rest and motion'],
          a: 0, e: 'Stair race with stopwatches - we used the data for the graph in the exercise book.' },
        { p: 'In the stair race, who came first overall?', o: ['Hamza', 'Ayesha', 'Bilal', 'Zoya'], a: 0,
          e: 'Hamza took first place, narrowly, in the boys heat on 9 September.' },
        { p: 'Our lab report on the ticker-tape timer was due on which date?',
          o: ['2 September', '9 September', '16 September', '23 September'], a: 1,
          e: 'The report was submitted on 9 September, the same week as the stairs experiment.' },
        { p: 'Which group was asked to present the acceleration results first?',
          o: ['Group A', 'Group B', 'Group C', 'Group D'], a: 1,
          e: 'Group B presented first because their readings were complete.' },
      ],
      textbook: [
        { p: 'A car accelerates from rest at 4 m/s^2 for 6 seconds. What speed does it reach?',
          o: ['10 m/s', '20 m/s', '24 m/s', '30 m/s'], a: 2, e: 'v = u + at = 0 + (4 x 6) = 24 m/s.' },
        { p: 'Which quantity is measured in metres per second per second?',
          o: ['Velocity', 'Acceleration', 'Displacement', 'Momentum'], a: 1,
          e: 'Acceleration is the rate of change of velocity, so its unit is m/s^2.' },
        { p: 'A body travels 120 m in 15 s at constant speed. What is its speed?',
          o: ['6 m/s', '8 m/s', '10 m/s', '12 m/s'], a: 1, e: 'v = d/t = 120/15 = 8 m/s.' },
        { p: 'Which of these is a vector quantity?',
          o: ['Speed', 'Distance', 'Mass', 'Displacement'], a: 3,
          e: 'Displacement has both magnitude and direction, so it is a vector.' },
        { p: 'The gradient of a distance-time graph gives:',
          o: ['Acceleration', 'Speed', 'Distance', 'Force'], a: 1, e: 'Slope of a distance-time graph is speed.' },
      ],
    },
  },
  {
    title: 'Forces and Laws of Motion', seq: 2,
    questions: {
      classroom: [
        { p: 'For our friction investigation, what did we use as the sliding surface?',
          o: ['A wooden board', 'A glass sheet', 'A metal tray', 'A plastic sheet'], a: 0,
          e: 'The wooden board from the physics store was the sliding surface.' },
        { p: 'How many students were on the team that built the spring-balance force meter?',
          o: ['Three', 'Four', 'Five', 'Six'], a: 1, e: 'Four students - the meter is still in the lab cupboard.' },
      ],
      textbook: [
        { p: 'Newton\'s third law states that forces come in:',
          o: ['Pairs of equal magnitude', 'A single large and small force', 'Equal and opposite directions only', 'Pairs that cancel to zero'], a: 0,
          e: 'Forces are equal in magnitude, opposite in direction, and act on different bodies.' },
        { p: 'What is the SI unit of force?', o: ['Joule', 'Newton', 'Watt', 'Pascal'], a: 1 },
        { p: 'A 5 kg mass accelerates at 2 m/s^2. What resultant force acts on it?',
          o: ['2.5 N', '7 N', '10 N', '25 N'], a: 2, e: 'F = ma = 5 x 2 = 10 N.' },
        { p: 'An object moving at constant velocity in a straight line has:',
          o: ['A large resultant force', 'Zero resultant force', 'Increasing acceleration', 'Non-zero momentum always'], a: 1 },
        { p: 'Weight is a force in newtons, and equals:', o: ['mg', 'm/g', 'g/m', 'm + g'], a: 0, e: 'W = mg, where g is about 9.8 N/kg.' },
      ],
    },
  },
]);

addSubject('Chemistry', 'CHE', '#7a3fb8', [{
  title: 'Atomic Structure', seq: 1,
  questions: { textbook: [
    { p: 'What is the number of protons in an atom called?', o: ['Mass number', 'Atomic number', 'Neutron number', 'Valency'], a: 1 },
    { p: 'The maximum number of electrons in the second shell is:', o: ['2', '6', '8', '18'], a: 2 },
    { p: 'Isotopes of an element differ in their number of:', o: ['Protons', 'Electrons', 'Neutrons', 'Shells'], a: 2 },
    { p: 'The neutral particle in the nucleus is the:', o: ['Proton', 'Electron', 'Neutron', 'Photon'], a: 2 },
    { p: 'Which subatomic particle has a negative charge?', o: ['Proton', 'Neutron', 'Electron', 'Nucleus'], a: 2 },
  ] },
}]);

addSubject('Mathematics', 'MAT', '#c2600a', [{
  title: 'Sets and Venn Diagrams', seq: 1,
  questions: { textbook: [
    { p: 'The intersection of two sets is written as:', o: ['A union B', 'A n B', 'A - B', 'A U B'], a: 1 },
    { p: 'The universal set is usually denoted by:', o: ['U', 'E', 'X', 'O'], a: 0 },
    { p: 'Two sets with no common elements are called:', o: ['Overlapping', 'Disjoint', 'Nested', 'Equal'], a: 1 },
    { p: 'A set containing only one element is a:', o: ['Null set', 'Singleton', 'Empty set', 'Subset'], a: 1 },
    { p: 'The complement of set A is written as:', o: ["A'", 'A n U', 'A - U', 'U n A'], a: 0 },
  ] },
}]);

addSubject('Computer Science', 'CSC', '#1a7f4b', [{
  title: 'Introduction to Algorithms', seq: 1,
  questions: { textbook: [
    { p: 'A step-by-step procedure to solve a problem is called an:', o: ['Algorithm', 'Program', 'Compiler', 'Variable'], a: 0 },
    { p: 'A flowchart symbol shaped like a diamond represents a:', o: ['Process', 'Decision', 'Start', 'Input'], a: 1 },
    { p: 'The smallest meaningful unit of a program is a:', o: ['Statement', 'Character', 'Bit', 'Byte'], a: 0 },
    { p: 'Which of these is NOT a control structure?', o: ['Sequence', 'Selection', 'Iteration', 'Compilation'], a: 3 },
  ] },
}]);

db.exec('COMMIT');

console.log('Seeded:', {
  campuses: db.prepare('SELECT COUNT(*) n FROM campuses').get().n,
  students: db.prepare('SELECT COUNT(*) n FROM students').get().n,
  subjects: db.prepare('SELECT COUNT(*) n FROM subjects').get().n,
  chapters: db.prepare('SELECT COUNT(*) n FROM chapters').get().n,
  quizzes: db.prepare('SELECT COUNT(*) n FROM quizzes').get().n,
  questions: db.prepare('SELECT COUNT(*) n FROM questions').get().n,
});
