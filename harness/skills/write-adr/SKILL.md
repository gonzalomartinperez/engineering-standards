---
name: write-adr
description: "Writes a MADR 4 architecture decision record from a decision, with options, consequences and a Confirmation section, and links it from the docs. Use when a decision changes structure, a contract, a dependency, a standard or a policy, or when asked to \"record this decision\", even if the change is small. Not for meeting notes or for changelog entries."
allowed-tools: Read, Grep, Glob, Edit, Write
metadata:
  owner: gonzalomartinperez
  last-reviewed: "2026-11-14"
  version: "1.0.0"
---

# write-adr

Catalog skeleton from engineering-standards (ecosystem 15.5). Repositories copy it to
`.agents/skills/write-adr/`, link `.claude/skills/write-adr` to it, and tune the commands to their stack.

## Checklist

- [ ] Inputs read (AGENTS.md, the item or diff in scope)
- [ ] Procedure followed with the repository's own commands
- [ ] Evidence collected for every claim
- [ ] Output delivered in the template below

## Procedure

1. Find the next number in `docs/decisions/` and the ADRs this one relates to or supersedes.
2. Write `NNNN-title.md` in MADR 4: context and problem, decision drivers, considered options, decision outcome, consequences, Confirmation (how compliance is checked).
3. Link both ways when superseding; update the docs map or README Documentation section.

## Feedback loop

Verify (run the check) → fix → re-verify. Stop after three failed attempts and report the blocker with evidence.

## Output template

The ADR path and the links added.
