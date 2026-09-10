# Mastery Pulse — 10-Minute Pitch Script

**Format:** ~6.5 min narrated through the 4-page deck, ~3 min live demo, ~30 sec close.
Stage directions are in *[brackets]*. Everything else is said aloud — read it as a starting point, not a script to memorize word for word.

Recording tip: screen-record the deck in one continuous take with your mic live, then switch windows to the running app for the demo segment without stopping the recording — one clean file is easier to upload than two clips to stitch.

---

## 0:00 – 0:45 — Open on the gap, not the product

*[Page 1 is on screen. Don't rush the first line — let it land before you move.]*

> Most AI-fluency programs measure one of two things, never both. Either you find out whether someone *learned* something — a course completion, a badge, a self-reported rating — or you find out whether they're *using* anything at all, from an activity dashboard. Nobody's answering the question a practice lead actually cares about: did the training change what someone does at work on Monday.
>
> That gap is what Mastery Pulse is built to close.

---

## 0:45 – 1:45 — The two-sided idea

*[Point at the diagram — Mastery Mesh, the shared skill graph, Adoption Pulse, the feedback loop.]*

> It's one application built from two ideas that share a single skill graph. Mastery Mesh is the front stage — a practitioner picks a certification, gets a personalized learning path built against that exam's *actual* domain weighting, and practices with items that include a trap-reveal mechanic — it doesn't just tell you you're wrong, it shows you the misconception you just fell for, at the exact moment you fell for it.
>
> Adoption Pulse is the back stage — it watches real usage signals, Claude Code activity, commit patterns, to see if that learning is actually showing up in the work. And here's the part that makes it a system instead of two separate tools: the gap Adoption Pulse finds feeds straight back into what the Curriculum Planner recommends next. That loop is the whole point.

---

## 1:45 – 3:45 — Architecture, fast

*[Move to page 2. You have a lot of surface area here — don't read every agent, gesture at the grid and pick three to actually talk about.]*

> Under the hood this is twelve single-purpose agents, not one big prompt trying to do everything. Each one has a typed input, a typed output, and every single call gets logged — so if something goes wrong at 2am, I'm reading a Python function top to bottom, not reverse-engineering a graph.
>
> Three of these are worth calling out. The Certification Advisor is the front door — four questions, and it matches you to a cert across four different providers, Anthropic, AWS, Google Cloud, Microsoft, because this was never meant to be an Anthropic-only tool. The Item-Writer is the one I spent the most personal time on — the trap-reveal copy is the signature pedagogical device in this whole product. And the Correlation Agent is the highest-stakes one in the system, because it's the one deciding whether someone looks like they're not adopting what they learned — get that framing wrong and you've built a surveillance tool, not a coaching tool.
>
> *[Point at the provider chain diagram.]* One more thing worth ten seconds: every agent call runs through a three-tier fallback — NVIDIA Nemotron first for cost, Anthropic Haiku as the paid last resort — with a circuit breaker so a bad NVIDIA outage doesn't cost every user a fifty-second wait on every single call.

---

## 3:45 – 5:15 — Trust, because this touches real people's data

*[Move to page 3.]*

> This handles people's actual skill gaps and performance data, so the access model isn't an afterthought. Three identity types share one session mechanism — a practitioner sees only their own data, an org admin sees their organization, and leadership sees aggregates only, never an individual's raw attempts. A product-admin layer sits above all of that for managing organizations and plans, and it *never* sees an individual practitioner's learning data — full stop, by design, not by convention.
>
> And when someone's deactivated, it's not a flag that a route might forget to check — deleting their session row happens in the same transaction, so their very next request is a 401, automatically, everywhere. There's no path around it.

---

## 5:15 – 6:15 — Where I stayed in the loop

*[Move to page 4.]*

> Last thing before the demo — I built almost all of this with Claude Code, but there's a short list of decisions I made myself, deliberately, because getting them wrong has a real cost. The Certification Advisor's recommendation logic, because a wrong call costs someone an exam fee. The Grader's partial-credit rubric, because that's what silently defines what "correct" means downstream. And the tone of every message a practitioner reads about themselves — because a technically-accurate but demoralizing nudge does real damage to how a tool like this gets received.
>
> Everything else — the routes, the migrations, the test scaffolding — Claude Code owns outright. That split is deliberate, and I'd make the same call again.

---

## 6:15 – 6:30 — Transition

> That's the system. Let me show you what it actually feels like to use.

*[Switch windows to the running app now. Keep talking through the switch so there's no dead air in the recording.]*

---

## 6:30 – 9:30 — Live demo (condensed)

Pick **one** of the two tracks below depending on which audience you're recording for. Track A is the stronger single demo if you only have three minutes — it hits the two most distinctive product moments (cert recommendation and trap-reveal) in one continuous practitioner journey.

### Track A — Practitioner journey (recommended, ~3 min)

| Time | Action | What to say |
|---|---|---|
| 6:30 | Log in as a practitioner (name + email, no password) | "No account setup — name, email, and you're in. Relaunch with the same email later and you're back exactly where you left off." |
| 6:50 | Certifications tab → Get a recommendation → answer the 4 questions | "Four questions. Watch what comes back." |
| 7:20 | Show the recommendation + rationale, accept it | "It's not just a match, it gives me the *why* — and if I'd answered differently, it would've told me the trade-off against the alternative." |
| 7:40 | Skill Radar tab → Regenerate learning path | "This kicks off three agents — profiling, domain scoring, curriculum planning — and it comes back in under 30 seconds." |
| 8:10 | Quiz tab → deliberately pick the trap answer | "Watch this — I'm going to pick the *plausible* wrong answer on purpose." |
| 8:30 | Trap-reveal panel appears | "That's the trap-reveal. It's not just 'wrong' — it names the specific misconception, right when I made it." |
| 8:50 | Answer correctly on the retry, show the score update | "And that answer just moved my actual mastery score, live." |
| 9:10–9:30 | Quick cut to Skill Radar showing the updated score | "One journey, closed loop, under three minutes." |

### Track B — Leadership / admin journey (~3 min, use if the audience is practice leadership)

| Time | Action | What to say |
|---|---|---|
| 6:30 | Log in as admin | "Same landing page — a toggle switches this to the admin path." |
| 6:50 | Admin practitioners list → open one practitioner's activity summary | "This is what an admin sees per practitioner — quiz activity, skill gaps, mock exam scores — read-only, never editable from here." |
| 7:20 | Nudges → Generate categories | "The system looks at aggregate KPI patterns — no names, no individual scores go into this call — and proposes categories worth nudging." |
| 7:50 | Pick a category → Compose message | "It drafts the message, and it self-checks its own tone before I ever see it — I'm reviewing, not writing from scratch." |
| 8:30 | Show the recipient table, uncheck one, send | "I can pull anyone out before it sends — this is a review step, not an autopilot." |
| 9:00 | Observability tab | "And every one of those calls — the recommendation, the grading, this nudge draft — logged here: model used, latency, cost. Nothing runs invisibly." |

*[If you have time for both tracks, Track A end-to-end plus the first two rows of Track B fits in about 4.5 minutes — cut the close down to 15 seconds if you go that route.]*

---

## 9:30 – 10:00 — Close

*[Cut back to your face or the cover slide.]*

> That's Mastery Pulse — a certification-prep tool and an adoption-tracking tool that were never going to be useful sitting apart, built as one closed loop instead. Happy to walk through the codebase, the agent prompts, or the resilience design in more depth whenever it's useful.

---

## Delivery notes

- **Pace:** the slide section is dense — resist the urge to explain every box on page 2. Naming three agents well beats naming twelve badly.
- **Energy:** the trap-reveal moment in the demo is your best "wow" beat — don't undersell it by rushing past it. Let the panel actually animate on screen before you talk over it.
- **If you're short on time:** cut the Track A quiz retry (8:50 row) and go straight from the trap-reveal to the close — you keep the single most distinctive moment and still land under 10 minutes.
- **If you're recording solo with no live audience:** say the transition line at 6:15 out loud anyway — it reads naturally on playback and covers the window-switch cleanly.
