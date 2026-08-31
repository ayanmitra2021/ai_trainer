# Data Flow

## Overview
Data enters the system through three channels: (1) practitioner interactions via the frontend REST API, (2) admin-triggered LLM workflows, and (3) nightly MCP signal ingestion from Claude Code sessions and git commits. Data flows through the agent layer (LLM calls) and persists to PostgreSQL. The nudge pipeline is intentionally gated — no nudge is sent without human approval.

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph "Inbound"
        FE_USER[Frontend<br/>Practitioner UI]
        FE_ADMIN[Frontend<br/>Admin UI]
        MCP_SIG[MCP Servers<br/>Claude Code / git signals]
        ADMIN_TRIGGER[Admin<br/>Cert refresh trigger]
    end

    subgraph "API Gateway"
        AUTH_MW{Session Cookie<br/>Auth Guard}
        FASTAPI[FastAPI Router<br/>/api/v1/*]
    end

    subgraph "Workflow Orchestration"
        WF_CERT[recommend_certification<br/>workflow]
        WF_PATH[generate_learning_path<br/>workflow]
        WF_PULSE[nightly_pulse<br/>workflow]
        WF_DOMAIN[domain_refresh<br/>workflow]
    end

    subgraph "Agent Chain"
        CERT_ADV[CertificationAdvisor]
        CURR_PLAN[CurriculumPlanner]
        ITEM_WRITE[ItemWriter]
        QUIZ_GEN[QuizBatchGenerator]
        GRADER[Grader]
        DOMAIN_SCOR[DomainScorer]
        SKILL_PROF[SkillProfiler]
        USAGE_SIG[UsageSignal]
        CORR[CorrelationAgent]
        NUDGE_COMP[NudgeComposer]
        CERT_DISC[CertDomainDiscovery]
    end

    subgraph "LLM Tier"
        MULTI_TIER[MultiTierModelClient<br/>Ultra → Lightning → Haiku]
    end

    subgraph "Storage"
        PG[(PostgreSQL)]
    end

    subgraph "Delivery"
        NUDGE_INBOX[Nudge Inbox<br/>in-app]
        HUMAN_REVIEW{Human<br/>Approval Gate}
    end

    FE_USER --> AUTH_MW --> FASTAPI
    FE_ADMIN --> AUTH_MW --> FASTAPI
    FASTAPI -->|practitioner login / profile| PG
    FASTAPI -->|start cert recommendation| WF_CERT
    FASTAPI -->|start learning path| WF_PATH
    FASTAPI -->|submit quiz attempt| GRADER

    MCP_SIG --> USAGE_SIG
    ADMIN_TRIGGER --> WF_DOMAIN

    WF_CERT --> CERT_ADV --> MULTI_TIER
    CERT_ADV -->|cert goal written| PG

    WF_PATH --> CURR_PLAN --> MULTI_TIER
    CURR_PLAN -->|learning_path written| PG
    WF_PATH --> ITEM_WRITE --> MULTI_TIER
    ITEM_WRITE -->|items written| PG

    WF_PULSE --> USAGE_SIG --> MULTI_TIER
    USAGE_SIG -->|usage_events written| PG
    WF_PULSE --> SKILL_PROF --> MULTI_TIER
    SKILL_PROF -->|skill_profile_snapshots upserted| PG
    WF_PULSE --> CORR --> MULTI_TIER
    CORR -->|correlation_snapshots written| PG
    WF_PULSE --> NUDGE_COMP --> MULTI_TIER
    NUDGE_COMP -->|nudge drafted| PG

    GRADER --> MULTI_TIER
    GRADER -->|attempt written, domain score updated| PG

    WF_DOMAIN --> CERT_DISC --> MULTI_TIER
    CERT_DISC -->|domain_proposal written| PG
    PG -->|admin approves proposal| DOMAIN_SCOR
    DOMAIN_SCOR -->|domain_scores written| PG

    QUIZ_GEN --> MULTI_TIER
    QUIZ_GEN -->|batch items written| PG

    PG -->|drafted nudges| HUMAN_REVIEW
    HUMAN_REVIEW -->|approved| NUDGE_INBOX

    MULTI_TIER -->|Structured Output| CERT_ADV & CURR_PLAN & ITEM_WRITE & GRADER
    MULTI_TIER -->|Structured Output| DOMAIN_SCOR & SKILL_PROF & USAGE_SIG & CORR & NUDGE_COMP & CERT_DISC
```

## Data Pipelines

| Pipeline | Source | Processing | Destination |
|----------|--------|-----------|-------------|
| Cert Recommendation | Practitioner questionnaire | CertificationAdvisor (LLM) | `practitioner_certification_goals` |
| Learning Path | Cert goal + skill snapshot | CurriculumPlanner (LLM) | `learning_paths`, `learning_path_items` |
| Quiz Items | Skill + cert domain | ItemWriter / QuizBatchGenerator (LLM) | `items` |
| Attempt Grading | Practitioner response | Grader (LLM) | `attempts`, `skill_profile_events`, `certification_domain_scores` |
| Nightly Pulse | MCP signals (Claude Code / git) | UsageSignal → SkillProfiler → CorrelationAgent → NudgeComposer | `usage_events`, `skill_profile_snapshots`, `correlation_snapshots`, `nudges` |
| Domain Refresh | Admin trigger → CertDomainDiscovery | Proposal review → DomainScorer | `certification_domain_proposals`, `certification_domain_versions`, `certification_domain_scores` |
| Mock Exams | Practitioner starts session | MockExamGenerator (LLM) | `mock_exam_sessions`, `mock_exam_questions` |
| Byte-sized Lessons | Practitioner requests | ByteSizedLessonAgent (LLM) | `byte_sized_lessons` |

## Integration Points

- **Inbound:** Frontend REST calls (cookie-authenticated), MCP stdio servers (local process)
- **Outbound:** Anthropic API (structured output), NVIDIA NIM API (OpenAI-compatible endpoint)
- **Internal async:** `asyncio.wait_for` timeouts between tier hops in MultiTierModelClient
- **Human gate:** Nudge approval (drafted → approved → sent) — no auto-send
- **Admin gate:** Domain proposal review (pending_review → approved/rejected)
