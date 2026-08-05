# Where You Should Be In The Loop

You said you want to write the key and complex parts yourself and let Claude Code handle the rest. This is the consolidated answer to "which parts are those" — the same flags appear inline in `project_plan.md` at the relevant step, so you don't have to cross-reference while you work. This is a judgment call, not a rule; treat it as a strong default.

The pattern across all nine: **it's almost never "write the Python yourself" — it's "own the prompt file, the rubric, or the policy decision."** Claude Code can write the plumbing around any of these perfectly well. What it can't do is make the judgment call that the plumbing serves.

| Step | What to own | Why it's not a delegation task |
|---|---|---|
| 0.4 Agent framework | Review/tune the base `Agent` class design — retry behavior, how structured-output validation failures are handled, what "success" means in `agent_runs` | Every one of the other seven agents inherits this contract. A wrong call here is a wrong call eight times over, and it's exactly the kind of foundational decision that's genuinely interesting to make yourself rather than delegate. |
| 1.2 Usage-Signal MCP adapter | Decide what actually counts as a meaningful usage signal, and how a Claude Code session or a commit maps to a skill node | This is a modeling judgment, not an engineering one — get it wrong and Adoption Pulse either misses real adoption or flags noise as signal. No amount of clean code fixes a bad mapping rule. |
| 2.4 Item-Writer prompt | The trap-reveal mechanic itself — what makes a good trap, and what the reveal copy says | This is your signature pedagogical device from the CCAF materials. It's also the single most "you" part of this product; delegating the prompt that defines it would hollow out the one thing that makes Mastery Mesh distinctive. |
| 2.5 Grader rubric | The rubric for free-text grading, especially partial-credit logic | Grading rubrics encode what you actually value in an answer. Get this wrong and every downstream skill score is measuring the wrong thing, quietly. |
| 3.2 Correlation Agent | The correlation methodology and the "correlation, not causation" framing in its own output | This is the ethically load-bearing agent in the whole system — it's the one that decides someone looks like they're not adopting what they learned. Worth designing carefully rather than trusting a first-draft prompt. |
| 3.3 Nudge Composer prompt | Tone and wording of anything a real practitioner will read about themselves | Nudges land in someone's inbox. A tone-deaf nudge (or a technically-accurate-but-demoralizing one) does real damage to how this tool is received internally — worth more scrutiny than any other copy in the product. |
| 3.4 Rollup Reporter | The minimum-cohort-size policy before a rollup is shown to leadership | This is a privacy decision with a number attached (`rollups.min_cohort_size_met`). Pick the number deliberately; don't let a default slip in. |
| 4.3 Quiz Runner (trap-reveal UI) | The interaction/animation at the moment of reveal | The mechanic's *effect* on the practitioner lives as much in the UI beat as in the copy. Worth a personal design pass once the plumbing works. |
| 5.2 Auth & access control | Who can see individual-level data vs. only aggregates, before any real usage | Get this wrong before real practitioners are in the system and it's a trust problem, not a bug report. |

## What this deliberately doesn't include

Anything CRUD, any API route, any migration, any frontend layout, any test scaffolding, the MCP server plumbing itself (as opposed to the signal-mapping judgment inside it), and the orchestration workflows (their logic is "call these agents in this order," which is a sequencing decision the plan already makes for you). Claude Code should own all of that outright — flagging it here too would just dilute the list down to the same nine things that actually need you.
