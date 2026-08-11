"""Certification exam domains seed data — Phase 10.1 bootstrap (updated Phase 10.2).

Usage (called automatically from seed.generate):
    from seed.certification_domains import seed_certification_domains
    await seed_certification_domains(session)

This module is the **bootstrap seed** — it populates the first version of exam
domain data for every active certification.  All ten certifications have been
verified against their official exam guide PDFs (see inline # Source: comments).

Phase 10.2 versioning strategy:
    From Step 10.2 onward every domain row belongs to a
    ``CertificationDomainVersion`` record (version_label = BOOTSTRAP_VERSION_LABEL
    on first run).  A practitioner profile's ``domain_version_id`` is frozen at
    lock time, so admin refreshes never retroactively shift existing scores.

    This seeder is idempotent under versioning:
    - If a bootstrap version already exists for a cert, it is reused.
    - Domain rows are only inserted if none yet exist for that (cert, version).
    - Existing domain rows are NEVER deleted — profiles may reference them via
      their frozen ``domain_version_id``.

⚠️  KEEPING DATA CURRENT:
    From Step 10.3 onward the Cert Domain Discovery Agent handles refreshes —
    no need to edit this file when an exam is revised.  For the period between
    Step 10.1 and Step 10.3, re-run verification manually if a cert's
    ``last_verified_at`` is more than 3 months old.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Certification, CertificationDomain, CertificationDomainVersion

# The version label applied to every domain row created by this seeder.
# The Step 10.2 migration imports this constant when it creates the bootstrap
# certification_domain_versions row — do not change the value without also
# updating the 013_domain_versioning migration.
BOOTSTRAP_VERSION_LABEL = "bootstrap-step-10.1"

_BOOTSTRAP_SOURCE_NOTES = (
    "Bootstrap seed from Phase 10.1 certification exam guides.  "
    "Verified against official exam guide PDFs at Step 10.1 time."
)


# ── Domain definitions ────────────────────────────────────────────────────────
# Each entry is keyed by certification code.
# weight_pct values must sum to 100 per cert (±1 rounding allowed).
# All entries have been verified against the official exam guide for each cert
# (see inline # Source: comments).  Use BOOTSTRAP_VERSION_LABEL as the version
# label when Step 10.2 creates the certification_domain_versions rows.

DOMAINS_BY_CERT_CODE: dict[str, list[dict]] = {
    # ── AWS Certified AI Practitioner (AIF-C01) ────────────────────────────
    # Source: AWS Certified AI Practitioner Exam Guide (AIF-C01), verified
    # from https://aws.amazon.com/certification/certified-ai-practitioner/
    "AIF-C01": [
        {
            "sequence_order": 1,
            "domain_name": "Fundamentals of AI and ML",
            "domain_description": (
                "Basic concepts of artificial intelligence and machine learning: "
                "AI/ML terminology, supervised vs. unsupervised learning, model "
                "training concepts, overfitting/underfitting, common ML use cases, "
                "and when to apply ML vs. rule-based systems."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 2,
            "domain_name": "Fundamentals of Generative AI",
            "domain_description": (
                "Core concepts of generative AI: foundation models, large language "
                "models (LLMs), tokenisation, embeddings, prompt engineering basics, "
                "retrieval-augmented generation (RAG), fine-tuning concepts, and the "
                "AWS generative AI service landscape (Amazon Bedrock, Titan)."
            ),
            "weight_pct": 24,
        },
        {
            "sequence_order": 3,
            "domain_name": "Applications of Foundation Models",
            "domain_description": (
                "Practical use of foundation models: selecting appropriate models for "
                "tasks, prompt engineering techniques (zero-shot, few-shot, chain-of-"
                "thought), model customisation methods, building RAG pipelines, "
                "integrating foundation models into applications using Amazon Bedrock "
                "and the Bedrock Knowledge Bases service."
            ),
            "weight_pct": 28,
        },
        {
            "sequence_order": 4,
            "domain_name": "Guidelines for Responsible AI",
            "domain_description": (
                "Responsible AI principles and practices: bias detection and "
                "mitigation, fairness, explainability, model transparency, dataset "
                "limitations, hallucination in LLMs, and AWS tools for responsible AI "
                "(Amazon SageMaker Clarify, Model Cards)."
            ),
            "weight_pct": 14,
        },
        {
            "sequence_order": 5,
            "domain_name": "Security, Compliance, and Governance for AI Solutions",
            "domain_description": (
                "Security and governance for AI workloads: data privacy, model "
                "intellectual property, regulatory compliance considerations, AWS "
                "shared responsibility model applied to AI, securing training data "
                "and model artefacts, identity and access management for AI services."
            ),
            "weight_pct": 14,
        },
    ],

    # ── Claude Certified Associate – Foundations (CCAO-F) ─────────────────
    # Source: Anthropic Claude Partner Network exam guide (CCAO-F).
    "CCAO-F": [
        {
            "sequence_order": 1,
            "domain_name": "Introduction to AI and Claude",
            "domain_description": (
                "Core concepts of large language models and Claude's place in the AI "
                "landscape: how Claude works at a high level, the Anthropic safety "
                "mission, key Claude capabilities (analysis, writing, coding, reasoning), "
                "model families (Haiku / Sonnet / Opus), and how to access Claude "
                "through the API and consumer products."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 2,
            "domain_name": "Prompt Engineering Fundamentals",
            "domain_description": (
                "Writing effective prompts: system prompts, user messages, context "
                "provision, tone and format specification, zero-shot and few-shot "
                "techniques, prompt structure best practices, common failure modes "
                "(hallucination, refusals), and iterative prompt improvement."
            ),
            "weight_pct": 25,
        },
        {
            "sequence_order": 3,
            "domain_name": "Claude API and Tool Use Essentials",
            "domain_description": (
                "Practical API usage: authentication, the Messages endpoint, "
                "conversation history management, tool use / function calling basics, "
                "streaming responses, token counting, and context window management "
                "— focused on the concepts a non-developer practitioner needs to "
                "understand, not deep implementation."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 4,
            "domain_name": "Responsible AI and Safety",
            "domain_description": (
                "Anthropic's approach to AI safety: Constitutional AI, RLHF, harm "
                "avoidance policies, usage policies, topics Claude declines to assist "
                "with, how to handle Claude refusals gracefully, bias awareness, and "
                "ethical considerations when deploying AI in business contexts."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 5,
            "domain_name": "Deploying Claude in Practice",
            "domain_description": (
                "Practical deployment considerations: use-case selection and "
                "feasibility, integrating Claude into business workflows, evaluating "
                "Claude outputs for quality and accuracy, cost considerations, "
                "monitoring and iterating on Claude-powered features, and common "
                "deployment anti-patterns to avoid."
            ),
            "weight_pct": 15,
        },
    ],

    # ── Claude Certified Developer – Foundations (CCDV-F) ─────────────────
    # Source: Anthropic Claude Partner Network exam guide (CCDV-F).
    "CCDV-F": [
        {
            "sequence_order": 1,
            "domain_name": "Claude API and SDK Essentials",
            "domain_description": (
                "Core API mechanics: authentication, the Messages API endpoint, "
                "model selection, request/response structure, streaming, error "
                "handling, rate limits, the Python and TypeScript SDK, and "
                "practical token budget management with the context window."
            ),
            "weight_pct": 25,
        },
        {
            "sequence_order": 2,
            "domain_name": "Advanced Prompt Engineering",
            "domain_description": (
                "Developer-level prompt techniques: system prompt design, multi-turn "
                "conversation construction, chain-of-thought prompting, XML tagging "
                "for structure, few-shot examples in code contexts, prompt caching "
                "for cost and latency optimisation, and debugging common prompt "
                "failure modes."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 3,
            "domain_name": "Tool Use and Function Calling",
            "domain_description": (
                "Implementing tool use: defining tools with JSON schema, handling "
                "tool_use and tool_result message blocks, multi-tool workflows, "
                "parallel vs. sequential tool calls, strict schema validation, "
                "testing tool integrations, and common pitfalls in tool-use loops."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 4,
            "domain_name": "Building and Testing Production Applications",
            "domain_description": (
                "Production engineering practices: structured outputs via Pydantic / "
                "JSON Schema, error handling and retry strategies, async patterns, "
                "prompt injection prevention, secrets management, writing testable "
                "Claude integrations, and CI practices for LLM-backed services."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 5,
            "domain_name": "Evaluation and Monitoring",
            "domain_description": (
                "Measuring and maintaining quality: defining success criteria for "
                "LLM outputs, building evaluation datasets, automated grading "
                "approaches, latency and cost monitoring, model drift detection, "
                "and iterating on prompts with production feedback."
            ),
            "weight_pct": 15,
        },
    ],

    # ── Claude Certified Architect – Foundations (CCAF) ───────────────────
    # Source: Anthropic Claude Partner Network exam guide (CCAF).
    "CCAF": [
        {
            "sequence_order": 1,
            "domain_name": "System Design with Claude",
            "domain_description": (
                "Architecture patterns for Claude-powered systems: choosing between "
                "single-model and multi-model designs, context engineering at scale, "
                "prompt management strategies, abstraction layers, latency vs. quality "
                "trade-offs, and how to structure Claude integrations in larger "
                "service-oriented architectures."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 2,
            "domain_name": "Multi-Agent and Agentic Architectures",
            "domain_description": (
                "Designing agentic systems: orchestrator/subagent patterns, agent "
                "communication protocols, MCP (Model Context Protocol) server design "
                "and consumption, tool-use strategy in multi-step pipelines, "
                "managing agent memory and state, failure recovery, and when to "
                "choose agentic vs. single-turn approaches."
            ),
            "weight_pct": 25,
        },
        {
            "sequence_order": 3,
            "domain_name": "RAG and Knowledge Integration",
            "domain_description": (
                "Retrieval-augmented generation architecture: vector store selection, "
                "chunking and embedding strategies, retrieval quality tuning, hybrid "
                "search approaches, knowledge freshness, citation and grounding "
                "techniques, and integrating external knowledge bases with Claude's "
                "context window efficiently."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 4,
            "domain_name": "Production Architecture Patterns",
            "domain_description": (
                "Running Claude in production: observability (tracing, cost tracking, "
                "latency monitoring), caching strategies (prompt cache, semantic "
                "cache), horizontal scaling patterns, graceful degradation, "
                "cost optimisation levers (model tiering, batching), and integrating "
                "with cloud infrastructure and CI/CD pipelines."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 5,
            "domain_name": "Safety Engineering and Responsible Design",
            "domain_description": (
                "Safety by design: threat modelling for LLM systems (prompt injection, "
                "data exfiltration risks), output validation architectures, guardrails "
                "and content filters, PII handling, access control for AI features, "
                "audit logging, and embedding responsible AI principles into "
                "architecture decisions rather than adding them as afterthoughts."
            ),
            "weight_pct": 15,
        },
    ],

    # ── Claude Certified Architect – Professional (CCAR-P) ────────────────
    # Source: Anthropic Claude Partner Network exam guide (CCAR-P).
    "CCAR-P": [
        {
            "sequence_order": 1,
            "domain_name": "Advanced Agentic Systems at Scale",
            "domain_description": (
                "Complex multi-agent architectures for enterprise scale: long-running "
                "agent workflows, hierarchical orchestration, inter-agent trust and "
                "authentication, shared memory architectures, consensus and conflict "
                "resolution between agents, and production debugging of distributed "
                "agentic pipelines."
            ),
            "weight_pct": 25,
        },
        {
            "sequence_order": 2,
            "domain_name": "Enterprise Integration Patterns",
            "domain_description": (
                "Integrating Claude into enterprise environments: SSO and identity "
                "federation for AI services, enterprise data governance, connecting "
                "to legacy systems via MCP adapters, event-driven architectures, "
                "async job queues for long-running inference, and managing multiple "
                "Claude deployments across business units."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 3,
            "domain_name": "Safety Engineering and Risk Management",
            "domain_description": (
                "Advanced safety architecture: red-teaming methodologies, adversarial "
                "robustness, model behaviour contracts, anomaly detection in LLM "
                "outputs, incident response procedures for AI failures, regulatory "
                "and compliance risk mapping, and privacy-by-design for AI systems "
                "handling sensitive data."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 4,
            "domain_name": "Performance Optimization and Cost Control",
            "domain_description": (
                "Maximising efficiency at scale: token cost modelling, prompt "
                "compression techniques, dynamic model routing (Haiku for simple "
                "tasks, Opus for complex reasoning), cache hit rate optimisation, "
                "batching strategies using the Message Batches API, and building "
                "FinOps practices around LLM spend."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 5,
            "domain_name": "Multi-Provider and Platform Strategies",
            "domain_description": (
                "Operating across AI providers: abstraction layers for provider "
                "portability, provider comparison frameworks, fallback and failover "
                "strategies, evaluating model capabilities for specific tasks, "
                "managing vendor lock-in risk, and governance of multi-provider AI "
                "deployments."
            ),
            "weight_pct": 15,
        },
    ],

    # ── Microsoft Azure AI Fundamentals (AI-900) ──────────────────────────
    # Source: Microsoft Learn exam guide for AI-900.
    # Weights are representative midpoints of the published ranges
    # (ranges: 15–20%, 20–25%, 15–20%, 15–20%, 15–20%).
    "AI-900": [
        {
            "sequence_order": 1,
            "domain_name": "AI Workloads and Considerations",
            "domain_description": (
                "Identifying common AI workload types and their appropriate uses: "
                "prediction, classification, clustering, anomaly detection, NLP, "
                "computer vision, and generative AI.  Responsible AI principles "
                "(fairness, reliability, privacy, inclusiveness, transparency, "
                "accountability) and their application in Microsoft's framework."
            ),
            "weight_pct": 18,
        },
        {
            "sequence_order": 2,
            "domain_name": "Machine Learning in Azure",
            "domain_description": (
                "Core ML concepts and Azure ML tooling: supervised vs. unsupervised "
                "learning, regression vs. classification, model training and "
                "evaluation metrics, Azure Machine Learning studio, automated ML "
                "(AutoML), and the Azure ML designer for low-code model training."
            ),
            "weight_pct": 22,
        },
        {
            "sequence_order": 3,
            "domain_name": "Computer Vision Workloads",
            "domain_description": (
                "Azure computer vision services: Azure AI Vision (image analysis, "
                "object detection, OCR), Azure AI Face service, Azure AI Custom "
                "Vision for training domain-specific image classifiers, and common "
                "use cases for computer vision in business applications."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 4,
            "domain_name": "Natural Language Processing Workloads",
            "domain_description": (
                "Azure NLP services: Azure AI Language (text analytics, sentiment "
                "analysis, key phrase extraction, named entity recognition, language "
                "detection), Azure AI Translator, Azure AI Speech (speech-to-text, "
                "text-to-speech), and the Azure AI Bot Service for conversational AI."
            ),
            "weight_pct": 20,
        },
        {
            "sequence_order": 5,
            "domain_name": "Generative AI Workloads",
            "domain_description": (
                "Generative AI fundamentals on Azure: large language models, "
                "Azure OpenAI Service capabilities (GPT, DALL-E, Codex), prompt "
                "engineering basics, Copilot products and the Microsoft Copilot "
                "ecosystem, and responsible considerations specific to generative AI "
                "(grounding, hallucination, content safety)."
            ),
            "weight_pct": 20,
        },
    ],

    # ── Microsoft Azure AI Engineer Associate (AI-102) ────────────────────
    # Source: Microsoft Learn exam guide for AI-102.
    # Weights are representative values within published ranges
    # (ranges: 15–20%, 10–15%, 15–20%, 30–35%, 10–15%, 10–15%).
    "AI-102": [
        {
            "sequence_order": 1,
            "domain_name": "Plan and Manage an Azure AI Solution",
            "domain_description": (
                "Solution architecture and governance for Azure AI: selecting "
                "appropriate Azure AI services for a scenario, planning compute and "
                "storage resources, configuring Azure AI services, securing AI "
                "solutions (keys, managed identities, network restrictions), "
                "monitoring costs and usage, and deploying containerised AI services."
            ),
            "weight_pct": 16,
        },
        {
            "sequence_order": 2,
            "domain_name": "Implement Content Moderation Solutions",
            "domain_description": (
                "Azure AI Content Safety: detecting harmful content (violence, hate, "
                "self-harm, sexual content), configuring severity thresholds, "
                "building content moderation pipelines, and integrating content "
                "safety checks into applications and Azure OpenAI deployments."
            ),
            "weight_pct": 12,
        },
        {
            "sequence_order": 3,
            "domain_name": "Implement Computer Vision Solutions",
            "domain_description": (
                "Building computer vision applications with Azure AI: image analysis "
                "and classification, object detection, OCR and document intelligence, "
                "Face API for face detection and verification, Custom Vision for "
                "domain-specific models, and Video Indexer for video analysis."
            ),
            "weight_pct": 16,
        },
        {
            "sequence_order": 4,
            "domain_name": "Implement NLP Solutions",
            "domain_description": (
                "NLP engineering with Azure AI Language: building CLU (conversational "
                "language understanding) models, named entity recognition, "
                "sentiment analysis and opinion mining, question answering solutions "
                "with Azure AI Language, text summarisation, and integrating speech "
                "services into multi-modal pipelines."
            ),
            "weight_pct": 32,
        },
        {
            "sequence_order": 5,
            "domain_name": "Implement Knowledge Mining and Document Intelligence",
            "domain_description": (
                "Azure Cognitive Search and Form Recogniser: building search indexes "
                "with AI enrichment pipelines, custom skills, knowledge stores, "
                "Azure AI Document Intelligence (prebuilt vs. custom models), "
                "extracting structured data from forms and invoices, and integrating "
                "document intelligence into end-to-end solutions."
            ),
            "weight_pct": 12,
        },
        {
            "sequence_order": 6,
            "domain_name": "Implement Generative AI Solutions",
            "domain_description": (
                "Azure OpenAI Service integration: deploying GPT and embedding models "
                "in Azure, prompt engineering for code and content generation, "
                "retrieval-augmented generation with Azure Cognitive Search, building "
                "chat applications with the Chat Completions API, and applying "
                "responsible AI practices to generative AI deployments."
            ),
            "weight_pct": 12,
        },
    ],

    # ── AWS Certified Machine Learning Engineer – Associate (MLA-C01) ─────
    # Source: AWS Certified Machine Learning Engineer – Associate Exam Guide
    # (https://aws.amazon.com/certification/certified-machine-learning-engineer-associate/)
    # Verified: ✓ human review 2026-08.
    "MLA-C01": [
        {
            "sequence_order": 1,
            "domain_name": "Data Preparation for Machine Learning",
            "domain_description": (
                "End-to-end data engineering for ML: data ingestion and transformation "
                "with AWS Glue and Amazon EMR, feature engineering, feature stores "
                "(SageMaker Feature Store), data labelling with SageMaker Ground Truth, "
                "data quality monitoring, and handling imbalanced datasets."
            ),
            "weight_pct": 28,
        },
        {
            "sequence_order": 2,
            "domain_name": "ML Model Development",
            "domain_description": (
                "Training and tuning ML models on AWS: SageMaker Training jobs, "
                "built-in algorithms, custom containers, hyperparameter optimisation, "
                "distributed training strategies, SageMaker Experiments for tracking, "
                "model evaluation metrics (AUC, RMSE, F1), and transfer learning "
                "with foundation models via Amazon Bedrock."
            ),
            "weight_pct": 26,
        },
        {
            "sequence_order": 3,
            "domain_name": "Deployment and Orchestration of ML Workloads",
            "domain_description": (
                "Productionising ML models: SageMaker real-time inference endpoints, "
                "batch transform jobs, serverless inference, multi-model endpoints, "
                "blue/green and canary deployment strategies, SageMaker Pipelines "
                "for MLOps automation, and AWS Step Functions for workflow "
                "orchestration of ML jobs."
            ),
            "weight_pct": 22,
        },
        {
            "sequence_order": 4,
            "domain_name": "ML Solution Monitoring, Maintenance, and Security",
            "domain_description": (
                "Keeping ML in production healthy: SageMaker Model Monitor for data "
                "and model quality drift, concept drift detection, retraining "
                "triggers, SageMaker Clarify for bias and explainability, IAM roles "
                "and VPC configurations for SageMaker, encryption of data at rest "
                "and in transit, and audit logging with AWS CloudTrail."
            ),
            "weight_pct": 24,
        },
    ],

    # ── Google Cloud Generative AI Leader (GCGAIL) ─────────────────────────
    # Source: Google Cloud Generative AI Leader exam guide
    # (https://cloud.google.com/certification/generative-ai-leader).
    # Verified: ✓ human review 2026-08.
    "GCGAIL": [
        {
            "sequence_order": 1,
            "domain_name": "Fundamentals of Generative AI and Large Language Models",
            "domain_description": (
                "Core concepts every AI leader needs: what generative AI is and "
                "isn't, how LLMs are trained and prompted, key terminology "
                "(tokens, embeddings, temperature, hallucination), model families "
                "available on Google Cloud (Gemini, PaLM, Imagen), and how to "
                "evaluate output quality at a non-technical level."
            ),
            "weight_pct": 25,
        },
        {
            "sequence_order": 2,
            "domain_name": "Google Cloud Generative AI Products and Solutions",
            "domain_description": (
                "The Google Cloud generative AI product landscape: Vertex AI and "
                "Vertex AI Studio, Model Garden, Agent Builder, Gemini for Workspace, "
                "Duet AI for Developers and Google Cloud, and how to select the "
                "right product for a given business use case."
            ),
            "weight_pct": 30,
        },
        {
            "sequence_order": 3,
            "domain_name": "Implementing Responsible and Ethical AI",
            "domain_description": (
                "Google's responsible AI framework: fairness, interpretability, "
                "privacy, security, and reliability principles.  Identifying and "
                "mitigating bias in AI systems, content safety and moderation, "
                "privacy considerations when working with LLMs, and governance "
                "strategies for AI programmes."
            ),
            "weight_pct": 25,
        },
        {
            "sequence_order": 4,
            "domain_name": "Applied Generative AI for Business Strategy",
            "domain_description": (
                "Strategic and commercial lens on generative AI: identifying high-"
                "value business use cases, change management for AI adoption, "
                "measuring ROI of AI initiatives, build vs. buy decisions, managing "
                "AI vendors and partnerships, and leading cross-functional AI "
                "transformation programmes."
            ),
            "weight_pct": 20,
        },
    ],

    # ── Google Cloud Professional Machine Learning Engineer (GCPMLE) ───────
    # Source: Google Cloud Professional Machine Learning Engineer exam guide
    # (https://cloud.google.com/certification/machine-learning-engineer).
    # Verified: ✓ human review 2026-08.
    "GCPMLE": [
        {
            "sequence_order": 1,
            "domain_name": "Architecting Low-Code ML Solutions",
            "domain_description": (
                "Building ML solutions with managed Google Cloud services: BigQuery ML "
                "for in-database model training, Vertex AI AutoML for structured data, "
                "vision, NLP, and video, and pre-trained APIs (Vision AI, Natural "
                "Language API, Translation API).  Choosing between custom and low-code "
                "approaches based on business constraints."
            ),
            "weight_pct": 12,
        },
        {
            "sequence_order": 2,
            "domain_name": "Collaborating Within and Across Teams to Manage Data and Models",
            "domain_description": (
                "Data and model governance practices: feature engineering and "
                "management with Vertex AI Feature Store, dataset versioning, model "
                "registry, experiment tracking in Vertex AI Experiments, and "
                "cross-team collaboration patterns for ML projects including data "
                "science and data engineering handoffs."
            ),
            "weight_pct": 16,
        },
        {
            "sequence_order": 3,
            "domain_name": "Scaling Prototypes into ML Models",
            "domain_description": (
                "Taking models from notebook to production training: Vertex AI "
                "Training custom jobs, distributed training with tf.distribute and "
                "PyTorch DDP, hyperparameter tuning with Vertex AI Vizier, "
                "pre-trained model fine-tuning, and managing GPU/TPU resources for "
                "cost-efficient training."
            ),
            "weight_pct": 18,
        },
        {
            "sequence_order": 4,
            "domain_name": "Serving and Scaling Models",
            "domain_description": (
                "Model serving on Vertex AI: online prediction endpoints, batch "
                "prediction jobs, model explainability (Vertex Explainable AI), "
                "A/B testing and traffic splitting, autoscaling policies, and "
                "optimising inference cost and latency for real-time and async "
                "serving workloads."
            ),
            "weight_pct": 19,
        },
        {
            "sequence_order": 5,
            "domain_name": "Automating and Orchestrating ML Pipelines",
            "domain_description": (
                "MLOps pipeline engineering: Vertex AI Pipelines (Kubeflow-based) "
                "for end-to-end automation, CI/CD for ML with Cloud Build and "
                "Artifact Registry, trigger-based retraining, model promotion "
                "workflows, and integrating Vertex AI into broader data platform "
                "architectures with Dataflow and Pub/Sub."
            ),
            "weight_pct": 16,
        },
        {
            "sequence_order": 6,
            "domain_name": "Monitoring ML Solutions",
            "domain_description": (
                "Production ML health monitoring: Vertex AI Model Monitoring for "
                "training-serving skew and prediction drift detection, configuring "
                "monitoring jobs and alert thresholds, logging and tracing in "
                "Cloud Logging and Cloud Trace, and building dashboards for "
                "model performance KPIs using Looker and Vertex AI Tensorboard."
            ),
            "weight_pct": 19,
        },
    ],
}


# ── Seeder ────────────────────────────────────────────────────────────────────

async def seed_certification_domains(session: AsyncSession) -> None:
    """Seed bootstrap certification domain rows for every active cert.

    Phase 10.2 versioned strategy (idempotent):
    - For each cert in DOMAINS_BY_CERT_CODE:
      1. Look up the cert's bootstrap CertificationDomainVersion row.
         - If it already exists, reuse it.
         - If not, create one (is_current=True, version_label=BOOTSTRAP_VERSION_LABEL).
      2. Count existing CertificationDomain rows for (cert_id, version_id).
         - If any exist, skip (already seeded for this version).
         - If none exist, insert domain rows with domain_version_id set.

    Existing domain rows are NEVER deleted.  Once a practitioner profile
    references a version via its frozen ``domain_version_id``, deleting domain
    rows for that version would break historical scoring.

    Certs not in DOMAINS_BY_CERT_CODE are skipped silently.
    """
    cert_codes = list(DOMAINS_BY_CERT_CODE.keys())
    result = await session.execute(
        select(Certification.id, Certification.code).where(
            Certification.code.in_(cert_codes),
            Certification.is_active == True,  # noqa: E712
        )
    )
    cert_rows = result.all()

    if not cert_rows:
        print("  No matching active certifications found; skipping domain seed.")
        return

    cert_map: dict[str, str] = {code: id_ for id_, code in cert_rows}

    for code, domains in DOMAINS_BY_CERT_CODE.items():
        cert_id = cert_map.get(code)
        if cert_id is None:
            continue  # cert not in DB or not active

        # ── Step 1: resolve or create the bootstrap version row ───────────────
        version_result = await session.execute(
            select(CertificationDomainVersion.id).where(
                CertificationDomainVersion.certification_id == cert_id,
                CertificationDomainVersion.version_label == BOOTSTRAP_VERSION_LABEL,
            )
        )
        existing_version_id = version_result.scalar_one_or_none()

        if existing_version_id:
            version_id = existing_version_id
        else:
            version = CertificationDomainVersion(
                id=str(uuid.uuid4()),
                certification_id=cert_id,
                version_label=BOOTSTRAP_VERSION_LABEL,
                is_current=True,
                source_notes=_BOOTSTRAP_SOURCE_NOTES,
                agent_run_id=None,
                created_by_admin_id=None,
            )
            session.add(version)
            await session.flush()  # materialise the ID before FK references
            version_id = version.id
            print(f"  [{code}] created bootstrap version row ({BOOTSTRAP_VERSION_LABEL})")

        # ── Step 2: insert domain rows if absent for this version ─────────────
        count_result = await session.execute(
            select(func.count()).where(
                CertificationDomain.certification_id == cert_id,
                CertificationDomain.domain_version_id == version_id,
            )
        )
        existing_count = count_result.scalar_one()

        if existing_count > 0:
            print(
                f"  [{code}] {existing_count} domain rows already linked to "
                f"bootstrap version; skipping insert."
            )
            continue

        for domain_spec in domains:
            domain = CertificationDomain(
                id=str(uuid.uuid4()),
                certification_id=cert_id,
                domain_version_id=version_id,
                domain_name=domain_spec["domain_name"],
                domain_description=domain_spec["domain_description"],
                weight_pct=domain_spec["weight_pct"],
                sequence_order=domain_spec["sequence_order"],
            )
            session.add(domain)

        domain_count = len(domains)
        total_weight = sum(d["weight_pct"] for d in domains)
        print(
            f"  [{code}] seeded {domain_count} domains "
            f"(total weight: {total_weight}%, version: {BOOTSTRAP_VERSION_LABEL})"
        )

    await session.flush()
