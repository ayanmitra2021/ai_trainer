-- ============================================================
-- Mastery Pulse — Certification Catalog Seed
-- Generated: 2026-08-10
-- Paste into Supabase SQL Editor and click Run.
-- Safe to re-run: deletes existing seed rows first.
-- ============================================================

-- 1. Deletes (FK-safe order: most-dependent first)
DELETE FROM certification_skills WHERE certification_id IN (SELECT id FROM certifications WHERE code IN ('CCAO-F', 'CCDV-F', 'CCAF', 'CCAR-P', 'AIF-C01', 'MLA-C01', 'GCGAIL', 'GCPMLE', 'AI-900', 'AI-102'));
DELETE FROM certifications WHERE code IN ('CCAO-F', 'CCDV-F', 'CCAF', 'CCAR-P', 'AIF-C01', 'MLA-C01', 'GCGAIL', 'GCPMLE', 'AI-900', 'AI-102');
DELETE FROM certification_providers WHERE name IN ('Anthropic', 'AWS', 'Google Cloud', 'Microsoft');
DELETE FROM skills WHERE name IN ('Prompt Engineering', 'AI Ethics & Safety', 'Evaluating LLM Output', 'Structured Outputs', 'Tool Use & Function Calling', 'Context & Caching', 'MCP Servers', 'Orchestration Patterns', 'Agent Observability', 'Model Deployment', 'Monitoring & Drift Detection', 'CI/CD for ML');
DELETE FROM skills WHERE name IN ('AI Foundations', 'Claude API', 'Agentic AI', 'MLOps');

