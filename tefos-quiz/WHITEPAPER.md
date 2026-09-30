# Turning the Notebook Into a Learning Loop

### A whitepaper on chapter-quiz engagement, merit bursaries, and inter-school measurement for a 16-campus school network

**Prepared for:** Telecom Foundation Education System
**Subject:** The notebook QR programme — design, economics, safeguards, and rollout
**Status:** Proposal. Nothing here is in production.

---

## Abstract

This paper describes a programme that begins with a single piece of print: a QR code on the cover of every subject notebook already being issued to students.

A student finishes Chapter 1 of Physics, opens their notebook, scans the code, types a six-character access code printed inside the front cover, and answers five questions. Most of those questions are about things that happened in *that specific classroom, that specific week* — so they cannot be looked up. The student earns points toward a monthly merit bursary, acquires a named rank, and appears on a board that spans all sixteen campuses.

We argue three things. First, that the notebook is the only school-owned surface a student touches voluntarily and daily, which makes it the highest-yield engagement channel available. Second, that the programme lives or dies on a single number — monthly participation — and that the intuitive scoring design (which penalises wrong answers) actively destroys that number. Third, that the school can fund the entire reward pool out of foregone tuition revenue rather than cash, which is what makes the scheme affordable at sixteen campuses and independent of sponsorship.

A working prototype with thirty-three automated tests accompanies this paper. The design decisions below are not aspirational; they are implemented and pinned by tests.

---

## 1. The opportunity

Schools run on measurement. Attendance is measured, grades are measured, fee collection is measured. What is almost never measured is the moment a student finishes a chapter.

That moment is the most valuable instructional minute a school has, and it is the one that goes unexploited. What typically happens instead is a broadcast strategy: a newsletter, an announcement, a parent circular, a poster. All of these compete with a student's existing attention, all of them are passive, and all of them are ignored at a rate of over ninety per cent within a fortnight.

The notebook solves this structurally rather than behaviourally. A student who has just completed a chapter is holding a book with a code on the cover, at the exact point of maximum receptivity. Reaching them requires no new behaviour — no app download, no URL memorisation, no notification, no reminder to parents. The channel is present, open, and in the student's hand.

Three properties follow, and they compound:

| Property | Why it matters |
|---|---|
| **Voluntary and recurring** | It is opened every day regardless of the programme. No other school channel has this. |
| **Physical and visible** | It sits open on a desk where visitors, invigilators, and parents see it. It is a physical advert for a school, placed in a student's own hands. |
| **Mobile in practice** | Students are already photographing and posting their materials. The notebook is already a marketing asset; the programme just instruments it. |

### 1.1 Why the obvious design fails

The first instinct is a signup form: the student scans, then enters name, parent's name, class, roll number, and campus. This fails in four independent ways, and any one of them is fatal.

**Privacy.** A web form that collects a child's name, a parent's name, a school, a class and a roll number is a children's personal data collection point. Under GDPR, COPPA, or India's DPDP Act, this requires verifiable parental consent obtained by a specific, defensible process. A login box is not that process. A school operator has the ability to obtain consent properly at enrolment; it does not have the ability to obtain it from a child at a public kiosk.

**Conversion.** No eleven-year-old types their father's name to win ten points. Every additional field on an optional-entry form costs participation, and the fields most likely to be abandoned are exactly the identifying ones. The most motivated student in the cohort is the one most likely to be deterred by being asked to identify themselves to a public endpoint.

**Data quality.** Hand-typed roll numbers carry a material error rate. A leaderboard containing visible mistakes loses its credibility permanently, in week one, with the teachers and parents whose buy-in the programme depends on.

**Abuse.** A form that accepts a name creates an impersonation problem: any student can score under another student's identity. A rotatable per-student code does not.

The school already holds every one of these facts in its admission records. There is no reason to re-collect them over HTTP. The system this paper describes therefore has **no student data collection surface at all** — the entire student login is a six-character code.

---

## 2. Design principles

Seven principles govern the system. Each is implemented, and each is pinned by at least one automated test.

### 2.1 Participation can never be punished

This is the most important line in the paper, and it is a correction rather than a feature.

