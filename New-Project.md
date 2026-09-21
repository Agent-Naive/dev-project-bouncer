# New Project Checklist

Verify the following before a project is considered set up.
Check the box only when it's true on disk, not "planned."

---

## 1. Directory location & structure

- [ ] Lives at `~/dev-project-<name>/` — lowercase, hyphens, no spaces, no unicode.
- [ ] Has a `docs/` folder. That's where randoms live — loose notes, exports, references.
- [ ] Subfolders only as needed. The top level should be readable at a glance:
  `README.md`, `docs/`, `runlines.md`, and the work itself.

## 2. Project name

- [ ] Follows the `dev-project-<name>` convention. Short, searchable, says what it is.
- [ ] The name describes what the project *does*, not what it might become.
- [ ] No renames after sessions exist inside it — renaming a live project directory
  strands tooling (learned via the GLink → Dropwire cwd trap).

## 3. Ruleset loaded — `docs/SHQL-v1.1b.md`

- [ ] A copy of SHQL-v1.1b.md sits in `docs/`.
- [ ] SHQL is treated as persistently ON: prefix-first parsing, the nine hard-stop
  errors, tag/lock state, and `::@` management commands.
- [ ] DADO means digest-and-discuss-only, and applies to the message containing it.

## 4. `runlines.md` created

- [ ] Every repeated command has a runline: setup, servers, tunnels, tests,
  one-shot jobs. If you typed it twice, it belongs in runlines.
- [ ] Kill runlines are included — how to stop everything cleanly
  (ports, processes, tunnels) without nuking the machine.
- [ ] Runlines are tested, not transcribed. A runline that never ran is a rumor.

## 5. Subagent tagging

- [ ] If subagents are used, they load the *same* tag chain / preset as the
  main session. Define it once (docs or preset file), reference it everywhere.
- [ ] No tag drift: a subagent inventing its own tags is a project with two rulesets.
- [ ] `@effort` is a real knob. `@temperature` / `@context` are not — don't put
  them in a checklist expecting them to do something.

---

## 6. Local git, no remotes *(added)*

- [ ] `git init` locally. No GitHub, no remotes, no push — standing rule.
- [ ] First commit is the scaffold, before real work lands. A repo born mid-project
  has no clean starting point to rewind to.
- [ ] Never `git` from `$HOME` — home is not a project (the Aug 30 worktree incident).

## 7. Secrets never touch the repo *(added)*

- [ ] `.gitignore` covers `.env`, tokens, keys, `GO.live`-style arm files, and logs.
- [ ] Tokens live in a gitignored `.env`, never in chat, docs, filenames, or
  desktop rtfs. (The GH Token.rtf lesson — 2026-09-21.)
- [ ] No real secret is ever pasted where it can be copied, screenshotted, or synced.

## 8. `README.md` states what and why *(added)*

- [ ] One screen: what it is, what it is *not*, hard rules, how to run it.
- [ ] Anyone — including future-you in three months — can orient in 60 seconds.
- [ ] "What it is not" matters: it stops the project from absorbing neighboring ideas.

## 9. Session continuity log *(added)*

- [ ] `HANDOFF-LOG.md` (or `JOBS.md` + `STATUS.md`): what was done, what's next,
  what's blocked, what was deliberately *not* done.
- [ ] Updated at session end, not "later." Later is where context goes to die.
- [ ] Each entry says what changed on disk — filenames, not vibes.

## 10. External-action gates *(added)*

- [ ] Anything that touches the outside world — posts, sends, publishes, spends,
  tunnels — ships with a default-OFF gate.
- [ ] The gate is a real mechanism (unset env var, absent arm file), not a comment
  saying "don't run this yet." Comments don't stop execution.
- [ ] Dry-run path exists and is the default. Live path requires a deliberate,
  logged arming step.

---

*Items 1–5 from the original rtf (2026-09-20). Items 6–10 added 2026-09-21 from
established project patterns (terrarium, harness, corpus, router-judge).*
