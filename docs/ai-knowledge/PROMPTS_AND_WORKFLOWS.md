# PROMPTS_AND_WORKFLOWS.md — the prompts and working conventions that produced this project

**Governing rule (PART T of the backup request):**

> "Preserve exact prompts when they are available."

Every prompt referenced here exists as a file in this backup. The originals are
in `session-backup/paste-cache/` (10 files + `INDEX.md`),
`session-backup/prompt-history--D--Thesis.jsonl` (98 entries) and the 15
transcripts in `session-backup/claude-code-transcripts--D--Thesis/`.

---

## 1. There are no custom commands, agents or hooks in this project

`VERIFIED_FACT`, measured 2026-09-18:

| Path | Exists? |
|---|---|
| `D:\Thesis\.claude\commands\` | **No** |
| `D:\Thesis\.claude\agents\` | **No** |
| `D:\Thesis\.claude\hooks\` | **No** |
| `C:\Users\ABN\.claude\commands\` | **No** |
| `C:\Users\ABN\.claude\agents\` | **No** |
| `D:\Thesis\.claude\` actual contents | `settings.local.json`, `skills/` — nothing else |

`INFERENCE`. **The project's entire reusable-prompt surface is: `CLAUDE.md` + four
Skills + hand-pasted phase briefs.** Every slash command, subagent and hook that
exists on this machine belongs to an installed plugin, not to this project. The
20 command files and 27 agent files in `commands-backup/` and `agents-backup/`
are all plugin-provided — see [PLUGINS_INDEX.md](PLUGINS_INDEX.md).

`INFERENCE`. This is good news for migration: there is **no project automation to
port**. The working method is a documented human convention, not tooling.

---

## 2. The founding prompt — verbatim, 552 characters

`VERIFIED_FACT`. The first prompt ever sent in this project, session
`a4cbf1ac`, 2026-08-25 01:15 local / 2026-08-24T21:45:45Z. Recovered verbatim
from `history.jsonl` → `pastedContents[1].content`:

```
قبل از هر کاری این موارد را بررسی کن و فعلاً هیچ فایلی را تغییر نده:

1. CLAUDE.md
2. تمام Skillهای داخل .claude/skills/
3. Proposal
4. Seminar Report
5. تمام Research Corpus موجود در papers/ و سایر پوشه‌های پژوهشی

ابتدا تأیید کن که:
- CLAUDE.md به‌درستی load شده.
- هر چهار Skill شناسایی و قابل استفاده هستند.
- Proposal و Seminar و Research Corpus برایت قابل دسترسی هستند.
- repository فعلی همان پروژه پایان‌نامه است.

سپس فقط یک گزارش کوتاه از وضعیت دسترسی و آماده بودن محیط بده.

