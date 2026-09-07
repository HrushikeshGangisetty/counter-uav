# pod_contracts

**Owner:** Person A · **Not one of the seven PRD modules** — see
[decision 0015](../../docs/decisions/0015-shared-contracts-package.md).

Every cross-module data structure, defined exactly once. Stdlib only; imports no
`pod_*` module, so every module can safely depend on it.

- Full registry with owners, producers, consumers, units and timestamp/sequence
  semantics: [`docs/contracts.md`](../../docs/contracts.md).
- Detection message schema v1.0 is frozen —
  [decision 0008](../../docs/decisions/0008-detection-message-schema-v1.md).

**Adding a message:** define it here, add it to `CROSS_MODULE_MESSAGES`, add it to
`docs/contracts.md`, bump `CONTRACT_VERSION`, get review from all three owners.
