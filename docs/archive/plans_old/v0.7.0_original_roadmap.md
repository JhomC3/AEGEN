# Roadmap v0.7.0: Bulk Ingestion and Smart Decay

**Goal:** Transform AEGEN into a life-long companion by allowing the import of historical data and implementing a human-like memory decay system.

## Phase 1: Bulk Ingestion (The "Life Review")
*   **Tooling**: Implement a specialized ingestion tool for ChatGPT/Claude/WhatsApp exports (.json, .txt, .csv).
*   **The Review Agent**: A specialist task that reads large document sets to extract:
    *   Core values and Med-Term goals.
    *   Relationship dynamics (Support Network mapping).
    *   Key life milestones (Timeline population).
*   **DoD**: User can upload a 1MB chat history and see their profile "populated" with facts they never told MAGI directly.

## Phase 2: Smart Decay (The "Evolving Memory")
*   **Temporal Weighting**: Modify the RRF search algorithm to apply a boost to recent memories.
*   **State vs. Trait Classification**:
    *   **States**: Emotional states ("I'm sad") or context-bound facts. TTL: 24h-7d.
    *   **Traits**: Structural facts ("I have a brother") or core values. Permanence: Indefinite.
*   **Confirmation Loops**: High-confidence inferences from the past that haven't been mentioned in 30 days are flagged for "re-confirmation" by the bot.

## Phase 3: Linguistic Flexibility (Accent Fix)
*   **Soft Adaptation**: Remove the `Matiz Español` forced grammar rules from the `PromptBuilder`.
*   **Mirroring 2.0**: The bot defaults to Neutral Spanish and only adopts regional slang if the user's recent messages (last 10) consistently show a specific regional pattern.
