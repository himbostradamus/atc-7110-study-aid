# Chapter Content Remediation Assignment

You are the sole remediation reviewer for one chapter of an FAA JO 7110.65
study platform. Review the complete assigned chapter packet and propose precise
corrections to the assigned questions, flashcards, and activities.

Follow:

```text
docs/content-remediation-agent-harness.md
```

Non-negotiable constraints:

- Work only on the assigned chapter.
- Do not launch subagents.
- Do not create task lists or spend context narrating a future manifest. Review
  the bounded packet, decide interventions, and write the manifest promptly.
- Do not use image-generation tools or any external model/API.
- Do not browse the web; the packet is the source record for this pass.
- Do not edit live curriculum, databases, frontend code, or repair scripts.
- Do not overwrite another pass or another chapter's files.
- Review every target ID and include complete coverage in `reviewed_item_ids`.
- Write changed-item decisions only. Do not produce redundant keep decisions.
- Use only `minor`, `major`, or `blocker` for decision severity.
- Do not replace an item solely to reorder its choices. Runtime order is shuffled.
- Do not invent explanatory rationales that are absent from the source blocks.
- A validator error for unsupported rationale requires correction unless the
  source basis is expanded with the explicit supporting source statement. Do
  not merely add an inferred rationale to `source_basis`.
- Replacement explanations must state the operating requirement directly. Do
  not write explanations that lean on document-location scaffolding such as
  "the paragraph says," "this section requires," "per paragraph X," or "the
  source states."
- Inspect each activity's full content object; activity types use different fields.
- Finish the full chapter before setting `status` to `complete`.

Read the packet's `audit_findings` and each item's `automated_flags`, but do not
treat heuristics as truth. Independently determine whether the item is correct,
self-contained, educationally coherent, and appropriate for its format.

Use rote memorization where exact phraseology, readbacks, minima, codes,
sequences, or defined terms require exact recall. Otherwise prioritize applying
the rule, recognizing its conditions and exceptions, and choosing the proper
operational action.

The Markdown summary must state:

- overall chapter quality;
- recurring defects and strengths;
- counts of replacements, removals, and splits by format;
- concrete guidance for the later content-generation pass.

The orchestrator validates the manifest after you write it. Do not run shell
commands or validators yourself.
