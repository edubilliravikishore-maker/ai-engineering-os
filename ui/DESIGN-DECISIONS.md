# UI Design Decisions

Recorded 2026-09-04. The reasoning behind [workroom.html](workroom.html), including
the trade-offs accepted and the directions rejected.

This is a **product and visual** record, not an architecture record. It supersedes
no ADR and decides nothing about the backend.

---

## The governing idea

**The office is the state machine, not a metaphor over it.**

`TASK_STATE_MACHINE` assigns every transition to exactly one initiator — the
Coordinator assigns, the Worker starts and submits, the Reviewer approves or
returns, QA accepts, and `SystemActor.OS` is the *sole* permitted initiator of four
transitions including `CREATED -> READY`. So "which desk is this task on" and
"what state is this task in" are the same question.

Everything below follows from that.

---

## 1. A room, watched from a fixed camera

**Decision.** A 3D room seen from above at an angle, with three fixed camera
positions and no free movement.

**Why.** The first four attempts were flat 2D floor plans. They were legible but
lifeless, and the point of the view is to feel that work is *happening*. Depth and
motion do that; a diagram does not.

**Trade-off.** A fixed camera cannot show everything at once. Accepted: the room
is small, and a camera the viewer can wander with is a camera they can get lost in.

**No dragging.** Deliberate, at the Builder's instruction. Three buttons, each
snapping to a locked position. Free orbit made the view feel unstable.

## 2. Built in CSS 3D, with no library

**Decision.** Every object is a box of five painted faces — top brightest, sides
progressively darker. ~149 boxes, ~710 faces, no dependencies.

**Why.** A library would have to be inlined to run inside a sandboxed page, and it
would add hundreds of kilobytes to draw shapes this simple. The per-face shading is
what makes the boxes read as solid, and that is three CSS filter values.

**Trade-off.** No real lighting, no shadows beyond a soft ellipse under each
person, no models. Accepted — the look is deliberate, not a limitation being hidden.

## 3. Seniority is the dress code

**Decision.** The longer someone has been there, the sharper they dress. Rex wears
a three-piece with a pocket square; Mina a tailored blazer; Ash a knit vest over an
oxford; Juno an all-black turtleneck. The three newest — Bo, Pip, Tam — wear a
hoodie, a denim jacket and a bomber, with chunky sneakers and cargos.

**Why.** It lets the room's seniority be read at a glance without a single label.

**Trade-off.** Role colour moved from the whole body to the tie and the trim, so
the room reads calmer but roles take a moment longer to identify.

## 4. Every hairstyle is different, and that is the important part

**Decision.** Seven distinct silhouettes: swept back with grey temples, a high bun,
a side part, a blunt bob with one red panel, high-top curls, a pulled-down beanie,
a bleached crop.

**Why.** **From directly overhead the tailoring disappears entirely.** Shoulders
and hair are all that remain. So the hair carries the identity, and the suits are
for when you drop the camera to eye level.

This is the single decision most likely to be undone by someone who does not know
why it is there. It is not styling.

## 5. Walking means it mattered; a floating message means it did not

**Decision.** Routine hand-offs appear as a message bubble. Anything that needed a
person — above all a refusal — makes someone stand up and walk across the floor.

**Why.** It gives the room a readable temperature. The amount of walking on screen
tells you how much friction the work is hitting, before you read a word.

## 6. A refusal is warm orange, never alarm red

**Decision.** Returned work is a soft orange, and the bubble explains itself:
*"Not yet — I can't check this. No test run, no API response. Saying it works
isn't showing it."*

**Why.** In this architecture a refusal is the system working correctly, not an
incident. ADR-001 exists so that no agent completes its own work; the UI should
make that feel routine and fair rather than punitive.

## 7. Nothing on screen without an event behind it

**Decision.** Every visible change corresponds to something that would be a real
row in `os_events`. The log panel shows the event type and a rising sequence number.

**Why.** The alternative — decorative motion — would make the room a cartoon of the
system rather than a window onto it. It also keeps the prototype honest about what
the backend must actually provide.

**Consequence.** The sequence numbers in the panel are the same ordering authority
[ADR-006](../adr/ADR-006.md) 6.1 established. When this is wired up, the browser
holds a position and asks "what happened after N?" — the same drain-then-listen
design as ADR-006 6.6, one layer up.

---

## Two bugs worth remembering

**The room sat off-centre.** The world transform ended with
`translate(-450px, -310px)`. The element was already centred by its layout and its
rotations already pivot on its own middle, so that translate did nothing but push
the room half its own size up and to the left.

**Then a subtler one.** Even correctly centred, a *tilted* plane does not project
symmetrically — the near edge fans wider than the far edge, so the visible shape
drifts. It drifts by a different amount at every angle. Each camera preset
therefore carries its own `--ox` / `--oy` correction, solved from the projection
maths rather than nudged by eye.

If a future camera angle is added, **it needs its own offset computed**, or it will
sit off-centre like the first three did.

---

## Rejected, and why

Kept in [explorations/](explorations/README.md).

| Direction | Why not |
| :--- | :--- |
| Blueprint floor plan | Read as an architectural drawing. Correct, cold. *(Source overwritten during iteration — only described here.)* |
| Workshop line | Stations in a row with a return rail for refused work. The return rail was the best idea of the night; the layout was too literal. |
| Control room | Dark instrument panels. Showed *which rule failed by name* — still the most informative thing anyone drew — but it was mission control, not an office. |
| Flat cartoon room | The right warmth, wrong dimension. Cute but static. |

**The one idea worth reviving:** the control room named the failing rule
(`system_evidence_required`, with GIT_DIFF present and TEST_OUTPUT missing). The
current room says *that* work came back but not *which rule* refused it. Once
Checkpoint 6 produces real `RuleResult` values, that detail belongs in the bubble.

---

## Open questions

1. **Should Reviewer and QA get cabins**, or stay on the open floor with the workers?
2. **How does the room behave at scale?** Seven people and four desks is comfortable.
   Forty tasks across twelve workers is not yet designed for.
3. **What does an idle room look like?** Right now something is always happening.
4. **Payload requirements.** Formally: what must each of the thirteen event types
   carry for this room to render it? That is the input ADR-006 6.5 is waiting on.
