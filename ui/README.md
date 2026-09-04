# UI

The visual layer of AI Engineering OS: an office you watch from above, where the
work moves between desks and a refused task visibly comes back.

**Status: accepted prototype. Not wired to the backend.** Nothing here imports
from `src/`, and nothing in `src/` imports from here. It is deliberately a
separate world — see [Boundary](#boundary).

---

## Open it

```bash
xdg-open ui/workroom.html
```

It is one self-contained HTML file. No build step, no install, no server, no
dependencies. Open it in a browser and it runs.

Published copy: <https://claude.ai/code/artifact/06b5e5a4-c874-43ff-9e4d-5dd74ae6349f>

## What you are looking at

A room seen from a fixed camera. Two cabins on the left hold the Orchestrator and
the Coordinator; the workers, the Reviewer and QA sit out on the open floor. There
is a coffee corner and a lounge, because a workplace that is only desks reads as a
diagram rather than a place.

Seven characters, each dressed by seniority and each with a different hairstyle.
The hairstyles are load-bearing, not decoration: from directly overhead the
tailoring is invisible and the silhouette of the head is the only thing telling
one person from another.

A loop plays the Foundation v1 password-reset story — Bo submits, Ash refuses it
for missing evidence and **walks it back across the floor**, Bo fixes it, it
passes. The panel bottom-left logs each step against a rising sequence number.

Three camera buttons — Overhead, **Angled** (the default), Eye level. Each snaps
to a fixed position and holds it. There is deliberately no drag.

## Why this shape

The Task lifecycle already assigns every transition to exactly one role: the
Coordinator assigns, the Worker submits, the Reviewer approves or returns, QA
accepts, and the OS itself moves a Task to `READY`. "Which desk is this on" and
"what state is this in" are therefore the same question, so an office is a literal
picture of the state machine rather than a metaphor laid over it.

The rest of the reasoning — every decision and its trade-off — is in
[DESIGN-DECISIONS.md](DESIGN-DECISIONS.md).

## Boundary

| | |
| :--- | :--- |
| **Reads** | Nothing yet. Every event on screen is scripted. |
| **Will read** | `os_events`, over Server-Sent Events, once Checkpoint 7 exposes an API. |
| **Never** | Imports from `src/`, or is imported by it. |

**This prototype cannot go live until Checkpoints 6 and 7 land.** Checkpoint 5
built the event stream it will eventually read; Checkpoint 6 builds the Kernel
that writes to it; Checkpoint 7 exposes the API a browser can reach.

**It is still useful now.** [ADR-006](../adr/ADR-006.md) 6.5 deliberately left the
event payload unconstrained, on the grounds that the components which would read
it did not exist. This is that reader. Working out what the room must show is how
the payload requirements get discovered.

## Files

| Path | What it is |
| :--- | :--- |
| `workroom.html` | The accepted prototype. Pure CSS 3D — no library. |
| `DESIGN-DECISIONS.md` | Every decision made, with its trade-off. |
| `explorations/` | The rejected directions, kept on purpose. |

## Related

- [DESIGN-DECISIONS.md](DESIGN-DECISIONS.md) — why it looks like this
- [explorations/](explorations/README.md) — what was tried and set aside
- [brain/Current-Focus.md](../brain/Current-Focus.md) — what the project is doing next
