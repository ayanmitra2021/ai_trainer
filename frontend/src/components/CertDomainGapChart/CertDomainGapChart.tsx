/**
 * CertDomainGapChart — horizontal progress bars showing exam-domain readiness.
 *
 * Shows one bar per certification exam domain in sequence_order.
 * Bar fill colour follows the trend: improving → green, declining → amber, stable → blue.
 * Delta chips appear to the right of each bar.
 * An estimate note is shown if any domain is still self-assessment-derived.
 */

import { useCertDomainScores } from "../../hooks";
import type { CertificationDomainScore } from "../../api/types";

interface Props {
  practitionerId: string;
  certificationId: string;
  certCode: string;
}

// Derive fill colour from trend, using CSS variables with fallbacks
function trendFillColor(trend: CertificationDomainScore["trend"], pct: number): string {
  if (trend === "improving") return "var(--color-trend-up, #22c55e)";
  if (trend === "declining") return "var(--color-trend-down, #f59e0b)";
  // stable / new: use primary-like colour based on pct bucket
  if (pct < 30) return "var(--danger)";
  if (pct < 60) return "var(--warning)";
  return "var(--primary)";
}

function DeltaChip({ delta }: { delta: number | null | undefined }) {
  if (delta == null || Math.abs(delta) < 0.001) return null;
  const isPositive = delta > 0;
  const label = `${isPositive ? "+" : ""}${(delta * 100).toFixed(0)}%`;
  return (
    <span
      style={{
        fontSize: "0.75rem",
        fontWeight: 700,
        color: isPositive
          ? "var(--color-trend-up, #22c55e)"
          : "var(--color-trend-down, #f59e0b)",
        minWidth: "3rem",
        textAlign: "right",
        flexShrink: 0,
        fontVariantNumeric: "tabular-nums",
      }}
      aria-label={`${isPositive ? "Increased" : "Decreased"} by ${Math.abs(delta * 100).toFixed(0)}%`}
    >
      {isPositive ? "▲" : "▼"} {label}
    </span>
  );
}

function DomainBar({ domain, certCode }: { domain: CertificationDomainScore; certCode: string }) {
  const pct = domain.mastery_score * 100;
  const fillColor = trendFillColor(domain.trend, pct);
  const updatedDate = new Date(domain.last_computed_at).toLocaleDateString();

  const tooltipText = [
    `Domain ${domain.sequence_order}: ${domain.domain_name}`,
    `${domain.weight_pct}% of ${certCode} exam`,
    `Last updated: ${updatedDate}`,
  ].join(" · ");

  return (
    <div
      title={tooltipText}
      aria-label={tooltipText}
      style={{ marginBottom: "0.75rem" }}
    >
      {/* Label row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "0.3rem",
          gap: "0.5rem",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flex: 1, minWidth: 0 }}>
          <span
            style={{
              fontSize: "0.8125rem",
              color: "var(--text)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {domain.domain_name}
          </span>
          <span
            style={{
              fontSize: "0.7rem",
              padding: "0.1rem 0.4rem",
              borderRadius: "999px",
              background: "var(--surface-alt)",
              border: "1px solid var(--border)",
              color: "var(--text-muted)",
              flexShrink: 0,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {domain.weight_pct}%
          </span>
          {domain.source === "self_assessment_estimate" && (
            <span
              style={{
                fontSize: "0.65rem",
                padding: "0.1rem 0.35rem",
                borderRadius: "999px",
                background: "color-mix(in srgb, var(--warning) 15%, var(--surface))",
                color: "var(--warning)",
                border: "1px solid color-mix(in srgb, var(--warning) 30%, transparent)",
                flexShrink: 0,
              }}
              title="Estimated from self-assessment — take quizzes to refine"
            >
              est.
            </span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
          <span
            style={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: fillColor,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {pct.toFixed(0)}%
          </span>
          <DeltaChip delta={domain.mastery_delta} />
        </div>
      </div>

      {/* Progress bar */}
      <div
        style={{
          height: 8,
          background: "var(--border)",
          borderRadius: 4,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.max(pct, 0)}%`,
            background: fillColor,
            borderRadius: 4,
            transition: "width 0.5s ease",
            opacity: domain.source === "self_assessment_estimate" ? 0.65 : 1,
          }}
        />
      </div>
    </div>
  );
}

export default function CertDomainGapChart({ practitionerId, certificationId, certCode }: Props) {
  const { data: domains, isLoading, isError } = useCertDomainScores(practitionerId, certificationId);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "1.5rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (isError || !domains) {
    return (
      <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", padding: "0.5rem 0" }}>
        Could not load domain readiness data.
      </div>
    );
  }

  if (domains.length === 0) {
    return (
      <div style={{ color: "var(--text-muted)", fontSize: "0.875rem", padding: "0.5rem 0" }}>
        No exam domain data yet. Take cert-relevant quizzes to see your readiness by domain.
      </div>
    );
  }

  const hasEstimates = domains.some((d) => d.source === "self_assessment_estimate");
  const sorted = [...domains].sort((a, b) => a.sequence_order - b.sequence_order);

  return (
    <div>
      <h3 style={{ marginBottom: "0.125rem" }}>
        {certCode} exam domain readiness
      </h3>
      <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "0 0 0.875rem" }}>
        Weighted by official exam blueprint.
      </p>

      {hasEstimates && (
        <div
          style={{
            fontSize: "0.8125rem",
            color: "var(--warning)",
            background: "color-mix(in srgb, var(--warning) 8%, var(--surface))",
            border: "1px solid color-mix(in srgb, var(--warning) 25%, transparent)",
            borderRadius: "var(--radius)",
            padding: "0.625rem 0.875rem",
            marginBottom: "0.875rem",
            lineHeight: 1.5,
          }}
        >
          Domains marked <strong>"est."</strong> show initial estimates from your self-assessment.
          Take cert-relevant quizzes to refine them.
        </div>
      )}

      <div>
        {sorted.map((domain) => (
          <DomainBar key={domain.certification_domain_id} domain={domain} certCode={certCode} />
        ))}
      </div>
    </div>
  );
}