-- 2. Skills (parents first, then children)
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('6f7ac185-7174-4a76-9336-57708a80a59a', 'AI Foundations', 'AI Foundations', NULL, 'Core concepts of artificial intelligence and machine learning.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('57d00cac-d891-4ac2-b4ed-7f7e10468aef', 'Claude API', 'Claude API', NULL, 'Working with the Anthropic Claude API.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('7fca2331-a8d7-4591-ad44-c7252f94c04d', 'Agentic AI', 'Agentic AI', NULL, 'Building autonomous AI agents and multi-agent systems.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('d6c1d2c0-e061-429f-921b-6014d1772cb0', 'MLOps', 'MLOps', NULL, 'Operations and lifecycle management for ML systems.');

INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('8d8282a5-9155-4c7c-9884-661cada9d700', 'Prompt Engineering', 'AI Foundations', '6f7ac185-7174-4a76-9336-57708a80a59a', 'Crafting effective prompts for language models.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('dd42b41b-7e7f-49d6-a748-8807354a15cf', 'AI Ethics & Safety', 'AI Foundations', '6f7ac185-7174-4a76-9336-57708a80a59a', 'Responsible AI development and deployment principles.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('5205abe6-b7cd-4674-a1e0-71e70c49fccc', 'Evaluating LLM Output', 'AI Foundations', '6f7ac185-7174-4a76-9336-57708a80a59a', 'Techniques for assessing the quality of model responses.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('165b4ba3-94de-47ed-a460-cb654aaf1969', 'Structured Outputs', 'Claude API', '57d00cac-d891-4ac2-b4ed-7f7e10468aef', 'Using JSON schemas and Pydantic models to enforce typed responses.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('11efee6c-dec0-4fe4-b244-61135b47c097', 'Tool Use & Function Calling', 'Claude API', '57d00cac-d891-4ac2-b4ed-7f7e10468aef', 'Implementing and calling tools within a Claude conversation.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('0ee1013b-d18f-4447-bf60-dd7735d7d515', 'Context & Caching', 'Claude API', '57d00cac-d891-4ac2-b4ed-7f7e10468aef', 'Prompt caching, context window management, and token efficiency.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('e6affd07-cd3e-4931-a56f-47901bbd139c', 'MCP Servers', 'Agentic AI', '7fca2331-a8d7-4591-ad44-c7252f94c04d', 'Building and consuming Model Context Protocol servers.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('bb1ffdb6-af6e-4746-9417-252b9708cc78', 'Orchestration Patterns', 'Agentic AI', '7fca2331-a8d7-4591-ad44-c7252f94c04d', 'Workflow design for multi-step agent pipelines.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('424e4505-132e-41ad-8d1f-3136ef42e606', 'Agent Observability', 'Agentic AI', '7fca2331-a8d7-4591-ad44-c7252f94c04d', 'Tracing, logging, and debugging AI agent runs.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('b17afee2-59d3-424c-ae55-6442b508b03f', 'Model Deployment', 'MLOps', 'd6c1d2c0-e061-429f-921b-6014d1772cb0', 'Packaging and serving ML models in production environments.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('9929e287-1a4a-4f9e-83d8-6590d731e491', 'Monitoring & Drift Detection', 'MLOps', 'd6c1d2c0-e061-429f-921b-6014d1772cb0', 'Tracking model performance and detecting data/concept drift.');
INSERT INTO skills (id, name, category, parent_skill_id, description) VALUES ('628a6633-12fd-42df-a503-22c4af41553b', 'CI/CD for ML', 'MLOps', 'd6c1d2c0-e061-429f-921b-6014d1772cb0', 'Automating training, evaluation, and deployment pipelines.');

-- 3. Certification providers
INSERT INTO certification_providers (id, name, website, notes) VALUES ('e7e41370-87fc-41a3-a3d1-3a73eb4a7042', 'Anthropic', 'https://www.anthropic.com/partners', 'Partner Network certifications — registration requires a partner-org email. Contact your Anthropic partner representative to access exam portals.');
INSERT INTO certification_providers (id, name, website, notes) VALUES ('fd98f423-da00-40c6-be97-aa95ce08fbd0', 'AWS', 'https://aws.amazon.com/certification/', 'Amazon Web Services certifications via AWS Training and Certification.');
INSERT INTO certification_providers (id, name, website, notes) VALUES ('b67a8222-b248-4896-84ed-f06e3b0866ef', 'Google Cloud', 'https://cloud.google.com/certification', 'Google Cloud certifications via Google Cloud Skills Boost.');
INSERT INTO certification_providers (id, name, website, notes) VALUES ('7dfe01d0-29ae-4143-b6de-911df667a706', 'Microsoft', 'https://learn.microsoft.com/en-us/certifications/', 'Microsoft Azure certifications via Microsoft Learn.');

-- 4. Certifications
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('b5127b43-ffd1-48a7-92e8-6ca5510acc63', 'e7e41370-87fc-41a3-a3d1-3a73eb4a7042', 'CCAO-F', 'Claude Certified Associate – Foundations', 'foundational', FALSE, 'Business users, consultants, and productivity-focused practitioners who use Claude conversationally — not developers or agentic builders.', 'Effective use of Claude for business tasks; prompt fundamentals; AI ethics.', 'Multiple-choice and short-response; no coding required.', 'Requires Anthropic Partner Network org email.', NULL, TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('88a9a862-92b5-4261-9c49-e2d2e2bcd5dd', 'e7e41370-87fc-41a3-a3d1-3a73eb4a7042', 'CCDV-F', 'Claude Certified Developer – Foundations', 'foundational', TRUE, 'Software developers building Claude-powered applications.', 'Claude API integration; tool use; structured outputs; basic agent patterns.', 'Multiple-choice and coding exercises.', 'Requires Anthropic Partner Network org email.', NULL, TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('3d8b4868-fa80-424e-b14a-222108fa59d0', 'e7e41370-87fc-41a3-a3d1-3a73eb4a7042', 'CCAF', 'Claude Certified Architect – Foundations', 'foundational', TRUE, 'Technical architects designing Claude-powered systems at scale.', 'System design with Claude; agentic patterns; MCP; observability; multi-agent orchestration.', 'Scenario-based design questions; no live coding required.', 'Technical background recommended. Requires Anthropic Partner Network org email.', NULL, TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('08787644-46fb-4c67-aa14-9c9cf0218a7e', 'e7e41370-87fc-41a3-a3d1-3a73eb4a7042', 'CCAR-P', 'Claude Certified Architect – Professional', 'professional', TRUE, 'Senior architects with hands-on production experience building complex Claude-powered systems.', 'Advanced multi-agent design; security and compliance; cost optimisation; large-scale deployment patterns.', 'Scenario-based deep dives; architecture review exercises.', 'CCAF recommended as prerequisite. Requires Anthropic Partner Network org email.', NULL, TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('c56aacaf-2a11-4d68-ab3b-6aed8a43f56d', 'fd98f423-da00-40c6-be97-aa95ce08fbd0', 'AIF-C01', 'AWS Certified AI Practitioner', 'foundational', FALSE, 'Business stakeholders, project managers, and non-technical practitioners working with AWS AI/ML services.', 'AWS AI/ML service landscape; responsible AI; basic ML concepts.', '65 questions; 90 minutes; Pearson VUE or testing centre.', NULL, 'https://aws.amazon.com/certification/certified-ai-practitioner/', TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('339305f4-7776-4d41-8952-ae2eebff9a79', 'fd98f423-da00-40c6-be97-aa95ce08fbd0', 'MLA-C01', 'AWS Certified Machine Learning Engineer – Associate', 'associate', TRUE, 'ML engineers building, deploying, and monitoring models on AWS.', 'SageMaker; MLOps pipelines; model deployment; monitoring.', '65 questions; 130 minutes; Pearson VUE or testing centre.', 'Recommended: 1+ year hands-on ML on AWS.', 'https://aws.amazon.com/certification/certified-machine-learning-engineer-associate/', TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('45b9c814-eeef-43e6-bab2-f0361b3c20d1', 'b67a8222-b248-4896-84ed-f06e3b0866ef', 'GCGAIL', 'Google Cloud Generative AI Leader', 'foundational', FALSE, 'Business leaders, strategists, and non-technical practitioners evaluating generative AI for their organisations.', 'GenAI strategy; responsible AI; Google Cloud AI product landscape.', 'Multiple-choice; no coding.', NULL, 'https://cloud.google.com/certification/generative-ai-leader', TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('e6c51d47-6584-4aa6-86ef-9a6ca0c0c360', 'b67a8222-b248-4896-84ed-f06e3b0866ef', 'GCPMLE', 'Professional Machine Learning Engineer', 'professional', TRUE, 'ML engineers designing, building, and productionising ML models on GCP.', 'Vertex AI; MLOps on GCP; model monitoring; feature engineering.', '60 questions; 120 minutes; Pearson VUE or testing centre.', 'Recommended: 3+ years industry experience, 1+ year on GCP.', 'https://cloud.google.com/certification/machine-learning-engineer', TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('a79b3329-7a50-4400-908d-e837b037eb52', '7dfe01d0-29ae-4143-b6de-911df667a706', 'AI-900', 'Azure AI Fundamentals', 'foundational', FALSE, 'Non-technical practitioners new to AI and Azure AI services.', 'Azure Cognitive Services; responsible AI; basic ML concepts.', '40–60 questions; 45 minutes; Pearson VUE.', NULL, 'https://learn.microsoft.com/en-us/certifications/azure-ai-fundamentals/', TRUE, '2026-08-10');
INSERT INTO certifications (id, provider_id, code, name, level, requires_coding_background, typical_audience, focus_area, exam_format, eligibility_notes, external_url, is_active, last_verified_at) VALUES ('668096ff-ec81-49ea-bc6b-4281992eb328', '7dfe01d0-29ae-4143-b6de-911df667a706', 'AI-102', 'Azure AI Engineer Associate', 'associate', TRUE, 'Developers building Azure AI solutions using Cognitive Services and Azure OpenAI.', 'Azure OpenAI integration; Cognitive Services; AI solution design.', '40–60 questions; 120 minutes; Pearson VUE.', 'Recommended: AI-900 or equivalent experience.', 'https://learn.microsoft.com/en-us/certifications/azure-ai-engineer/', TRUE, '2026-08-10');

-- 4. Certification–skill mappings
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('b5127b43-ffd1-48a7-92e8-6ca5510acc63', '8d8282a5-9155-4c7c-9884-661cada9d700', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('b5127b43-ffd1-48a7-92e8-6ca5510acc63', 'dd42b41b-7e7f-49d6-a748-8807354a15cf', 0.8);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('b5127b43-ffd1-48a7-92e8-6ca5510acc63', '5205abe6-b7cd-4674-a1e0-71e70c49fccc', 0.6);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('88a9a862-92b5-4261-9c49-e2d2e2bcd5dd', '165b4ba3-94de-47ed-a460-cb654aaf1969', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('88a9a862-92b5-4261-9c49-e2d2e2bcd5dd', '11efee6c-dec0-4fe4-b244-61135b47c097', 0.8);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('88a9a862-92b5-4261-9c49-e2d2e2bcd5dd', '8d8282a5-9155-4c7c-9884-661cada9d700', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('88a9a862-92b5-4261-9c49-e2d2e2bcd5dd', '0ee1013b-d18f-4447-bf60-dd7735d7d515', 0.6);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('3d8b4868-fa80-424e-b14a-222108fa59d0', 'e6affd07-cd3e-4931-a56f-47901bbd139c', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('3d8b4868-fa80-424e-b14a-222108fa59d0', 'bb1ffdb6-af6e-4746-9417-252b9708cc78', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('3d8b4868-fa80-424e-b14a-222108fa59d0', '424e4505-132e-41ad-8d1f-3136ef42e606', 0.8);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('3d8b4868-fa80-424e-b14a-222108fa59d0', '165b4ba3-94de-47ed-a460-cb654aaf1969', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('3d8b4868-fa80-424e-b14a-222108fa59d0', '11efee6c-dec0-4fe4-b244-61135b47c097', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('08787644-46fb-4c67-aa14-9c9cf0218a7e', 'bb1ffdb6-af6e-4746-9417-252b9708cc78', 1.0);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('08787644-46fb-4c67-aa14-9c9cf0218a7e', '424e4505-132e-41ad-8d1f-3136ef42e606', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('08787644-46fb-4c67-aa14-9c9cf0218a7e', 'e6affd07-cd3e-4931-a56f-47901bbd139c', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('08787644-46fb-4c67-aa14-9c9cf0218a7e', 'b17afee2-59d3-424c-ae55-6442b508b03f', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('08787644-46fb-4c67-aa14-9c9cf0218a7e', '9929e287-1a4a-4f9e-83d8-6590d731e491', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('c56aacaf-2a11-4d68-ab3b-6aed8a43f56d', '8d8282a5-9155-4c7c-9884-661cada9d700', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('c56aacaf-2a11-4d68-ab3b-6aed8a43f56d', 'dd42b41b-7e7f-49d6-a748-8807354a15cf', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('c56aacaf-2a11-4d68-ab3b-6aed8a43f56d', '5205abe6-b7cd-4674-a1e0-71e70c49fccc', 0.5);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('339305f4-7776-4d41-8952-ae2eebff9a79', 'b17afee2-59d3-424c-ae55-6442b508b03f', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('339305f4-7776-4d41-8952-ae2eebff9a79', '9929e287-1a4a-4f9e-83d8-6590d731e491', 0.8);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('339305f4-7776-4d41-8952-ae2eebff9a79', '628a6633-12fd-42df-a503-22c4af41553b', 0.8);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('45b9c814-eeef-43e6-bab2-f0361b3c20d1', '8d8282a5-9155-4c7c-9884-661cada9d700', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('45b9c814-eeef-43e6-bab2-f0361b3c20d1', 'dd42b41b-7e7f-49d6-a748-8807354a15cf', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('e6c51d47-6584-4aa6-86ef-9a6ca0c0c360', 'b17afee2-59d3-424c-ae55-6442b508b03f', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('e6c51d47-6584-4aa6-86ef-9a6ca0c0c360', '9929e287-1a4a-4f9e-83d8-6590d731e491', 0.9);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('e6c51d47-6584-4aa6-86ef-9a6ca0c0c360', '628a6633-12fd-42df-a503-22c4af41553b', 0.8);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('a79b3329-7a50-4400-908d-e837b037eb52', '8d8282a5-9155-4c7c-9884-661cada9d700', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('a79b3329-7a50-4400-908d-e837b037eb52', 'dd42b41b-7e7f-49d6-a748-8807354a15cf', 0.6);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('668096ff-ec81-49ea-bc6b-4281992eb328', '11efee6c-dec0-4fe4-b244-61135b47c097', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('668096ff-ec81-49ea-bc6b-4281992eb328', '8d8282a5-9155-4c7c-9884-661cada9d700', 0.7);
INSERT INTO certification_skills (certification_id, skill_id, weight) VALUES ('668096ff-ec81-49ea-bc6b-4281992eb328', 'dd42b41b-7e7f-49d6-a748-8807354a15cf', 0.6);

-- 5. Certification domain versions (bootstrap snapshot, one per cert)
-- Generated: 2026-08-11 — matches migration 014_seed_domain_data.py
-- Uses DO $$ ... $$ so re-runs are idempotent: skips any cert that already
-- has a domain_version row with this label, and skips domain rows that already
-- exist for the resolved version.

DO $$
DECLARE
  _label    TEXT := 'bootstrap-step-10.1';
  _notes    TEXT := 'Bootstrap seed from Phase 10.1 certification exam guides. Verified against official exam guide PDFs at Step 10.1 time.';
  _now      TIMESTAMPTZ := NOW();

  -- Procedure: given a cert code, ensure a bootstrap version exists and
  -- domain rows are seeded.  Returns without action if the cert is absent.
  _cert_id  UUID;
  _ver_id   UUID;
  _cnt      INT;

BEGIN
  -- ── Helper: resolve or create bootstrap version for a given cert ──────────
  -- We use a nested loop over cert codes rather than a function so this block
  -- stays self-contained and pasteable into the Supabase SQL editor.

  FOR _cert_id IN
    SELECT id FROM certifications
    WHERE code IN ('AIF-C01','CCAO-F','CCDV-F','CCAF','CCAR-P',
                   'AI-900','AI-102','MLA-C01','GCGAIL','GCPMLE')
      AND is_active = true
  LOOP
    -- Resolve or create bootstrap version
    SELECT id INTO _ver_id
      FROM certification_domain_versions
     WHERE certification_id = _cert_id AND version_label = _label;

    IF _ver_id IS NULL THEN
      SELECT id INTO _ver_id
        FROM certification_domain_versions
       WHERE certification_id = _cert_id AND is_current = true;
    END IF;

    IF _ver_id IS NULL THEN
      _ver_id := gen_random_uuid();
      INSERT INTO certification_domain_versions
        (id, certification_id, version_label, is_current, source_notes,
         agent_run_id, created_by_admin_id, created_at)
      VALUES (_ver_id, _cert_id, _label, true, _notes, NULL, NULL, _now);
    END IF;

    -- Skip domain insert if rows already exist for this (cert, version)
    SELECT COUNT(*) INTO _cnt
      FROM certification_domains
     WHERE certification_id = _cert_id AND domain_version_id = _ver_id;

    IF _cnt > 0 THEN
      CONTINUE;
    END IF;

    -- Insert domain rows based on cert code
    CASE (SELECT code FROM certifications WHERE id = _cert_id)

      WHEN 'AIF-C01' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Fundamentals of AI and ML','Basic concepts of artificial intelligence and machine learning: AI/ML terminology, supervised vs. unsupervised learning, model training concepts, overfitting/underfitting, common ML use cases, and when to apply ML vs. rule-based systems.',20),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Fundamentals of Generative AI','Core concepts of generative AI: foundation models, large language models (LLMs), tokenisation, embeddings, prompt engineering basics, retrieval-augmented generation (RAG), fine-tuning concepts, and the AWS generative AI service landscape (Amazon Bedrock, Titan).',24),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Applications of Foundation Models','Practical use of foundation models: selecting appropriate models for tasks, prompt engineering techniques (zero-shot, few-shot, chain-of-thought), model customisation methods, building RAG pipelines, integrating foundation models into applications using Amazon Bedrock and the Bedrock Knowledge Bases service.',28),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Guidelines for Responsible AI','Responsible AI principles and practices: bias detection and mitigation, fairness, explainability, model transparency, dataset limitations, hallucination in LLMs, and AWS tools for responsible AI (Amazon SageMaker Clarify, Model Cards).',14),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Security, Compliance, and Governance for AI Solutions','Security and governance for AI workloads: data privacy, model intellectual property, regulatory compliance considerations, AWS shared responsibility model applied to AI, securing training data and model artefacts, identity and access management for AI services.',14);

      WHEN 'CCAO-F' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Introduction to AI and Claude','Core concepts of large language models and Claude''s place in the AI landscape: how Claude works at a high level, the Anthropic safety mission, key Claude capabilities (analysis, writing, coding, reasoning), model families (Haiku / Sonnet / Opus), and how to access Claude through the API and consumer products.',20),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Prompt Engineering Fundamentals','Writing effective prompts: system prompts, user messages, context provision, tone and format specification, zero-shot and few-shot techniques, prompt structure best practices, common failure modes (hallucination, refusals), and iterative prompt improvement.',25),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Claude API and Tool Use Essentials','Practical API usage: authentication, the Messages endpoint, conversation history management, tool use / function calling basics, streaming responses, token counting, and context window management — focused on the concepts a non-developer practitioner needs to understand, not deep implementation.',20),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Responsible AI and Safety','Anthropic''s approach to AI safety: Constitutional AI, RLHF, harm avoidance policies, usage policies, topics Claude declines to assist with, how to handle Claude refusals gracefully, bias awareness, and ethical considerations when deploying AI in business contexts.',20),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Deploying Claude in Practice','Practical deployment considerations: use-case selection and feasibility, integrating Claude into business workflows, evaluating Claude outputs for quality and accuracy, cost considerations, monitoring and iterating on Claude-powered features, and common deployment anti-patterns to avoid.',15);

      WHEN 'CCDV-F' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Claude API and SDK Essentials','Core API mechanics: authentication, the Messages API endpoint, model selection, request/response structure, streaming, error handling, rate limits, the Python and TypeScript SDK, and practical token budget management with the context window.',25),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Advanced Prompt Engineering','Developer-level prompt techniques: system prompt design, multi-turn conversation construction, chain-of-thought prompting, XML tagging for structure, few-shot examples in code contexts, prompt caching for cost and latency optimisation, and debugging common prompt failure modes.',20),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Tool Use and Function Calling','Implementing tool use: defining tools with JSON schema, handling tool_use and tool_result message blocks, multi-tool workflows, parallel vs. sequential tool calls, strict schema validation, testing tool integrations, and common pitfalls in tool-use loops.',20),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Building and Testing Production Applications','Production engineering practices: structured outputs via Pydantic / JSON Schema, error handling and retry strategies, async patterns, prompt injection prevention, secrets management, writing testable Claude integrations, and CI practices for LLM-backed services.',20),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Evaluation and Monitoring','Measuring and maintaining quality: defining success criteria for LLM outputs, building evaluation datasets, automated grading approaches, latency and cost monitoring, model drift detection, and iterating on prompts with production feedback.',15);

      WHEN 'CCAF' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'System Design with Claude','Architecture patterns for Claude-powered systems: choosing between single-model and multi-model designs, context engineering at scale, prompt management strategies, abstraction layers, latency vs. quality trade-offs, and how to structure Claude integrations in larger service-oriented architectures.',20),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Multi-Agent and Agentic Architectures','Designing agentic systems: orchestrator/subagent patterns, agent communication protocols, MCP (Model Context Protocol) server design and consumption, tool-use strategy in multi-step pipelines, managing agent memory and state, failure recovery, and when to choose agentic vs. single-turn approaches.',25),
          (gen_random_uuid(),_cert_id,_ver_id,3,'RAG and Knowledge Integration','Retrieval-augmented generation architecture: vector store selection, chunking and embedding strategies, retrieval quality tuning, hybrid search approaches, knowledge freshness, citation and grounding techniques, and integrating external knowledge bases with Claude''s context window efficiently.',20),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Production Architecture Patterns','Running Claude in production: observability (tracing, cost tracking, latency monitoring), caching strategies (prompt cache, semantic cache), horizontal scaling patterns, graceful degradation, cost optimisation levers (model tiering, batching), and integrating with cloud infrastructure and CI/CD pipelines.',20),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Safety Engineering and Responsible Design','Safety by design: threat modelling for LLM systems (prompt injection, data exfiltration risks), output validation architectures, guardrails and content filters, PII handling, access control for AI features, audit logging, and embedding responsible AI principles into architecture decisions rather than adding them as afterthoughts.',15);

      WHEN 'CCAR-P' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Advanced Agentic Systems at Scale','Complex multi-agent architectures for enterprise scale: long-running agent workflows, hierarchical orchestration, inter-agent trust and authentication, shared memory architectures, consensus and conflict resolution between agents, and production debugging of distributed agentic pipelines.',25),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Enterprise Integration Patterns','Integrating Claude into enterprise environments: SSO and identity federation for AI services, enterprise data governance, connecting to legacy systems via MCP adapters, event-driven architectures, async job queues for long-running inference, and managing multiple Claude deployments across business units.',20),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Safety Engineering and Risk Management','Advanced safety architecture: red-teaming methodologies, adversarial robustness, model behaviour contracts, anomaly detection in LLM outputs, incident response procedures for AI failures, regulatory and compliance risk mapping, and privacy-by-design for AI systems handling sensitive data.',20),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Performance Optimization and Cost Control','Maximising efficiency at scale: token cost modelling, prompt compression techniques, dynamic model routing (Haiku for simple tasks, Opus for complex reasoning), cache hit rate optimisation, batching strategies using the Message Batches API, and building FinOps practices around LLM spend.',20),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Multi-Provider and Platform Strategies','Operating across AI providers: abstraction layers for provider portability, provider comparison frameworks, fallback and failover strategies, evaluating model capabilities for specific tasks, managing vendor lock-in risk, and governance of multi-provider AI deployments.',15);

      WHEN 'AI-900' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'AI Workloads and Considerations','Identifying common AI workload types and their appropriate uses: prediction, classification, clustering, anomaly detection, NLP, computer vision, and generative AI. Responsible AI principles (fairness, reliability, privacy, inclusiveness, transparency, accountability) and their application in Microsoft''s framework.',18),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Machine Learning in Azure','Core ML concepts and Azure ML tooling: supervised vs. unsupervised learning, regression vs. classification, model training and evaluation metrics, Azure Machine Learning studio, automated ML (AutoML), and the Azure ML designer for low-code model training.',22),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Computer Vision Workloads','Azure computer vision services: Azure AI Vision (image analysis, object detection, OCR), Azure AI Face service, Azure AI Custom Vision for training domain-specific image classifiers, and common use cases for computer vision in business applications.',20),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Natural Language Processing Workloads','Azure NLP services: Azure AI Language (text analytics, sentiment analysis, key phrase extraction, named entity recognition, language detection), Azure AI Translator, Azure AI Speech (speech-to-text, text-to-speech), and the Azure AI Bot Service for conversational AI.',20),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Generative AI Workloads','Generative AI fundamentals on Azure: large language models, Azure OpenAI Service capabilities (GPT, DALL-E, Codex), prompt engineering basics, Copilot products and the Microsoft Copilot ecosystem, and responsible considerations specific to generative AI (grounding, hallucination, content safety).',20);

      WHEN 'AI-102' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Plan and Manage an Azure AI Solution','Solution architecture and governance for Azure AI: selecting appropriate Azure AI services for a scenario, planning compute and storage resources, configuring Azure AI services, securing AI solutions (keys, managed identities, network restrictions), monitoring costs and usage, and deploying containerised AI services.',16),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Implement Content Moderation Solutions','Azure AI Content Safety: detecting harmful content (violence, hate, self-harm, sexual content), configuring severity thresholds, building content moderation pipelines, and integrating content safety checks into applications and Azure OpenAI deployments.',12),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Implement Computer Vision Solutions','Building computer vision applications with Azure AI: image analysis and classification, object detection, OCR and document intelligence, Face API for face detection and verification, Custom Vision for domain-specific models, and Video Indexer for video analysis.',16),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Implement NLP Solutions','NLP engineering with Azure AI Language: building CLU (conversational language understanding) models, named entity recognition, sentiment analysis and opinion mining, question answering solutions with Azure AI Language, text summarisation, and integrating speech services into multi-modal pipelines.',32),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Implement Knowledge Mining and Document Intelligence','Azure Cognitive Search and Form Recogniser: building search indexes with AI enrichment pipelines, custom skills, knowledge stores, Azure AI Document Intelligence (prebuilt vs. custom models), extracting structured data from forms and invoices, and integrating document intelligence into end-to-end solutions.',12),
          (gen_random_uuid(),_cert_id,_ver_id,6,'Implement Generative AI Solutions','Azure OpenAI Service integration: deploying GPT and embedding models in Azure, prompt engineering for code and content generation, retrieval-augmented generation with Azure Cognitive Search, building chat applications with the Chat Completions API, and applying responsible AI practices to generative AI deployments.',12);

      WHEN 'MLA-C01' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Data Preparation for Machine Learning','End-to-end data engineering for ML: data ingestion and transformation with AWS Glue and Amazon EMR, feature engineering, feature stores (SageMaker Feature Store), data labelling with SageMaker Ground Truth, data quality monitoring, and handling imbalanced datasets.',28),
          (gen_random_uuid(),_cert_id,_ver_id,2,'ML Model Development','Training and tuning ML models on AWS: SageMaker Training jobs, built-in algorithms, custom containers, hyperparameter optimisation, distributed training strategies, SageMaker Experiments for tracking, model evaluation metrics (AUC, RMSE, F1), and transfer learning with foundation models via Amazon Bedrock.',26),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Deployment and Orchestration of ML Workloads','Productionising ML models: SageMaker real-time inference endpoints, batch transform jobs, serverless inference, multi-model endpoints, blue/green and canary deployment strategies, SageMaker Pipelines for MLOps automation, and AWS Step Functions for workflow orchestration of ML jobs.',22),
          (gen_random_uuid(),_cert_id,_ver_id,4,'ML Solution Monitoring, Maintenance, and Security','Keeping ML in production healthy: SageMaker Model Monitor for data and model quality drift, concept drift detection, retraining triggers, SageMaker Clarify for bias and explainability, IAM roles and VPC configurations for SageMaker, encryption of data at rest and in transit, and audit logging with AWS CloudTrail.',24);

      WHEN 'GCGAIL' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Fundamentals of Generative AI and Large Language Models','Core concepts every AI leader needs: what generative AI is and isn''t, how LLMs are trained and prompted, key terminology (tokens, embeddings, temperature, hallucination), model families available on Google Cloud (Gemini, PaLM, Imagen), and how to evaluate output quality at a non-technical level.',25),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Google Cloud Generative AI Products and Solutions','The Google Cloud generative AI product landscape: Vertex AI and Vertex AI Studio, Model Garden, Agent Builder, Gemini for Workspace, Duet AI for Developers and Google Cloud, and how to select the right product for a given business use case.',30),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Implementing Responsible and Ethical AI','Google''s responsible AI framework: fairness, interpretability, privacy, security, and reliability principles. Identifying and mitigating bias in AI systems, content safety and moderation, privacy considerations when working with LLMs, and governance strategies for AI programmes.',25),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Applied Generative AI for Business Strategy','Strategic and commercial lens on generative AI: identifying high-value business use cases, change management for AI adoption, measuring ROI of AI initiatives, build vs. buy decisions, managing AI vendors and partnerships, and leading cross-functional AI transformation programmes.',20);

      WHEN 'GCPMLE' THEN
        INSERT INTO certification_domains (id,certification_id,domain_version_id,sequence_order,domain_name,domain_description,weight_pct) VALUES
          (gen_random_uuid(),_cert_id,_ver_id,1,'Architecting Low-Code ML Solutions','Building ML solutions with managed Google Cloud services: BigQuery ML for in-database model training, Vertex AI AutoML for structured data, vision, NLP, and video, and pre-trained APIs (Vision AI, Natural Language API, Translation API). Choosing between custom and low-code approaches based on business constraints.',12),
          (gen_random_uuid(),_cert_id,_ver_id,2,'Collaborating Within and Across Teams to Manage Data and Models','Data and model governance practices: feature engineering and management with Vertex AI Feature Store, dataset versioning, model registry, experiment tracking in Vertex AI Experiments, and cross-team collaboration patterns for ML projects including data science and data engineering handoffs.',16),
          (gen_random_uuid(),_cert_id,_ver_id,3,'Scaling Prototypes into ML Models','Taking models from notebook to production training: Vertex AI Training custom jobs, distributed training with tf.distribute and PyTorch DDP, hyperparameter tuning with Vertex AI Vizier, pre-trained model fine-tuning, and managing GPU/TPU resources for cost-efficient training.',18),
          (gen_random_uuid(),_cert_id,_ver_id,4,'Serving and Scaling Models','Model serving on Vertex AI: online prediction endpoints, batch prediction jobs, model explainability (Vertex Explainable AI), A/B testing and traffic splitting, autoscaling policies, and optimising inference cost and latency for real-time and async serving workloads.',19),
          (gen_random_uuid(),_cert_id,_ver_id,5,'Automating and Orchestrating ML Pipelines','MLOps pipeline engineering: Vertex AI Pipelines (Kubeflow-based) for end-to-end automation, CI/CD for ML with Cloud Build and Artifact Registry, trigger-based retraining, model promotion workflows, and integrating Vertex AI into broader data platform architectures with Dataflow and Pub/Sub.',16),
          (gen_random_uuid(),_cert_id,_ver_id,6,'Monitoring ML Solutions','Production ML health monitoring: Vertex AI Model Monitoring for training-serving skew and prediction drift detection, configuring monitoring jobs and alert thresholds, logging and tracing in Cloud Logging and Cloud Trace, and building dashboards for model performance KPIs using Looker and Vertex AI Tensorboard.',19);

      ELSE
        -- Unknown cert code — skip.
        NULL;
    END CASE;
  END LOOP;
END $$;

-- 6. Verify
SELECT p.name AS provider, c.code, c.name, c.level, c.requires_coding_background
FROM certifications c
JOIN certification_providers p ON p.id = c.provider_id
ORDER BY p.name, c.code;

-- Domain counts per cert (should be 4–6 per cert, 0 = missing)
SELECT c.code, COUNT(cd.id) AS domain_count, SUM(cd.weight_pct) AS total_weight_pct
FROM certifications c
LEFT JOIN certification_domain_versions cdv ON cdv.certification_id = c.id AND cdv.is_current = true
LEFT JOIN certification_domains cd ON cd.domain_version_id = cdv.id
GROUP BY c.code
ORDER BY c.code;