هنوز هیچ تحلیل علمی، کدنویسی، تغییر فایل یا اجرای آزمایش انجام نده.
```

Translation:

> Before doing anything, check the following and **do not change any file for
> now**: 1. CLAUDE.md 2. all Skills inside `.claude/skills/` 3. Proposal
> 4. Seminar Report 5. the entire Research Corpus in `papers/` and the other
> research folders.
> First confirm that: CLAUDE.md has loaded correctly; all four Skills are
> detected and usable; the Proposal, Seminar and Research Corpus are accessible
> to you; the current repository is indeed the thesis project.
> Then give only a **short report** on access status and environment readiness.
> **Do not yet perform any scientific analysis, coding, file modification or
> experiment.**

`INFERENCE`. **This prompt establishes the project's founding convention**, and
every later phase brief repeats it: *verify the constitution and the Skills load
before any work; change nothing during an audit; report readiness, then stop.*
A migrating agent should open the same way on the new machine.

---

## 3. The ten phase-launch prompts — `session-backup/paste-cache/`

`DIRECT_OBSERVATION`. All ten are complete files in the backup, with a generated
`INDEX.md`. Opening lines verified by reading each file.

| # | File | Bytes | mtime (local) | Opens with | Launched |
|---|---|---|---|---|---|
| 1 | `533189f9ef5e24b9.txt` | 25 839 | 2026-08-25 01:31 | «تو اکنون وارد Phase 1.5 پروژه می‌شوی: Deep Literature Review.» | Phase 1.5 |
| 2 | `b756702ce4cf597d.txt` | 23 720 | 2026-08-25 01:34 | same sentence, one word changed (`این پروژه`) | Phase 1.5 (re-paste, 3½ min later) |
| 3 | `d82167a562268520.txt` | 17 344 | 2026-08-25 02:14 | «تو اکنون وارد Phase 1.5-B پروژه می‌شوی: Evidence Completion & Deep Verification» | Phase 1.5-B |
| 4 | `09d5e86bcd1f9724.txt` | 25 998 | 2026-08-26 22:22 | «تو اکنون وارد Phase 2 پروژه می‌شوی: # Methodology Review & Scientific Design» | Phase 2 |
| 5 | `911d51a0aada0c7f.txt` | 10 561 | 2026-08-26 23:34 | «ادامه Phase 2 … این session به‌دلیل قطع اینترنت متوقف شد.» | Phase 2 resume |
| 6 | `b39f66e2d8f00629.txt` | 20 417 | 2026-08-27 00:27 | `PHASE 3 — DECISION REVIEW & METHODOLOGY LOCK` | Phase 3 (Persian) |
| 7 | `bd95a48af8c554d8.txt` | 25 375 | 2026-08-29 02:37 | *"een completed."* — head-truncated | Phase 3 rewrite |
| 8 | `f8da334800d189f2.txt` | 26 385 | 2026-08-29 02:58 | `PHASE 3 — DECISION REVIEW, METHODOLOGY LOCK & IMPLEMENTATION GATE` | Phase 3, full English |
| 9 | `d0720659c2ef2862.txt` | 16 004 | 2026-08-29 03:57 | *"ssure control in water distribution networks…"* — head-truncated | methodology inheritance |
| 10 | `d8f25a13d721f88a.txt` | 18 766 | 2026-09-01 22:12 | *"حمایت نکن."* — head-truncated | Phase 4 network re-review |

`DIRECT_OBSERVATION`. Three files (#7, #9, #10) begin mid-sentence. The
paste-cache stores only the portion of a paste above the inline threshold; the
head of each is in the corresponding transcript. Recorded in
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md).

`DIRECT_OBSERVATION`. **Phases 1.5, 1.5-B, 2 and 3 have no report in `docs/`.**
For those four phases these prompt files plus the transcripts are the **only**
surviving specification of what was asked.

---

## 4. The two continuity conventions — quoted verbatim

These are the most reusable artefacts in this document. They are the user's own
answer to the problem of a long research project spanning many interrupted
sessions, and they are what a migrating agent should imitate.

### 4.1 "Resume, NOT Restart" — `911d51a0aada0c7f.txt`, Phase 2 after an internet outage

```
ادامه Phase 2 — Methodology Review را از آخرین وضعیت موجود ادامه بده.

این session به‌دلیل قطع اینترنت متوقف شد. از ابتدا شروع نکن و کارهای قبلی را
تکرار نکن.

==================================================
اصل مهم: Resume, NOT Restart
==================================================

قبل از انجام هر تحلیل جدید:

1. بررسی کن آخرین کاری که در همین session واقعاً انجام شده چیست.
2. آخرین findings، evidenceها، فایل‌های استخراج‌شده و نتایج قابل دسترسی را
   شناسایی کن.
3. مشخص کن دقیقاً در کدام بخش از Phase 2 متوقف شدی.
4. مشخص کن چه بخش‌هایی کامل شده‌اند و چه بخش‌هایی هنوز باقی مانده‌اند.
5. از تکرار کارهای قبلی خودداری کن.

اگر فایل‌های موقت استخراج‌شده در `tmp` یا محل دیگری هنوز وجود دارند، از آن‌ها
استفاده کن.

