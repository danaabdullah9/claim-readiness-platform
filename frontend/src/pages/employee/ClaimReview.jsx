import { useCallback, useEffect, useState } from "react";
import AIClaimSummary from "../../components/employee/AIClaimSummary";
import AIVerificationChecklist from "../../components/employee/AIVerificationChecklist";
import UploadedDocuments from "../../components/employee/UploadedDocuments";
import EmployeeNotes from "../../components/employee/EmployeeNotes";
import ClaimTimeline from "../../components/employee/ClaimTimeline";
import ConfirmationDialog from "../../components/employee/ConfirmationDialog";
import UserCorrectionsDisplay from "../../components/employee/UserCorrectionsDisplay";
import "./EmployeeDashboard.css";

const API_BASE_URL = "http://127.0.0.1:8001";

const formatMoney = (amount, currency) => new Intl.NumberFormat("en-SA", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);

// Approve / Reject تكتب فعليًا في عمود ClaimStatus بدل ما تبقى في المتصفح
const BACKEND_ACTIONS = { Approve: "Approved", Reject: "Rejected", "Request Missing Documents": "Action Required" };

function DetailList({ items }) {
  return <dl className="employee-detail-list">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

const DECISION_LABELS = {
  auto_approved: ["Auto-approved", "", "Processed automatically — no reviewer action was needed"],
  approve: ["Eligible — approve", "", "Fully payable under the member's benefits"],
  partial: ["Partially covered", "", "Payable up to the benefit limit; the member covers the rest"],
  pre_approval_required: ["Pre-approval required", "", "This benefit needs approval before the service is given"],
  investigate: ["Investigate before deciding", "", "Fraud signals need a reviewer's judgement"],
  reject: ["Not eligible — reject", "", "The claim falls outside the member's benefits"],
};

const RISK_TEXT = {
  clean: "No suspicious patterns found in documents or claim history",
  low: "Minor irregularities — proceed with normal review",
  medium: "Several irregularities — verify before approving",
  high: "Strong fraud indicators — manual investigation required",
  critical: "Severe fraud indicators — reject and consider blacklisting",
};

const money = (value) =>
  value == null ? "—" : `SAR ${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Bar({ label, used, total, fallbackLabel, fallbackUsed, fallbackTotal }) {
  // بند بلا حد خاص (مثل الطوارئ) يخضع للسقف السنوي، فنعرضه بدلاً منه
  const [text, spent, cap] = total ? [label, used, total] : [fallbackLabel, fallbackUsed, fallbackTotal];
  if (!cap) return null;
  const percent = Math.min(100, (spent / cap) * 100);
  const tone = percent >= 100 ? "full" : percent >= 75 ? "high" : "ok";
  return (
    <div className="intel-bar">
      <div className="intel-bar-head"><span>{text}</span><small>{money(spent)} of {money(cap)}</small></div>
      <div className={`intel-bar-track intel-bar-${tone}`}><span style={{ width: `${Math.max(percent, 1)}%` }} /></div>
    </div>
  );
}

function remaining(intel) {
  const limit = intel.policy.benefit_limit ?? intel.policy.annual_cap;
  const used = (intel.policy.benefit_limit ? intel.policy.benefit_used : intel.policy.annual_used) + intel.amounts.payable;
  return money(Math.max(0, limit - used));
}

const DECISION_TONE = {
  auto_approved: "passed", approve: "passed", partial: "warning",
  pre_approval_required: "warning", investigate: "failed", reject: "failed",
};

function ClaimReview({ claim: initialClaim, onBack }) {
  const [claim, setClaim] = useState(initialClaim);
  const [intel, setIntel] = useState(null);
  const [intelError, setIntelError] = useState("");
  const [blacklisting, setBlacklisting] = useState(false);
  const [notes, setNotes] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingAction, setPendingAction] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [correctionReview, setCorrectionReview] = useState({ isLoading: true, hasUnresolved: false });
  const handleCorrectionReviewState = useCallback((state) => setCorrectionReview(state), []);

  // طبقة الذكاء: البنود + الفئة + الاحتيال + التاريخ المرضي
  useEffect(() => {
    let cancelled = false;
    async function loadIntelligence() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/employee/claims/${claim.claimDbId}/intelligence`,
        );
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "Could not load AI assessment.");
        if (!cancelled) setIntel(result.data);
      } catch (err) {
        if (!cancelled) setIntelError(err.message || "Cannot connect to backend.");
      }
    }
    loadIntelligence();
    return () => { cancelled = true; };
  }, [claim.claimDbId]);

  async function handleBlacklist() {
    if (!intel) return;
    const reason = window.prompt(
      "Reason for adding this member to the blacklist:",
      `Fraud score ${intel.fraud.score}/100 — ${intel.fraud.signals.map((s) => s.code).join(", ")}`,
    );
    if (!reason) return;

    setBlacklisting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/employee/blacklist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: intel.member.user_id, reason, added_by: "employee" }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Could not update the blacklist.");
      setIntel({ ...intel, member: { ...intel.member, blacklisted: true } });
      setNotice(`${intel.member.name} was added to the blacklist.`);
    } catch (err) {
      setNotice(err.message || "Cannot connect to backend.");
    } finally {
      setBlacklisting(false);
    }
  }

  function handlePlaceholder(action) {
    setNotice(`${action} recorded for this review session only. No backend data was changed.`);
  }

  async function confirmAction() {
    const label = pendingAction.label;
    const backendStatus = BACKEND_ACTIONS[label];
    setPendingAction(null);

    if (!backendStatus) {
      handlePlaceholder(label);
      return;
    }

    setIsSaving(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/employee/claims/${claim.claimDbId}/status`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: backendStatus }),
        },
      );
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Could not update the claim.");

      setClaim({ ...result.data, assignedTo: claim.assignedTo });
      setNotice(`Claim ${claim.id} was updated to ${backendStatus} and the customer was notified.`);
    } catch (err) {
      setNotice(err.message || "Cannot connect to backend.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="employee-dashboard-page">
      <header className="employee-topbar"><button className="employee-back-link" type="button" onClick={onBack}>← Back to work queue</button><div className="employee-review-reference"><span>Claim reference</span><strong>{claim.id}</strong></div></header>
      <main className="employee-review-main">
        <section className="employee-review-hero">
          <div><div className="employee-review-badges"><span className={`employee-badge employee-priority-${claim.priority.toLowerCase()}`}>{claim.priority} priority</span><span className={`employee-badge employee-status-${claim.status.toLowerCase().replaceAll(" ", "-")}`}>{claim.status}</span></div><h1>Claim Review</h1><p>Review claim evidence, AI-assisted findings, and workflow readiness.</p></div>
          <div className="employee-readiness-card">
            <div className="employee-readiness-ring" role="progressbar" aria-label="Claim readiness" aria-valuemin="0" aria-valuemax="100" aria-valuenow={claim.readiness} style={{ "--employee-readiness": `${claim.readiness * 3.6}deg` }}><span>{claim.readiness}<small>%</small></span></div>
            <div><span>Claim Readiness</span><strong>{claim.readiness === 100 ? "Ready to submit" : "Review in progress"}</strong><small>{100 - claim.readiness}% requires attention</small></div>
          </div>
        </section>
        {notice && <div className="employee-notice" role="status"><span>✓</span>{notice}<button type="button" aria-label="Dismiss message" onClick={() => setNotice("")}>×</button></div>}
        <div className="employee-review-layout">
          <div className="employee-review-primary">
            <section className="employee-review-card" aria-labelledby="member-info-title"><div className="employee-section-heading"><div><p className="employee-eyebrow">Policy holder &amp; submission</p><h2 id="member-info-title">Member &amp; Claim Information</h2></div></div><DetailList items={[["Member Name", claim.member.name], ["Member ID", claim.member.memberId], ["National ID", claim.member.nationalId], ["Policy Number", claim.member.policyNumber], ["Insurance Company", "Bupa"], ["Email", claim.member.email], ["Invoice Number", claim.invoiceNumber], ["Claim Type", claim.claimType], ["Invoice Date", claim.invoiceDate], ["Submission Date", claim.submissionDate], ["Billing Entity", claim.provider], ["Service Provider", claim.serviceProvider], ["Department", claim.department], ["Submitted By", claim.submittedBy]]} /></section>
            <AIClaimSummary summary={claim.aiSummary} highlights={claim.highlights} confidence={claim.aiConfidence} />
            {intelError && <div className="employee-notice" role="alert"><span>!</span>{intelError}</div>}
            {!intel && !intelError && <section className="employee-review-card intel-loading">Running policy, fraud and history checks…</section>}

            {intel && (
              <section className={`employee-review-card intel-card intel-${DECISION_TONE[intel.decision] || "warning"}`} aria-labelledby="verdict-title">
                <div className="intel-head">
                  <div>
                    <p className="employee-eyebrow">Policy decision engine</p>
                    <h2 id="verdict-title">{DECISION_LABELS[intel.decision]?.[0] || intel.decision}</h2>
                    <p className="intel-benefit">
                      {intel.benefit.name_en} · Policy p.{intel.benefit.source_page} · {intel.policy.tier} tier
                    </p>
                  </div>
                  {intel.auto_processed && <span className="intel-chip intel-chip-auto">AUTO-PROCESSED</span>}
                </div>

                <div className="intel-figures">
                  <div className="intel-figure intel-figure-lead">
                    <span>Insurer pays</span>
                    <strong>{money(intel.amounts.payable)}</strong>
                  </div>
                  <div className="intel-figure">
                    <span>Member pays</span>
                    <strong>{money(intel.amounts.member_share)}</strong>
                  </div>
                  <div className="intel-figure">
                    <span>
                      {intel.policy.benefit_limit
                        ? "Benefit limit left after this claim"
                        : "Annual cap left after this claim"}
                    </span>
                    <strong>{remaining(intel)}</strong>
                  </div>
                </div>

                <Bar
                  label={`Benefit limit used this year`}
                  used={intel.policy.benefit_used + intel.amounts.payable}
                  total={intel.policy.benefit_limit}
                  fallbackLabel="Annual policy cap used this year"
                  fallbackUsed={intel.policy.annual_used + intel.amounts.payable}
                  fallbackTotal={intel.policy.annual_cap}
                />

                <ul className="intel-checks">
                  <li className={`intel-check intel-check-${DECISION_TONE[intel.decision] === "failed" ? "fail" : DECISION_TONE[intel.decision] === "warning" ? "warn" : "pass"}`}>
                    <span className="intel-check-icon" aria-hidden="true">{DECISION_TONE[intel.decision] === "passed" ? "✓" : "!"}</span>
                    <div>
                      <strong>Benefit rules</strong>
                      {intel.rationale.filter((item) => item.source !== "fraud").map((item, index) => (
                        <p key={index}>{item.text_en}</p>
                      ))}
                    </div>
                  </li>

                  <li className={`intel-check intel-check-${intel.fraud.risk_level === "clean" ? "pass" : intel.fraud.risk_level === "low" || intel.fraud.risk_level === "medium" ? "warn" : "fail"}`}>
                    <span className="intel-check-icon" aria-hidden="true">{intel.fraud.risk_level === "clean" ? "✓" : "!"}</span>
                    <div>
                      <strong>Fraud screening · {intel.fraud.score}/100</strong>
                      {intel.fraud.signals.length === 0 ? (
                        <p>{RISK_TEXT.clean}</p>
                      ) : (
                        <ul className="intel-signals">
                          {intel.fraud.signals.map((signal, index) => (
                            <li key={index}>
                              <span className={`intel-sev intel-sev-${signal.severity}`}>{signal.severity}</span>
                              <div><strong>{signal.code.replaceAll("_", " ")}</strong><p>{signal.detail_en}</p></div>
                              <em>+{signal.score}</em>
                            </li>
                          ))}
                        </ul>
                      )}
                      {!intel.member.blacklisted && intel.fraud.risk_level !== "clean" && (
                        <button type="button" className="employee-action-danger intel-blacklist-btn" disabled={blacklisting} onClick={handleBlacklist}>
                          {blacklisting ? "Saving…" : "Add member to blacklist"}
                        </button>
                      )}
                      {intel.member.blacklisted && <p className="intel-blocked-note">This member is on the blacklist.</p>}
                    </div>
                  </li>

                  <li className={`intel-check intel-check-${intel.clinical_context.notes.length ? "info" : "pass"}`}>
                    <span className="intel-check-icon" aria-hidden="true">{intel.clinical_context.notes.length ? "i" : "✓"}</span>
                    <div>
                      <strong>Medical history</strong>
                      {intel.clinical_context.notes.length === 0 ? (
                        <p>No chronic or hereditary condition on file matches this diagnosis.</p>
                      ) : (
                        intel.clinical_context.notes.map((note, index) => <p key={index}>{note.text_en}</p>)
                      )}
                    </div>
                  </li>

                  {intel.member.family.dependents.length > 0 && (
                    <li className="intel-check intel-check-info">
                      <span className="intel-check-icon" aria-hidden="true">i</span>
                      <div>
                        <strong>Family on this policy</strong>
                        {intel.member.family.dependents.map((person) => (
                          <p key={person.user_id}>
                            {person.name} — {person.relationship}
                            {person.shares_data ? "" : " · data withheld by adult consent"}
                          </p>
                        ))}
                      </div>
                    </li>
                  )}
                </ul>
              </section>
            )}

            <AIVerificationChecklist checklist={intel?.checklist} />
            <UploadedDocuments documents={claim.documents} />
            <UserCorrectionsDisplay claimId={claim.claimDbId} onReviewStateChange={handleCorrectionReviewState} />
            
            
          </div>
          <aside className="employee-review-sidebar">
            <EmployeeNotes value={notes} onChange={setNotes} />
            <ClaimTimeline currentStage={claim.currentStage} />
            <section className="employee-review-card employee-actions-card" aria-labelledby="actions-title"><div className="employee-section-heading"><div><p className="employee-eyebrow">Decision support</p><h2 id="actions-title">Employee Actions</h2></div></div><button type="button" className="employee-action-primary" disabled={isSaving || correctionReview.isLoading || correctionReview.hasUnresolved} onClick={() => setPendingAction({ label: "Approve", prompt: "approve this", tone: "primary" })}>{isSaving ? "Saving…" : "Approve"}</button>{correctionReview.hasUnresolved && <p className="employee-correction-approval-warning">Review all user corrections before approving this claim.</p>}<button type="button" className="employee-action-danger" disabled={isSaving} onClick={() => setPendingAction({ label: "Reject", prompt: "reject this", tone: "danger" })}>Reject</button><button type="button" onClick={() => setPendingAction({ label: "Request Missing Documents", prompt: "request missing documents for this", tone: "primary" })}>Request Missing Documents</button><button type="button" onClick={() => handlePlaceholder("Save Draft")}>Save Draft</button><button type="button" onClick={() => setPendingAction({ label: "Assign Claim", prompt: "assign this", tone: "primary" })}>Assign to Another Employee</button><p>Approve and Reject update the claim status in the database. The remaining actions stay in this session.</p></section>
          </aside>
        </div>
      </main>
      <ConfirmationDialog action={pendingAction} claimId={claim.id} onConfirm={confirmAction} onCancel={() => setPendingAction(null)} />
    </div>
  );
}

export default ClaimReview;