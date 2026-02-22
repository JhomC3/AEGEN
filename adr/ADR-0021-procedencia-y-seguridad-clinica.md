# ADR-0021: Provenance and Clinical Safety Architecture

## Status
Accepted

## Context
As AEGEN evolves towards a clinical tool (Mental Health tool with boundaries), the current memory system was treating all extracted information as equally true. LLM inferences (e.g., "user has all-or-nothing thinking") were being stored alongside explicit facts (e.g., "user lives in Bogotá") without distinction. This created risks of "over-personalization" where errors in extraction could contaminate the assistant's behavior for months.

Additionally, the system lacked explicit clinical guardrails and user-facing privacy controls, which are prerequisites for any therapeutic-style intervention.

## Decision
We implement a **Provenanced Memory and Clinical Safety Layer** based on the following principles:

1.  **Memory Stratification**: All memories in SQLite now carry a `source_type`:
    *   `explicit`: Literal user statements (Highest trust).
    *   `observed`: System-verified behavior (e.g., usage patterns).
    *   `inferred`: LLM interpretations (Must include `confidence` and `evidence`).
2.  **Soft-Delete Pattern**: Use `is_active` instead of physical deletion to allow for audit trails and easy recovery of accidentally "forgotten" data.
3.  **Pydantic Profile Migration**: Move the `UserProfile` from an unvalidated dictionary to a Pydantic model with default values for clinical safety (disclaimers, emergency contacts).
4.  **Implicit to Hypothesis Shift**: The `FactExtractor` is instructed to treat cognitive patterns as hypotheses, not facts.
5.  **Direct User Agency**: Commands like `/privacidad`, `/olvidar`, and `/efimero` give the user direct control over the memory system without relying on natural language requests that might fail.

## Consequences
*   **Trust**: The assistant can now say "I noticed X (which sounds like Y), is that correct?" because it knows what is an inference versus what was explicitly said.
*   **Compliance**: The system is now closer to regulatory standards for health-related data.
*   **Complexity**: Increased schema complexity and the need for a migration engine.
*   **Performance**: RAG queries are slightly heavier due to provenance filtering, but offset by new indexing.