The intuitive scoring model awards ten points for a correct answer and deducts five for a wrong one. Under that model the *floor of a five-question quiz is negative twenty-five points*. A student who scans, attempts honestly and performs badly finishes **worse off** than a student who never scans at all.

This is catastrophic in a programme whose only success metric is participation. A nervous Year 9 performs the arithmetic immediately and concludes that the rational strategy is not to participate. A negative marking scheme, which is entirely appropriate in an examination where a grade is at stake, is a tax on trying in a scheme where no grade is at stake and the only currency is effort.

The implemented model has a floor of zero:

| Event | Points | Counts on leaderboard |
|---|---|---|
| Correct, first attempt | +10 | Yes |
| **Wrong, any attempt** | **0** | — |
| Correct, retry | +3 | No |
| Perfect chapter (≥3 questions) | +25 | Yes |

Scanning is therefore never worse than not scanning. The only route to the top is accuracy on first attempts, which is the thing we actually want to incentivise.

### 2.2 Participation earns the first rank

A student who takes part acquires an identity immediately, at any score including zero. The first rank tier is granted for taking part at all. The bottom half of the cohort must have a reason to open the notebook, and if the ladder has a cliff beneath the first rung, they will find it.

### 2.3 Only a first attempt moves the board

Retries pay out, at a reduced rate, so a student who has genuinely misunderstood a concept is never locked out and never punished. But retried points do not count toward the leaderboard. A student cannot resubmit until they top the board.

This is enforced in the database, not in application code, via a partial unique index. A double-tap, a refresh, a network retry, or a tampered client cannot produce a second scoring attempt. Relying on application logic for this would eventually fail; relying on a unique constraint cannot.

### 2.4 Show growth before distance

The natural instinct on a leaderboard is to tell a student how far they are from the top. This is a design error. A gap measured against other people is a measure of defeat, and a student whose gap is large has a rational reason to disengage.

Progress measured against one's own past self is a measure of momentum, and it is available to every student regardless of ability.

The implemented rule is a hybrid:

- **Growth is always shown.** "You are 180 points ahead of where you were last month."
- **The gap is shown only when genuinely reachable.** The "240 more points puts you on the top 10 board" line is suppressed unless the shortfall is plausibly closable.

Both lines appear together when a student is within reach, so near-miss players receive a genuine nudge while distant players receive encouragement instead of a verdict.

### 2.5 Never publish only the top

Three boards, always: **Champions**, **Most improved**, and **Participation rate**. The third is awarded on the share of a campus's students who took part, not on scores. This is what allows a smaller or weaker campus to win something genuine, and it aligns the competitive incentive with the programme's actual purpose.

### 2.6 Never remove a student's access to an adult

Every screen in the system carries the front-office telephone number in the footer, and the same number is printed permanently inside the front cover of every notebook. A student must never be unable to reach an adult because a server is unavailable. This costs one line of print and is not negotiable.

### 2.7 Collect nothing that is not needed

The absence of a data collection surface is a design outcome, not an oversight. See §1.1 and §7.

---

## 3. The student journey

The entire interaction is five steps, and it must stay that way. Everything else in this paper exists to keep students at step five.

1. **Scan** the QR code on the notebook cover. A tracked redirect records the scan and forwards to the code entry screen.
2. **Enter** the six-character code printed inside the front cover. The code alphabet deliberately excludes lookalike glyphs (0/O, 1/I/L) so a code can be read aloud or copied from a smudged slip. Login is rate-limited to ten attempts per fifteen minutes per address, and codes are rotatable per student.
3. **Choose** the chapter they have just finished. Each subject notebook is scoped to its own subject, so the app opens on the relevant chapter list.
4. **Answer** five questions under a time limit. The answer key is never transmitted to the device (§6).
5. **Receive** points, a rank tier, the growth line, and a place on the board.

Target completion time: ninety seconds.

A full five-question quiz page is approximately **2.5 KB gzipped**, including all styling, with no client framework and roughly forty lines of JavaScript. It renders on a five-year-old Android handset over 3G.

---

## 4. The rank system

Ranks are named for clarity and progression, deliberately avoiding a theme that would read as an adult hierarchy.

