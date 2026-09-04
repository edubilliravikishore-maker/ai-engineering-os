# UI Explorations

Directions drawn on the way to [workroom.html](../workroom.html), and set aside.

Kept on purpose. Repository principles 6 and 7: *experiments should be preserved*,
*failures are knowledge*. Two of these carry ideas worth reviving — see
[DESIGN-DECISIONS.md](../DESIGN-DECISIONS.md#rejected-and-why).

## Opening them

These are **Design Component** files (`.dc.html`), authored for a canvas editor.
They will **not** render correctly by double-clicking — each expects a runtime that
replaces its `<script src="./support.js">` line. Read them as source, or view the
published canvas:

<https://claude.ai/code/artifact/2afb690f-c120-4804-a1c7-977457b16371>

`canvas.json` records how they were laid out and the notes pinned beside them.

## The sequence

| File | Direction | Set aside because |
| :--- | :--- | :--- |
| `01-workshop-line.dc.html` | Four stations in a row; work travels a forward rail, refused work returns on a lower rail | Too literal a production line — but **the return rail is the best idea here**, making "sent back" a built-in road rather than a failure |
| `02-control-room.dc.html` | Dark instrument panels, dense, data-first | Mission control, not an office — but it is **the only one that named the failing rule**, which belongs in the final room once real `RuleResult` values exist |
| `03-cartoon-room.dc.html` | Warm flat room, round characters, top-down | Right warmth, wrong dimension. Cute but static |
| `04-cartoon-rejection.dc.html` | The same room at the moment work is refused | As above |
| `05-cartoon-pieces.dc.html` | Component sheet: characters, desk, message, walk | Superseded, but the piece-by-piece format was the most useful thing for getting feedback |
| `06-blocky-cast.dc.html` | Seven blocky characters, dress code by seniority, seven hairstyles | **Not rejected — adopted.** This is the cast that became the 3D room |

## Not here

**The blueprint floor plan**, the first direction drawn — a top-down architectural
plan where the OS was the building itself. Its source was overwritten during
iteration rather than preserved. Recorded honestly rather than quietly dropped;
it is described in [DESIGN-DECISIONS.md](../DESIGN-DECISIONS.md#rejected-and-why).

**The seeded canvas bundle.** The published editor page is ~2.3 MB, almost all of
it editor code rather than design. The artboards above are its actual content.
