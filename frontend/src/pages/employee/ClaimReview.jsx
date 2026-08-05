import { useCallback, useState } from "react";
import AIClaimSummary from "../../components/employee/AIClaimSummary";
import AIVerificationChecklist from "../../components/employee/AIVerificationChecklist";
import UploadedDocuments from "../../components/employee/UploadedDocuments";
import EmployeeNotes from "../../components/employee/EmployeeNotes";
import ClaimTimeline from "../../components/employee/ClaimTimeline";
import ConfirmationDialog from "../../components/employee/ConfirmationDialog";
import UserCorrectionsDisplay from "../../components/employee/UserCorrectionsDisplay";
import "./EmployeeDashboard.css";

const API_BASE_URL = "http://127.0.0.1:8001";

const formatMoney = (amount, currency) => new Intl.NumberFormat("en-SA", { style: "currency", currency }).format(amount);

// Approve / Reject تكتب فعليًا في عمود ClaimStatus بدل ما تبقى في المتصفح
const BACKEND_ACTIONS = { Approve: "Approved", Reject: "Rejected", "Request Missing Documents": "Action Required" };

function DetailList({ items }) {
  return <dl className="employee-detail-list">{items.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

function ClaimReview({ claim: initialClaim, onBack }) {
  const [claim, setClaim] = useState(initialClaim);
  const [notes, setNotes] = useState("");
  const [notice, setNotice] = useState("");
  const [pendingAction, setPendingAction] = useState(null);
  const [isSaving, setIsSaving] = useState(false);
  const [correctionReview, setCorrectionReview] = useState({ isLoading: true, hasUnresolved: false });
  const handleCorrectionReviewState = useCallback((state) => setCorrectionReview(state), []);

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
            <section className="employee-review-card" aria-labelledby="member-info-title"><div className="employee-section-heading"><div><p className="employee-eyebrow">Policy holder</p><h2 id="member-info-title">Member Information</h2></div></div><DetailList items={[["Member Name", claim.member.name], ["Member ID", claim.member.memberId], ["National ID", claim.member.nationalId], ["Policy Number", claim.member.policyNumber], ["Insurance Company", claim.insuranceCompany], ["Submitted By", claim.submittedBy], ["Phone Number", claim.member.phone], ["Email", claim.member.email]]} /></section>
            <AIClaimSummary summary={claim.aiSummary} highlights={claim.highlights} confidence={claim.aiConfidence} />
            <UploadedDocuments documents={claim.documents} />
            <UserCorrectionsDisplay claimId={claim.claimDbId} onReviewStateChange={handleCorrectionReviewState} />
            <section className="employee-review-card" aria-labelledby="claim-info-title"><div className="employee-section-heading"><div><p className="employee-eyebrow">Submission details</p><h2 id="claim-info-title">Claim Information</h2></div></div><DetailList items={[["Claim ID", claim.id], ["Invoice Number", claim.invoiceNumber], ["Claim Type", claim.claimType], ["Service Type", claim.serviceType], ["Invoice Date", claim.invoiceDate], ["Hospital or Provider", claim.provider], ["Department", claim.department], ["Claim Amount", formatMoney(claim.amount, claim.currency)], ["Currency", claim.currency], ["Submission Date", claim.submissionDate], ["Current Status", claim.status], ["Priority", claim.priority]]} /></section>
            <AIVerificationChecklist items={claim.verification} />
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
