import { useEffect, useState } from "react";
import {
  fetchUserCorrections,
  reviewUserCorrection,
} from "../../services/userCorrections";
import "./UserCorrectionsDisplay.css";

const FIELD_LABELS = {
  PatientName: "Patient Name",
  MemberId: "Member ID",
  NationalId: "National ID",
  PolicyNumber: "Policy Number",
  InsuranceCompany: "Insurance Company",
  InvoiceNumber: "Invoice Number",
  InvoiceDate: "Invoice Date",
  ServiceDate: "Service Date",
  HospitalName: "Hospital Name",
  ProviderName: "Service Provider",
  ProviderType: "Provider Type",
  City: "City",
  DiagnosisCode: "Diagnosis Code",
  DiagnosisDescription: "Diagnosis Description",
  Department: "Department",
  DoctorName: "Doctor Name",
  ClinicalSummary: "Clinical Summary",
  TotalAmount: "Total Amount",
};

function asRecords(data) {
  if (!data) return [];
  return Array.isArray(data) ? data : [data];
}

function recordsHaveUnresolvedCorrections(records) {
  return records.some((record) =>
    (record.corrections || []).some((correction) =>
      ["pending", "additional_information_required"].includes(
        correction.review_status || "pending",
      ),
    ),
  );
}

const STATUS_LABELS = {
  pending: "Pending Human Review",
  accepted: "Accepted by Employee",
  rejected: "Rejected by Employee",
  additional_information_required: "Supporting Document Requested",
};

