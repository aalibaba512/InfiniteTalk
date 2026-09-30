# TEFOS Quiz

Chapter quiz engine for the **Telecom Foundation Education System** notebook QR programme.

A student finishes Chapter 1 of Physics, scans the QR on their notebook, types the
6-character code printed inside the cover, and takes the chapter quiz. Points
accumulate toward a monthly **merit bursary**. Questions reference things that
happened in *that* class, so they cannot be googled.

> **Note:** this folder is unrelated to the InfiniteTalk model in this repo. It
> lives here only because loose files outside the repository were not persisting
> in the workspace. It has no dependency on the rest of the repo and can be moved
> anywhere.

## Run it

No `npm install`. No build step. Node 22+ only.

```bash
node src/seed.js --force     # creates data/tefos.db with demo data
node src/server.js           # http://localhost:3000
node test/e2e.js             # 33 assertions (server must be running)
node report.js               # participation report
```

Demo access codes are printed by the seed script.

---

## The design decisions that matter

### Points are never negative

The original sketch was `+10 correct / −5 wrong`. Run the arithmetic over a
4-question quiz and you get a floor of **−20**. A student who scans and does badly
ends up *worse off* than a student who ignored the notebook entirely. In a
programme whose only success metric is participation, that is fatal — and a
nervous Year 9 does that arithmetic instantly.

| Event | Points | Counts on leaderboard |
|---|---|---|
| Correct, first attempt | **+10** | yes |
| Wrong, any attempt | **0** | — |
| Correct, retry | **+3** | no |
| 100% on a chapter (3+ questions) | **+25** | yes |

The floor is 0, so scanning always beats not scanning, and the only route to the
top is accuracy on first tries.

### The login is a printed code, not a signup form

The sketch had the student type name, father's name, class, roll number and campus.
Replaced with a 6-character code printed inside the front cover:

- **Privacy.** The school already holds all of this in its admission records —
  there is no reason to re-collect it over HTTP through a public web form.
- **Conversion.** No one types their father's name for 10 points.
- **Data quality.** Hand-typed roll numbers are wrong often enough to wreck a
  leaderboard's credibility in week one.
- **Abuse.** Codes are rotatable per student; login is rate-limited to 10 tries per
  15 minutes per IP.

The code alphabet deliberately excludes lookalike glyphs (0/O, 1/I/L) so a code can
be read aloud or copied off a smudged slip.

### Rank tiers have an activity floor

| Points rate | Rank |
|---|---|
| Any points | ✦ **Spark** |
| 30%+ | ✨ **Rising Star** |
| 50%+ | ⭐ **Star** |
| 70%+ | 🌟 **Bright Star** |
| 85%+ | 💫 **Supernova** |
| 95%+ | 🌌 **Galaxy** |

Participation alone earns the first rank. The programme dies if the bottom half of
the school decides there is nothing to play for.

The tier comes from **points earned ÷ points available**, never a raw average of
percentages, and a student must attempt **5 chapters** before a tier shows. Without
that floor, a student who sits one easy quiz, scores 95% and quits would out-rank a
student who shows up every week. Below the floor the *displayed* tier is clamped to
Spark as well as the displayed number — otherwise the student still reads "Galaxy"
on their own result screen and the floor achieves nothing. (That exact bug existed
and is now covered by a test.)

### Show growth, not shame; show the gap only when it's reachable

Two rules on the leaderboard, both tested:

- **Growth first.** "You gained 180 points this month" measures progress against
  your own past self, which sustains effort.
- **The gap is conditional.** "240 more points puts you on the top 10 board" is
  only shown when the student is genuinely within reach. Telling a child they are
  2,000 points away is how you make them stop opening the book.

Publish at least three boards — Champions, Most improved, and Participation rate.
Never only the top. The participation board should be scored on *participation*, not
scores, so smaller and weaker campuses have a fair way to win.

### Only a first attempt moves the leaderboard

Retries still pay, so a student can always recover, but they cannot climb. The
`one_first_attempt` partial unique index enforces this at the database level, so a
double-tap or a browser refresh cannot farm points.

### The quiz is uncheatable by design

Every quiz is one of two kinds:

- **`textbook`** — syllabus content, the normal kind of quiz.
- **`classroom`** — questions only someone who was *there* can answer. *"On the
  first day of the Motion unit, which activity did we do?"*, *"Our lab report was due
  on which date?"*, *"Which group presented the acceleration results first?"*

Nobody can search those. This is also better teaching: it pays students for paying
attention, not for googling.

The answer key is never sent to the device. Options are shuffled server-side on
every request, so a student reading the page source cannot recover the answer from
the markup. Explanations are revealed only after submission. The quiz start time is
HMAC-signed so it cannot be backdated to dodge the timer.

### Merit bursary, never "students earn their own fee"

Same budget impact, completely different posture. "Students compete to pay their
own tuition" reads badly to parents, inspectors and newspapers. "Up to 10 merit
bursaries of up to 10% of one month's fee, awarded on points" is something a school
can announce proudly.

Cap the total value — suggest **0.5–1% of annual fee revenue**. Keep a small,
separately-funded **need-based** component, because a bursary helps a wealthy family
more than a poor one; sponsors underwrite that, and it is the best CSR outcome
report available.

**Quiz points and school roles are deliberately decoupled.** Quiz points earn
prizes. Head Girl/Head Boy, monitors and prefects stay with the existing school
process. Merging them replaces an election with a leaderboard, which parents will
read as a rigged contest.

---

## What the QR should point at

Each printed batch gets its own tracked short link:

```
https://<host>/t/{batch}/{subject}     ->  redirects to /s, records the scan
```

So the school can answer *"which print run of notebooks actually drove
engagement?"* — the marketing measurement the programme is supposed to produce.
`report.js` prints it by batch.

**For a Pakistani rollout, the single biggest adoption lever is zero-rated data.**
If the operator sponsors zero-rating for this host, participation should jump
enormously. Pages are already small: a full 4-question quiz is **~2.5 KB gzipped**.

---

## Privacy posture

Pakistan has no fully enacted comprehensive data-protection statute comparable to
GDPR or COPPA. That is not a reason to collect loosely — adopt GDPR-K-grade
standards voluntarily, because they are cheap, defensible, and any international
sponsor will ask. The engineering already assumes it:

- No personal data is collected through any web form.
- No full names or guardian names on any public page — leaderboards show
  `display_name` only.
- `points_ledger` is append-only, so every point a student has ever been awarded is
  traceable. Never `UPDATE` or `DELETE` a row.
- Print a fallback inside the front cover: the front office number and the key
  links. A student must never be unable to reach an adult because a server is down.

## Stack

`node:http` + `node:sqlite` + server-rendered HTML. Zero dependencies, so handover
is `node server.js` and nothing else. Plain HTML forms, ~40 lines of JavaScript
total, no client framework. Works on a five-year-old Android over 3G.

## Not built yet

In priority order:

1. **Teacher dashboard** — class-level results and weak-chapter detection. This is
   how the programme earns teacher buy-in instead of looking like surveillance, and
   it is why teachers will not quietly sabotage it in week three. The underlying
   numbers already exist in `report.js`.
2. **Admin console** — question bank, student/campus registry, bursary rules.
3. **Championship** — school heat and city final as separate entities, with 16
   school champions rather than 5 finalists.
4. **Sponsor tiers** — logo placement, ceremony sponsorships, scholarship funds.
5. **Monthly bursary run** — rank, cap, and export a disbursement list.
6. **NFC tag** on the cover, alongside the QR.
