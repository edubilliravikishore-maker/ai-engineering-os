# Lessons Learned

## Purpose

Record what this project has learned the hard way, so it is not learned twice.

## Lessons

### The navigation files go stale silently, and it costs real time

**What happened.** `brain/Current-Focus.md`, `brain/Project-State.md` and
`docs/05-roadmap/Roadmap.md` sat as empty placeholders from the start of the
project through the end of Checkpoint 4. The code was healthy the entire time —
581 tests passing, lint and types clean — but with no map, returning to the project
meant re-reading a 1,200-line Blueprint and five ADRs to work out the next move.

**The cost.** The Builder's own words on 2026-09-04: *"I feel like I went out of
it."* Not a code problem. A navigation problem, and it nearly stalled the project.

**The rule.** **Update `brain/Project-State.md` at the end of every checkpoint, in
the same commit as the work.** A map that is only sometimes right is worse than no
map, because it is trusted.

### An empty document is invisible; a wrong one is not

The placeholders never triggered a failure, a warning or a test. Nothing pointed at
them. Compare the layer boundaries, which are pinned by tests that fail loudly the
moment they are broken.

**The rule.** Where a document must stay true, pin it with something that breaks.
The Blueprint's `[IMPLEMENTED]` markers and the checkpoint tables have no such pin
and are maintained by discipline alone — treat them accordingly.

### Two authoritative records can quietly contradict each other

Discovered three separate times, each during implementation rather than review:
the Actor table split (ADR-005 5.1), the `work_packages` classification
(ADR-005 5.8), the event-table ownership (ADR-005 5.13), and the `events`/`storage`
dependency cycle the Blueprint §11 file tree required (ADR-006 6.11).

**The rule.** Implementation is where contradictions surface. When one appears, stop
and record an amendment. **Never pick whichever record is more convenient and move
on** — that is how the contradiction became invisible in the first place.

### Deferring a decision is only safe if the shortcuts are closed too

ADR-004 4.15 left the authoritative QA-result mechanism open. ADR-005 5.9 then had
to *forbid* using the persistence timestamps for it, and ADR-006 6.1 had to confirm
`sequence_number` is not a selector either — because both are exactly the right
shape to be pressed into service by someone who does not know the question is open.

**The rule.** When deferring a decision, name the plausible wrong answers and close
them explicitly.

### Design work feeds the backend, not just the front

[ADR-006](../adr/ADR-006.md) 6.5 deferred per-event-type payload schemas on the
grounds that no consumer existed. Designing [the UI](../ui/README.md) produced that
consumer, and with it the actual requirements. Visual work is not a detour from
architecture here — it is an input to a question already parked.