function CorrectionReviewCard({ claimId, submittedAt, correction, onUpdated }) {
  const status = correction.review_status || "pending";
  const isResolved = status === "accepted" || status === "rejected";
  const [action, setAction] = useState(null);
  const [comment, setComment] = useState("");
  const [documentType, setDocumentType] = useState("Updated Invoice");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  function closeForm() {
    setAction(null);
    setComment("");
    setDocumentType("Updated Invoice");
    setError("");
  }

  async function submitReview(event) {
    event.preventDefault();
    if (action === "rejected" && !comment.trim()) {
      setError("Enter a rejection reason.");
      return;
    }
    if (action === "additional_information_required" && !comment.trim()) {
      setError("Enter a message explaining what supporting document is needed.");
      return;
    }

    setIsSaving(true);
    setError("");
    try {
      const updated = await reviewUserCorrection(claimId, correction.field, {
        submittedAt,
        decision: action,
        employeeComment: comment.trim() || null,
        requestedDocumentType: action === "additional_information_required" ? documentType : null,
        reviewedBy: localStorage.getItem("careflow-demo-employee"),
      });
      onUpdated(updated);
      closeForm();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <article className="employee-correction-comparison">
      <div className="employee-correction-title-row">
        <h3>{FIELD_LABELS[correction.field] || correction.field}</h3>
        <span className={`employee-correction-status employee-correction-status-${status}`}>
          {STATUS_LABELS[status] || status}
        </span>
      </div>
      <div className="employee-correction-values">
        <div className="employee-correction-ai">
          <span>AI Extracted Value</span>
          <p>{String(correction.originalValue ?? "")}</p>
        </div>
        <div className="employee-correction-user">
          <span>User Corrected Value</span>
          <p>{String(correction.correctedValue ?? "")}</p>
        </div>
      </div>
      {correction.reason && (
        <p className="employee-correction-reason"><strong>Correction Reason:</strong> {correction.reason}</p>
      )}

      {correction.final_value !== undefined && correction.final_value !== null && (
        <div className="employee-correction-final">
          <span>Final Verified Value</span>
          <strong>{String(correction.final_value)}</strong>
        </div>
      )}
      <div className="employee-correction-review-meta">
        {correction.reviewed_at && <span><strong>Reviewed:</strong> {correction.reviewed_at}</span>}
        {correction.reviewed_by && <span><strong>Reviewed by:</strong> {correction.reviewed_by}</span>}
        {correction.requested_document_type && <span><strong>Document requested:</strong> {correction.requested_document_type}</span>}
        {correction.employee_comment && <span><strong>Employee comment:</strong> {correction.employee_comment}</span>}
      </div>

      {!isResolved && !action && (
        <div className="employee-correction-actions">
          <button type="button" onClick={() => setAction("accepted")}>Accept Correction</button>
          <button type="button" onClick={() => setAction("rejected")}>Reject Correction</button>
          <button type="button" onClick={() => setAction("additional_information_required")}>Request Supporting Document</button>
        </div>
      )}

      {action && (
        <form className="employee-correction-review-form" onSubmit={submitReview}>
          {action === "accepted" && <p>Confirm that the user-corrected value should be the final verified value.</p>}
          {action === "rejected" && (
            <label>
              Rejection reason
              <textarea value={comment} onChange={(event) => setComment(event.target.value)} required rows="3" />
            </label>
          )}
          {action === "additional_information_required" && (
            <>
              <label>
                Supporting document type
                <select value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
                  <option>Updated Invoice</option>
                  <option>Medical Report</option>
                  <option>Proof of Payment</option>
                  <option>Other</option>
                </select>
              </label>
              <label>
                Message to member
                <textarea value={comment} onChange={(event) => setComment(event.target.value)} required rows="3" />
              </label>
            </>
          )}
          {error && <p className="employee-correction-review-error" role="alert">{error}</p>}
          <div className="employee-correction-form-actions">
            <button type="button" onClick={closeForm} disabled={isSaving}>Cancel</button>
            <button type="submit" disabled={isSaving}>{isSaving ? "Saving..." : "Confirm Decision"}</button>
          </div>
        </form>
      )}
    </article>
  );
}

export default function UserCorrectionsDisplay({ claimId, onReviewStateChange }) {
  const [records, setRecords] = useState([]);
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isActive = true;

    fetchUserCorrections(claimId)
      .then((data) => {
        if (isActive) {
          setRecords(asRecords(data));
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (isActive) {
          setHasError(true);
          setIsLoading(false);
        }
      });

    return () => { isActive = false; };
  }, [claimId]);

  useEffect(() => {
    const hasUnresolved = hasError || recordsHaveUnresolvedCorrections(records);
    onReviewStateChange({ isLoading, hasUnresolved });
  }, [hasError, isLoading, onReviewStateChange, records]);

  function updateCorrection(submittedAt, updatedCorrection) {
    setRecords((current) => current.map((record) => (
      record.submittedAt !== submittedAt
        ? record
        : {
            ...record,
            corrections: (record.corrections || []).map((correction) =>
              correction.field === updatedCorrection.field ? updatedCorrection : correction,
            ),
          }
    )));
  }

  if (hasError) {
    return (
      <section className="employee-review-card employee-corrections" aria-labelledby="user-corrections-title">
        <div className="employee-section-heading">
          <div>
            <p className="employee-eyebrow">User submitted correction</p>
            <h2 id="user-corrections-title">User Corrections</h2>
          </div>
        </div>
        <p className="employee-corrections-error" role="status">Corrections could not be loaded. Claim review is still available.</p>
      </section>
    );
  }

  if (!records.length) return null;

  return (
    <section className="employee-review-card employee-corrections" aria-labelledby="user-corrections-title">
      <div className="employee-section-heading">
        <div>
          <p className="employee-eyebrow">User submitted correction</p>
          <h2 id="user-corrections-title">User Corrections</h2>
        </div>
        <span className="employee-corrections-pending">
          {recordsHaveUnresolvedCorrections(records) ? "Pending Human Review" : "All Corrections Reviewed"}
        </span>
      </div>

      {records.map((record, recordIndex) => (
        <div className="employee-correction-record" key={`${record.submittedAt || "correction"}-${recordIndex}`}>
          <div className="employee-correction-meta">
            {record.submittedAt && <span><strong>Submitted:</strong> {record.submittedAt}</span>}
            {record.status && <span><strong>Submission status:</strong> {record.status}</span>}
          </div>
          {(record.corrections || []).map((correction, correctionIndex) => (
            <CorrectionReviewCard
              key={`${correction.field}-${correctionIndex}`}
              claimId={claimId}
              submittedAt={record.submittedAt}
              correction={correction}
              onUpdated={(updated) => updateCorrection(record.submittedAt, updated)}
            />
          ))}
        </div>
      ))}
    </section>
  );
}