اگر نتیجه‌ای قبلاً با Evidence تأیید شده، دوباره از صفر بررسی نکن مگر اینکه
دلیل مشخصی برای شک به آن وجود داشته باشد.
```

Translation of the five numbered rules:

> Before any new analysis: (1) determine what was actually last done in this
> session; (2) identify the latest findings, evidence, extracted files and
> accessible results; (3) state exactly where in Phase 2 you stopped; (4) state
> which parts are complete and which remain; (5) **do not repeat earlier work.**
> If extracted temporary files still exist in `tmp` or elsewhere, use them. If a
> result was already confirmed with evidence, do not re-verify it from scratch
> unless there is a specific reason to doubt it.

The same prompt then restates the locked status of prior phases —
`Phase 1 ✅ / Phase 1.5 ✅ / Phase 1.5-B ✅ / Phase 2 ⏸ متوقف‌شده` — and
enumerates what Phase 2 had already read (`CLAUDE.md`,
`methodology-review/SKILL.md`, `research-review/SKILL.md`, Proposal, Seminar,
Research Corpus, the text extraction of 42 sources, the Jowitt & Xu evidence).

### 4.2 "0. ABSOLUTE CONTINUITY RULE" — `bd95a48af8c554d8.txt`, Phase 3

The English formulation of the same idea, verbatim:

```
============================================================
0. ABSOLUTE CONTINUITY RULE
============================================================

DO NOT restart the research from scratch.

DO NOT repeat the full 42-paper literature review.

DO NOT re-read every PDF unless a specific unresolved decision requires
direct verification.

DO NOT reconstruct old findings from memory if a transcript or prior
phase output is available on disk.

First inspect the current repository and available previous-session
transcripts/reports.

Use the previous Phase 1/1.5/1.5-B/2 work as the starting point.

If previous reports are not persisted in docs/, search for the prior
session transcript(s) and recover the relevant prior conclusions.

If any previous conclusion cannot be recovered reliably:
mark it as [NOT RECOVERED]
instead of inventing it.

============================================================
1. FIRST ACTION — ORIENTATION
============================================================

Before making any decision:

1. Read CLAUDE.md.
2. Inspect git status.
3. Inspect the current repository tree.
4. Identify all available prior-phase artifacts.
5. Locate the previous session transcript if necessary.
6. Determine which decisions are already locked and which remain open.
7. Produce a short Resume Check.

The Resume Check must contain:

- Previous phases completed
- Last known completed section
- Current phase
- Available evidence
- Missing evidence
- Locked decisions
- Unresolved decisions
- External verification limitations
- Current git status
```

`INFERENCE`. **`[NOT RECOVERED]` is the user's own invented label for
irrecoverable prior conclusions**, and it is the direct ancestor of the
classification discipline used throughout this backup (`VERIFIED_FACT`,
`ASSUMPTION`, `OPEN_QUESTION`, …) and of `CLAUDE.md` §7. A migrating agent that
cannot recover something must mark it, not invent it.

---

## 5. The standard shape of a phase brief

`INFERENCE`, from reading all ten paste-cache files. Every brief from Phase 1.5
onward follows the same skeleton:

1. **Phase declaration** — «تو اکنون وارد Phase N پروژه می‌شوی: \<title\>»
   ("You are now entering Phase N of the project: …").
2. **Constitution re-assertion** — read `CLAUDE.md` and all four Skills first and
   treat them as the project's binding rules and execution protocols.
3. **Conflict clause** — «اگر بین این دستور و CLAUDE.md یا Skillها تعارضی وجود
   دارد، تعارض را صریحاً گزارش کن و خودسرانه تصمیم نگیر» — *"if there is any
   conflict between this instruction and CLAUDE.md or the Skills, report the
   conflict explicitly and do not decide unilaterally."*
4. **Inherited state** — an explicit list of what earlier phases established.
5. **Numbered sections of work** — typically 15–36 of them.
6. **Explicit prohibitions**, usually in capitals or with «به هیچ عنوان» ("under
   no circumstances").
7. **A deliverables list** with a required verdict (PASS / CONDITIONAL / FAIL).
8. **A labelling requirement** — every conclusion must carry exactly one of a
   fixed set of evidence labels.

`VERIFIED_FACT`. The Phase 6 brief now in force uses exactly this skeleton with
36 numbered sections, and its §35 labels are
`VALIDATED FACT` / `ENGINEERING DECISION` / `RESEARCH ASSUMPTION` /
`HYPOTHESIS TO TEST`, with the instruction «هیچ کدام را با هم مخلوط نکن»
("do not mix any of them together"). See [ROADMAP.md](ROADMAP.md) §2.

---

## 6. What the prompt history actually shows

`VERIFIED_FACT`. `prompt-history--D--Thesis.jsonl` — 98 entries in the backup,
schema `{display, pastedContents, project, sessionId, timestamp}`.

| Category | Count |
|---|---|
| Built-in slash commands | **58** |
| Actual task prompts | **40** |

Slash-command frequency:

| Count | Command |
|---|---|
| 17 | `/effort` |
| 17 | `/resume` |
| 5 | `/model` |
| 5 | `/logout` |
| 3 | `/btw` |
| 3 | `/status` |
| 3 | `/export` |
| 2 | `/rename` |
| 1 each | `/usage`, `/config`, `/login` |

`VERIFIED_FACT`. **Not one `/ars-*` command appears anywhere in the history**
(`grep -c "ars-"` → 0), despite academic-research-skills being the most-loaded
plugin on the machine (214 + 90 loads). Same for any superpowers or
document-skills command. **Every command ever run in this project is a Claude
Code built-in.**

`DIRECT_OBSERVATION`. The 40 task prompts show a heavy **retry pattern**:

- Phase 1.5 pasted **4 times** in 7 minutes (2026-08-24 21:57 → 22:04 UTC).
- Phase 3 pasted **9 times** across 2026-08-28 22:47 → 23:28 UTC, all
  `+1258 lines`.
- The Phase 4 brief («# فاز جدید: بازبینی مستقل و عمیق انتخاب شبکه…») pasted
  **11 times** on 2026-09-01 between 17:42 and 18:42 UTC.
- Six bare `hi` probes interleaved with those retries.

`INFERENCE`. The retries are **not** the user changing their mind — the text is
identical across repeats. They are the signature of failed submissions (the
user's recurring message *"last prompt failed continue from where it is
stopped"*). The `hi` probes are connectivity checks between failures. A
migrating agent should read repeated identical prompts as **one** instruction,
not several.

### 6.1 ⚠ The prompt history stops before Phase 5

`VERIFIED_FACT`. The last **task** prompt in `history.jsonl` for this project is
2026-09-01 22:58 local. Everything after it — 2026-09-06 and 2026-09-18 — is
slash commands only.

`DIRECT_OBSERVATION`. The live `history.jsonl` today holds **100** `D:\Thesis`
entries, two more than the 98 in the backup: `/model` and `/resume` at
2026-09-18 02:50, written by this very session. Both are slash commands, so no
task prompt was lost by the backup being taken earlier.

`OPEN_QUESTION`. **Why the Phase 5, Phase 6 and backup-request briefs are absent
from `history.jsonl` was not determined.** They were unquestionably sent — the
work exists — but they are not in this store. A migrating agent must take them
from the transcript `32df42f5-06e0-4c73-91f0-0a6aea86fc15.jsonl` (12.4 MB) or
from `session-backup/2026-09-06-232706-…txt`, not from the prompt history.
**Do not treat the 40 task prompts as the complete set of instructions given to
this project.**

---

## 7. The Phase 2 background-job launch prompt

`DIRECT_OBSERVATION`. `session-backup/background-job-10b7b88f/timeline.jsonl`
preserves the Phase 2 brief as sent to a background job. Opening, verbatim:

```
تو اکنون وارد Phase 2 پروژه می‌شوی:

# Methodology Review & Scientific Design

هدف این Phase این است که بر اساس:

- Proposal
- Seminar Report
- Research Corpus موجود
- 42 منبع پژوهشی
- یافته‌های Phase 1 Audit
- یافته‌های Phase 1.5 Literature Review
- یافته‌های Phase 1.5-B Evidence Completion
- و ادبیات علمی معتبر و به‌روز در صورت نیاز