| Points rate | Rank | Meaning |
|---|---|---|
| Any | ✦ Spark | You took part. This is the whole entry fee. |
| 30% | ✨ Rising Star | Getting going. |
| 50% | ⭐ Star | Solid and consistent. |
| 70% | 🌟 Bright Star | Reliably strong across chapters. |
| 85% | 💫 Supernova | Outstanding. |
| 95% | 🌌 Galaxy | Exceptional. |

### 4.1 The activity floor

Rank is computed as **points earned ÷ points available**, where points available is the score a perfect first attempt would have achieved on each chapter. It is never a raw average of percentages, because a chapter with four questions and a chapter with ten would otherwise carry equal weight, and a student averaging 60% by acing three chapters and failing two completely would be indistinguishable from a student who is consistently adequate.

Crucially, **no rank tier is displayed until a student has attempted five chapters.**

Without this floor the system is trivially exploitable: a student sits one easy chapter, scores ninety-five per cent on a first attempt, and holds the top rank for the month while never opening the notebook again. Worse, they would do so while a student who engaged every week displayed a lower rank. The floor is what makes sustained engagement the winning strategy.

The floor must apply to the **displayed** tier, not merely to the stored one. An earlier build of the prototype applied the floor in the data layer but not in the view, so a student with a single perfect chapter still read "Galaxy" on their own result screen. The floor was therefore achieving nothing. The displayed tier is now clamped to Spark below the floor, and a test pins the behaviour.

### 4.2 Why not names like Captain and Colonel

A military-rank ladder was considered and rejected. Senior commissioned ranks applied to eleven-year-olds are incongruous, they acquire gendered and political connotations that are not neutral in a school setting, and — most practically — they are not aspirational to the student. A child wants to be a Quiz Champion, not a Brigadier.

The word "Captain" survives usefully as a single elective role: **Quiz Captain**, one per class, chosen by the highest-scoring students from among themselves. Because it is elected rather than scored, it confers peer respect rather than opening an argument with a scoreboard.

### 4.3 Roles and points are decoupled

Quiz points determine prizes. They do **not** determine any existing school role.

Head Girl, Head Boy, class monitor and prefect remain governed entirely by the school's existing process. Merging them with a points table would replace a student election with a leaderboard — a change that parents of losing candidates would reasonably read as a rigged contest, that a newspaper would frame as a school monetising children's grades, and that invites fee-regulation scrutiny. It would also create a high-stakes monthly event around a child's worth, which is a considerably more serious matter than a leaderboard.

A single additional role, Quiz Captain, is available if the school wants an aspiration attached to the programme. It is additive and elective.

---

## 5. Question design: the quiz that cannot be searched

Every quiz is one of two kinds.

**Textbook questions** test syllabus content in the conventional way. **Classroom questions** reference events in that specific class, during that specific period. Examples from the prototype:

- *"On the first day of the Motion unit, which classroom activity did we do?"*
- *"Our lab report on the ticker-tape timer was due on which date?"*
- *"How many students were on the team that built the spring-balance force meter?"*
- *"Which group was asked to present the acceleration results first?"*

No student can look these up. Only a student who was present can answer them.

This solves the integrity problem that ends most quiz-based incentive schemes, where the top prizes are won by whoever has the fastest connection and the most willing relatives. It is also simply better pedagogy: the programme ends up paying students for *paying attention in class*, which is the outcome a school actually wants.

The prototype's seeded data places classroom and textbook questions in roughly equal proportion, with classroom questions given a shorter time limit.

---

## 6. Anti-gaming controls

| Control | Implementation |
|---|---|
| Answer key never reaches the device | Options are shuffled server-side on every request. The submitted values are indices into the original array, so a student reading the page source cannot map an option to its correctness. Verified by sampling twelve page loads and confirming the correct option occupies different positions. |
| Explanations withheld until submission | Explanations are held server-side and revealed only on the result page. |
| Timer cannot be backdated | The quiz start time is HMAC-signed with the server secret and validated on submission. |
| One scoring attempt per chapter | Partial unique database index on `(student_id, quiz_id) WHERE is_first = 1`. |
| Timing uncheatable | Each chapter's questions draw on the class's own history, so a shared answer key has no value. |
| Codes rotatable and rate-limited | Per-student codes, ten attempts per fifteen minutes per address. |
| Session integrity | HMAC-signed session cookie, `HttpOnly`, `SameSite=Lax`, constant-time signature comparison. Rejects forged tokens. |

