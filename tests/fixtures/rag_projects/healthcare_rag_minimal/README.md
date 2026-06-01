# healthcare_rag_minimal

## Reference sources

- https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant
- https://github.com/dmis-lab/RAG2
- Project-owned healthcare readiness fixture pattern.

## Scanner signals

- `config.yaml` contains `medical_domain`, `synthetic_patient_data`, `phi_policy`, `cite_sources_required`, and guardrail settings.
- `docs/synthetic_guideline.md` contains a fake clinical guidance source with `source_id`.
- `docs/fake_patient_note.md` is explicitly marked `SYNTHETIC`.
- `src/guardrails.py` contains `no_diagnosis` and `emergency_escalation` signals.
- `src/citation.py` requires source citations for medical answers.

## Safety notes

- This fixture does not require network, Docker, or external medical systems.
- This fixture does not include real secrets.
- This fixture does not include real patient data, PHI, PII, or clinical records.
- All medical text is synthetic and exists only to test scanner readiness signals.
