# Provenance and AI-assistance disclosure (UQCC-R0)

- Created 2026-10-10 during the Qollab × IonQ build window as a new, separate project by AgentNOMOS Quantum Lab.
- Code written by an AI coding assistant (Claude, Anthropic) under the team's direction, then reviewed by the team owner (review pending).
- Clean-room: no code, data, or private API from AgentNOMOS UVO / ActionGate 2.0 (or related components) or the team's other Qollab projects was accessed or reused. "Claim gate" here is a fresh, minimal implementation; it is NOT the UVO ActionGate 2.0 system.
- Prior work: the team has previously designed scientific-claim-verification concepts (UVO). Those concepts inspired the evidence-class separation; no implementation was carried over.
- External data: bibliographic metadata from the public Crossref REST API and arXiv API, retrieved 2026-10-10 (raw responses in evidence/raw/). Runtime makes no network calls.
- Physics references: see uqcc/sources.json. The circuit follows the network described by Bužek, Braunstein, Hillery & Bruß, Phys. Rev. A 56, 3446 (1997); the preparation angles were derived here and verified numerically.