A test suite of thirty-three assertions covers each of these, including the negative-property checks — for example, that an all-wrong attempt yields exactly zero and never a negative total.

---

## 7. Privacy and safeguarding

Pakistan has no enacted comprehensive data-protection statute comparable to GDPR or COPPA. This is frequently read as licence to collect loosely, and it should not be. The absence of a statute is not the absence of obligation: the school's exposure runs through general contract and tort law, through any international sponsor's due diligence, and through its own reputation. The standard is also cheap to adopt voluntarily.

**What the system does not do:**

- It collects no personal data through any web form. There is no signup surface.
- It publishes no full names, no guardian names, no student numbers, and no photographs.
- It publishes no more than a first name and a campus name on any public board.

**What it does do:**

- **Append-only ledger.** Every point a student has ever been awarded is written with a reason, a reference, and a timestamp, and is never updated or deleted. A parent can be shown the complete audit trail for their child. This is a deliberate governance decision, and it should be preserved in any future implementation.
- **Participation board.** Every participant appears on a board, so no student is publicly invisible.
- **Age-neutral presentation.** The public name can be a nickname, which removes the identification problem that a sixteen-campus board creates for small cohorts.

**Before launch:**

1. Obtain parental consent at enrolment, in writing, for participation and for any board publication.
2. Publish a plain-language privacy notice inside the front cover of every notebook.
3. Confirm current ICT Directorate guidance with local counsel.
4. Do not publish photographs of students to social media without separate, explicit, written parental consent — a separate consent from participation.

---

## 8. Data model

Nine tables. Deliberately small, and every one of them is queryable from a school administrator's spreadsheet.

| Table | Purpose |
|---|---|
| `campuses` | The sixteen campuses |
| `classes` | Class and year group, scoped to a campus |
| `students` | Name, display name, guardian name, class, campus, house. Already held in admission records. |
| `access_codes` | The rotatable six-character login code |
| `subjects`, `chapters`, `quizzes` | The curriculum spine, with quiz kind and time limit |
| `questions` | Prompt, options, correct index, explanation, teaching notes |
| `attempts`, `answers` | Per-attempt record including the partial unique index |
| `points_ledger` | Append-only point history — the audit trail |
| `scans` | QR scan events keyed by print batch — the marketing measurement |

The schema is already campus-scoped throughout, so the sixteen-campus leaderboard and per-campus participation reporting are query changes rather than structural work.

---

## 9. The economics: why tuition credit, not cash

The school pays the reward pool out of foregone tuition revenue rather than cash expenditure. This is what makes the scheme affordable, and it is the key to independence from sponsorship.

**Merit bursary.** Up to ten bursaries per month, each worth up to ten per cent of one month's tuition fee, awarded on points earned. Cost to the school: foregone revenue on a student who was already paying. The cost is budgetable, capped, and predictable. We recommend a hard cap of **0.5–1% of annual fee revenue**, published in advance.

**Framing.** The same money must not be described as "students earning their own fees." That framing invites fee-regulation scrutiny, replaces a student election with a leaderboard, and is the kind of sentence that becomes a headline. "Merit bursary, awarded on published criteria" is a programme a school can announce proudly. The budget impact is identical.

**The equity caveat, stated plainly.** A bursary helps a wealthy family more than a poor one, because a wealthy family can absorb the fee. A school serious about this should therefore maintain a small, separately funded **need-based** component alongside the merit pool. The advantage is that this is the easiest CSR money in the sector to raise: "we funded bursaries for students who could not otherwise have continued" is a clean education-access outcome report, and sponsors fund outcomes rather than marketing.

**Where the money should not go.** Physical prizes (laptops, tablets, gear) generate a great deal of excitement and almost no family benefit. Keep one trophy prize per year group for the photo opportunity, and let fee bursaries be the spine of the pool.

---

## 10. The inter-school championship

Every two months, per class group.

A live online final is the obvious design and it is the wrong one. Forty-eight finalists competing live, synchronously, on uneven home connections, with laptops and fee waivers as prizes and no proctoring, will produce at least one cheating incident — and one public incident ends the programme's credibility permanently. It is also the most operationally expensive element in the entire scheme.

The recommended structure:

