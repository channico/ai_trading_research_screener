# Repository guidance

- Preserve the boundary between deterministic screening and AI explanation: Python code owns calculations, filters, rankings, and timestamps.
- AI output must be grounded in supplied evidence, state uncertainty, and abstain when evidence is missing or conflicting.
- Do not add order placement, autonomous execution, guaranteed predictions, or ungrounded position sizing.
- Never commit credentials, private account data, licensed provider data, or generated local datasets.
- Keep changes linked to Jira project `AITS`, add tests for behavior changes, and update implementation documentation when interfaces or formulas change.
- Keep live backlog status in Jira and private product planning in the separate planning repository.
