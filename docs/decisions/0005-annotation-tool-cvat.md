# 0005 — Annotation tool: CVAT, self-hosted

- **Date:** 2026-09-07
- **Status:** CLOSED (OD-B1)
- **Owner:** Person B (Raghava)
- **Source:** `[Team 2026-09-07]`, Document 4 §2.1, `[PRD 4.7]`

**Decision.** CVAT, self-hosted on KFT infrastructure. Roboflow Universe is retained
as a **download source** for public datasets only.

**Reasoning.** The counter-UAV imagery is KFT-collected for a defence-adjacent
programme; uploading it to a third-party hosted service is a decision that deserves
to be made deliberately, and probably made "no". Choosing hosted now means accepting
that later or migrating mid-project — and this project has already paid twice for
reversals. Secondly, there is no free-tier ceiling to hit at exactly the scale a
small-object dataset needs.

**Trade-offs accepted.** CVAT has **no built-in dataset versioning** — a real loss,
and it lands on OD-B2, which must supply a scheme (DVC, or a manifest plus Git LFS
over the export directory). Self-hosting costs Person B a Docker deployment and
backups. Roboflow's augmentation pipeline is given up; Ultralytics augments at
training time anyway.

**Alternatives considered.** Roboflow hosted — faster start, genuinely good
versioning, third-party data residency, free-tier ceiling.

**Caveat, carried deliberately.** If the CVAT standup turns into a multi-day
yak-shave, annotate the first **public**-data batch in Roboflow's free tier (public
data, no sensitivity) and migrate before any KFT-collected imagery is touched. Do not
let this land on the critical path.