**Phase 1 — School heat.** Two weeks, asynchronous, in the application. Every student in the class can enter. Identical questions, completed in each student's own time inside the window. No timing pressure, no dropped connections, no proctoring requirement. This is where "represent your school" pride lives, and participation stays near total because anyone can enter.

**Phase 2 — City final.** Sixteen students — one champion per school, per class — compete live over one afternoon. Sixteen people, all on campus, on good connections, with staff in the room. Manageable, and it produces a ceremony worth filming.

The critical inversion is the reward structure: **sixteen school champions, not five finalists.** Every campus produces a genuine winner, which solves the elimination problem that otherwise drains engagement from everyone who is knocked out before the real event. Sixteen PR moments rather than five.

| Place | Reward |
|---|---|
| School champion (×16) | Bursary + trophy + name on the school's banner + a slot in the final |
| City winner, 1st–3rd | Laptop or tablet |
| City 4th–5th | Fee waiver |
| Top school of the term | Inter-school trophy and banner |

**Scheduling.** The championship must avoid examination terms. Published on a fixed calendar so campuses can plan.

---

## 11. The marketing engine

Every printed batch of notebooks carries its own tracked short link:

```
https://<host>/t/{batch}/{subject}   ->   redirects to code entry, records the scan
```

This answers the only marketing question that matters — *which print run of notebooks actually drove engagement?* — and it costs nothing, because the tracking is a redirect. Scans, participation, and average score are attributable per batch, per campus, per subject.

**The single largest lever for a Pakistani rollout is zero-rated data.** Students are on metered mobile connections. If the operator affiliates with the host and exempts its traffic, participation does not improve marginally; it changes order of magnitude. The application is already engineered for it at 2.5 KB per quiz page, which makes this a cheap request with an enormous ceiling. In our assessment this is the most valuable thing an affiliated operator can contribute, and it should be the first thing asked for — ahead of sponsorship.

---

## 12. Sponsorship

Once the programme spans sixteen campuses, the sponsorship conversation changes character.

**What will not sell:** "put your logo on our quiz." This is a marketing sponsorship, and education CSR budgets are overwhelmingly earmarked for scholarships, infrastructure, and teaching materials. It is a different budget line at most corporates, and expect it to be difficult. Institutional brand-safety rules also prohibit many otherwise obvious partners from appearing in a young children's environment, so a tiered menu with an approval policy is necessary from the outset.

**What will sell:** "title sponsor of a sixteen-school academic championship." Sixteen campuses, 2,000+ students, a recurring streamed event, trophies, media coverage, and a clean education-access outcome story.

| Tier | What they buy | Difficulty |
|---|---|---|
| Scholarship fund | "We underwrite N merit bursaries" | Easiest — maps directly to education-access outcomes |
| In-kind prizes | Printers, tablets, connectivity, local vouchers | Very easy — little cash required, highly valuable to a school |
| Named prize | "This month's top scorer wins a [brand] kit" | Moderate |
| Presented by | Title sponsor of the championship ceremony | Moderate |

**Governance constraint:** the programme must run phase 1 with zero sponsors. The bursary model already funds the core. Sponsorship is upside. A programme that only works with a sponsor dies the first time a sponsor does not renew, and the failure mode is that it takes the educational programme down with it.

---

## 13. Measurement

**The one number: monthly participation** — the share of enrolled students who opened at least one chapter this month.

| Participation | Verdict |
|---|---|
| Below 25% | At risk. Stop and fix before scaling. |
| 25–50% | Watch it. |
| Above 50% | On track. Scale. |

Track weekly during phase 1. This single figure overrides every other metric in this paper.

Secondary metrics, each owned by a specific person who can act on it:

| Metric | Question it answers | Owner |
|---|---|---|
| Participation by campus | Which campuses are engaged, and which need a teacher's nudge | Campus principal |
| Scans by print batch | Which notebook run actually worked | Marketing / HQ |
| Average score by chapter | Which chapters the cohort actually struggles with | Subject teacher |
| Share of students above 50% | Whether the programme is lifting the middle or only the top | Head of school |
| Points redeemed | Actual cost against the 0.5–1% cap | Finance |