یک روش‌شناسی دقیق، علمی، قابل اجرا، قابل تکرار و قابل دفاع برای پروژه طراحی و
ارزیابی کنی.
```

> "…design and evaluate a methodology for the project that is precise,
> scientific, executable, reproducible and defensible."

`INFERENCE`. The five adjectives — دقیق / علمی / قابل اجرا / قابل تکرار / قابل
دفاع — are the same five that reappear in the Phase 6 objective
(«یک محیط DRL دقیق، reproducible، physically meaningful و قابل دفاع»). **This is
the project's standing quality bar, restated in every phase.**

The job's closing state (`state.json` → `detail`) records it finished and waited:

> منتظر دستور بعدی شما هستم. اگر بخواهید، Phase بعدی می‌تواند یکی از این‌ها باشد:
> `novelty-check` مستقل (برای بستن G8 و AD3)، بستن شکاف‌های G1/G3 با خواندن دستی
> صفحات مشخص‌شده، یا نوشتن محتوای این Phase در `docs/` پس از تأیید.

The third option — *"writing this Phase's content into `docs/` after approval"* —
**was never taken**, which is why Phase 2 has no report. See
[MISSING_OR_UNRECOVERABLE.md](MISSING_OR_UNRECOVERABLE.md).

---

## 8. Session-opening ritual, observed across all 15 transcripts

`DIRECT_OBSERVATION`, from `SESSION_INDEX.json` → `first_user_texts`:

| Session | Opens with |
|---|---|
| `a4cbf1ac` | the founding prompt (§2), then the Phase 1.5 brief, then the `research-review` Skill preamble `Base directory for this skill: D:\Thesis\.claude\skills\research-review` |
| `10b7b88f` | `/effort` → *"Set effort level to max (this session only)"*, then the Phase 2 brief |
| `4f550550` | `/effort` → max, then Phase 3 |
| `e48e06b6`, `a49ef45a` | `/effort` → *"Set effort level to low (saved as your default for new sessions)"*, then `hi` |
| `32df42f5` | the Phase 4 brief, then a `<task-notification>` |
| `8677c290`, `38027d6e`, `551c2deb`, `4cbcd32e` | `hi` only |
| `e1b0711e` | `/__remote-workflow` only |

`VERIFIED_FACT`. **The three real working sessions all opened with
`/effort` set to `max`**; the throwaway probe sessions ran at `low`.

`INFERENCE`. The user's working configuration for this project is **Opus at
maximum effort**. A migrating agent should assume the destination harness's
highest reasoning setting is the intended one, not a default.

`DIRECT_OBSERVATION`. Session `a4cbf1ac`'s third `first_user_text` is the
**verbatim body of the `research-review` Skill**, injected as a user turn. That
is the only recorded formal Skill dispatch in the project — consistent with
`skillUsage.research-review.usageCount = 1`. See
[SKILLS_INDEX.md](SKILLS_INDEX.md) §2.1.

---

## 9. Reusable prompt templates for the next agent

`INFERENCE`. Four templates are worth carrying forward, all reconstructible from
files in this backup:

**T1 — Session opening (from §2).** Verify the constitution and Skills load,
confirm access to proposal / seminar / corpus, report readiness, change nothing.

**T2 — Resume after interruption (from §4.1/§4.2).** State what was last actually
done; list completed vs remaining; do not repeat confirmed work; mark
irrecoverable conclusions `[NOT RECOVERED]` rather than inventing them.

**T3 — Phase brief (from §5).** Phase declaration → constitution re-assertion →
conflict clause → inherited state → numbered work sections → explicit
prohibitions → deliverables with a single verdict → evidence labels.

**T4 — Conflict clause (verbatim, reusable as-is):**
«اگر بین این دستور و CLAUDE.md یا Skillها تعارضی وجود دارد، تعارض را صریحاً
گزارش کن و خودسرانه تصمیم نگیر.»
— *"If there is any conflict between this instruction and CLAUDE.md or the
Skills, report the conflict explicitly and do not decide unilaterally."*

`INFERENCE`. T4 is the operational form of `CLAUDE.md` §1's priority hierarchy
(scientific validity > approved scope > project decisions > convenience) and of
its rule *"When scientific validity and the approved documents appear to
conflict, surface the conflict explicitly. Never choose silently."* Preserve it
in whatever instruction file the destination harness reads.

---

## 10. Reading order for prompts

1. `session-backup/paste-cache/INDEX.md`, then the ten `.txt` files in the order
   of §3 — this is the project's instruction history for Phases 1.5 → 4.
2. `session-backup/prompt-history--D--Thesis.jsonl` — the user's own words,
   98 entries, Phases 1–4 only (see §6.1).
3. `session-backup/2026-09-06-232706-…txt` (124 794 B) — human-readable, contains
   a compaction summary no `.jsonl` preserves.
4. `session-backup/claude-code-transcripts--D--Thesis/32df42f5-….jsonl`
   (12.4 MB) — **the only source for the Phase 5, Phase 6 and backup-request
   briefs.** Grep it; do not read it linearly.