**The teacher-facing report is not a by-product.** Class-level results and weak-chapter detection are the reason teachers support the programme rather than quietly resenting it, and they are the reason the programme survives past week three. A teacher who is handed a free, live picture of the chapters their own class is weakest in is being given a gift. A teacher who is merely being measured is being given a threat. The same data serves both audiences; the framing is the entire difference.

---

## 14. Rollout

| Phase | Duration | Scope | Exit criterion |
|---|---|---|---|
| **1** | 4–6 weeks | One subject, one chapter, one class, one campus. No sponsors, no ceremony, no bursary. | Participation above 50% among that class. |
| **2** | Months 2–3 | All subjects. Weekly house boards. First bursary actually paid out. Teacher dashboard live. | Participation holds above 50% school-wide. |
| **3** | Months 4–6 | First inter-school championship. Ceremonies, trophies, first sponsorship conversation. | At least one sponsor for the second cycle. |
| **4** | Year 2 | Championship becomes a fixture. All sixteen campuses onboarded. | — |

**There is a kill switch, and it should be used without embarrassment.** If participation is below 50% at the end of phase 1, the correct action is to stop and diagnose, not to scale. Rolling out a weak programme across sixteen campuses is how a good idea dies of poor management rather than poor design, and it burns the teacher goodwill that phase 1 exists to build.

**Teacher adoption is the real cost.** It is not the software. The single most important onboarding step is briefing teachers that this is *for* them, and showing them what they get. A volunteer class teacher, not the most eager head of department, makes the best first cohort.

---

## 15. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Participation collapses after week 6 | **Critical** | Weekly board and monthly bursary. A yearly prize attached to a daily habit is the known failure mode. |
| Teachers view it as surveillance | **Critical** | Lead with the weak-chapter report as a gift to them. Volunteer first cohort. Brief before launch. |
| Cheating incident | High | Classroom-kind questions (§5). Eight laptop winners rather than one. Teacher verification for top awards. |
| Parent objection to points-based incentives | High | Decouple from school roles entirely (§4.3). Merit bursary framing. Publish criteria. |
| Sponsorship not renewed | Medium | Core is bursary-funded. Sponsors are upside, never the business case. |
| Server outage blocks students | Medium | Front office number permanently printed inside every cover, on every screen (§2.6). |
| Data breach | Medium | No personal data is collected. Append-only ledger. Rate-limited, rotatable codes. |
| Laptop prize fails on customs/import or safeguarding | Medium | Prefer a draw among the top ten, or devices sourced locally with a defined usage and monitoring policy. |
| Programme becomes exam-season pressure | Medium | Schedule clear of examination terms. No term-time leaderboard pressure on a single sitting. |
| Student discomfort with public board | Low | Nicknames supported. Participation board ensures visibility. Never only the top board published. |

---

## 16. What is already built

A working student-facing prototype accompanies this paper, with a passing test suite of thirty-three assertions.

- Scan → tracked redirect → code entry → chapter selection → quiz → graded result → rank → leaderboard
- Append-only points ledger with full audit history
- Rank tiers with the five-chapter activity floor and display clamping
- Growth and conditional-gap messaging
- Two question kinds, seeded with example classroom questions
- Zero dependencies: `node:http` and `node:sqlite` only. No package installation, no build step, no vendor, no licences. Deployment is `node server.js` on a single host.
- A participation report keyed to the primary metric, including per-campus participation and per-chapter weak spots

Not yet built, in priority order: **teacher dashboard** (the onboarding and retention lever), **admin console** (question bank, registry, bursary rules), **championship entities**, **sponsor tier management**, **monthly bursary run and disbursement export**, and **NFC** alongside the QR on the cover.

---

## 17. Open questions for the sponsor and the school

1. What is the monthly fee figure per class, so the bursary cap can be set at 0.5–1%?
2. Which subjects are in scope for phase 1, and who volunteers the class?
3. Can the operator zero-rate the quiz host, and what is the process?
4. How are houses currently structured, and do the weekly boards attach to house points or to quiz points?
5. What is the examination calendar, so the championship can be scheduled clear of it?
6. Is there an existing student council process that Quiz Captain should sit alongside?
7. What is the school's current position on publishing student names, and does a nickname-based board satisfy it?

---

*Prepared as a working proposal. Figures, thresholds and prize values are defaults and should be set by the school before commitment.*
