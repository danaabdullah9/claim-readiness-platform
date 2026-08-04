import { useEffect, useState } from 'react';
import './Summary.css';
import { fetchUserCorrections, submitUserCorrections } from '../services/userCorrections';

const API_BASE_URL = "http://127.0.0.1:8001";

function formatAmount(amount) {
  if (amount === null || amount === undefined) return '';
  return `${Number(amount).toFixed(2)} SAR`;
}

const EDITABLE_FIELDS = new Set([
  'PatientName', 'InvoiceNumber', 'InvoiceDate', 'ServiceDate', 'HospitalName',
  'ProviderName', 'DiagnosisCode', 'DiagnosisDescription', 'Department',
  'DoctorName', 'ClinicalSummary', 'TotalAmount',
]);

function Row({ field, label, value, originalValue, isEditing, onChange, type = 'text', multiline = false, formatValue }) {
  const editable = EDITABLE_FIELDS.has(field);
  if (!editable && (value === null || value === undefined || value === '')) return null;
  const edited = editable && String(value) !== String(originalValue ?? '');
  const Input = multiline ? 'textarea' : 'input';
  return (
    <div className={`summary-item${edited ? ' edited' : ''}`}>
      <div className="summary-field-label">
        <strong>{label}</strong>
        {edited && <span className="edited-badge">Edited</span>}
      </div>
      {isEditing && editable ? (
        <Input
          aria-label={label}
          type={multiline ? undefined : type}
          value={value}
          rows={multiline ? 4 : undefined}
          onChange={(event) => onChange(field, event.target.value)}
        />
      ) : (
        <span className={multiline ? 'clinical-text' : undefined}>
          {formatValue ? formatValue(value) : value}
        </span>
      )}
      {edited && <small className="original-value">Originally extracted: {String(originalValue ?? 'Not extracted')}</small>}
    </div>
  );
}

function Section({ title, children }) {
  return <section className="summary-section"><h3>{title}</h3><div className="summary-grid">{children}</div></section>;
}

const Summary = ({ claimId, onSubmit, onEdit }) => {
  const [claim, setClaim] = useState(null);
  const [isLoading, setIsLoading] = useState(Boolean(claimId));
  const [error, setError] = useState(claimId ? "" : "No claim was submitted.");
  const [displayValues, setDisplayValues] = useState({});
  const [draftValues, setDraftValues] = useState({});
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    if (!claimId) {
      return;
    }

    let isCancelled = false;

    async function fetchClaim() {
      setIsLoading(true);
      setError("");

      try {
        const response = await fetch(`${API_BASE_URL}/api/claims/${claimId}`);
        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.detail || "Failed to load the claim.");
        }

        const values = { ...result.data };
        try {
          const correctionRecord = await fetchUserCorrections(claimId);
          correctionRecord?.corrections?.forEach((correction) => {
            values[correction.field] = correction.final_value != null
              ? correction.final_value
              : correction.review_status === 'rejected'
                ? correction.originalValue
                : correction.correctedValue;
          });
        } catch {
          // Correction lookup must never block review of the original claim.
        }

        if (!isCancelled) {
          setClaim(result.data);
          setDisplayValues(values);
          setDraftValues(values);
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err.message || "Cannot connect to backend.");
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchClaim();

    return () => {
      isCancelled = true;
    };
  }, [claimId]);

  function startEditing() {
    setDraftValues(displayValues);
    setSaveMessage("");
    setSaveError("");
    setIsEditing(true);
  }

  function cancelEditing() {
    setDraftValues(displayValues);
    setSaveError("");
    setIsEditing(false);
  }

  function updateDraft(field, value) {
    setDraftValues((current) => ({ ...current, [field]: value }));
  }

  async function saveChanges() {
    const corrections = [...EDITABLE_FIELDS]
      .filter((field) => String(draftValues[field] ?? '').trim() !== String(claim[field] ?? '').trim())
      .map((field) => ({ field, correctedValue: String(draftValues[field] ?? '').trim() }));

    if (!corrections.length) {
      setSaveMessage("No changes were made.");
      setSaveError("");
      setIsEditing(false);
      return;
    }

    if (corrections.some((correction) => !correction.correctedValue)) {
      setSaveError("Corrected values cannot be empty.");
      return;
    }

    setIsSaving(true);
    setSaveError("");
    try {
      await submitUserCorrections(claimId, corrections);
      setDisplayValues(draftValues);
      setSaveMessage("Your changes have been saved and will be reviewed by an employee.");
      setIsEditing(false);
    } catch (requestError) {
      setSaveError(requestError.message || "Unable to save your changes.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="summary-container">
        <h2>Review Your Claim Details</h2>
        <p>Loading claim...</p>
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="summary-container">
        <h2>Review Your Claim Details</h2>
        <p className="field-error" role="alert">{error || "Claim not found."}</p>
        <div className="summary-actions">
          <button className="edit-btn" onClick={onEdit}>Back to Edit</button>
        </div>
      </div>
    );
  }

  // نتيجة تدقيق الـ AI: كانت تُحسب في الباك إند ثم تُرمى قبل الوصول للواجهة
  const verification = claim.Verification;
  const matchStatus = verification?.MatchStatus || 'success';
  const isRejected = verification?.IsValid === false || matchStatus === 'rejected';
  const isWarning = !isRejected && matchStatus === 'warning';

  const tone = isRejected ? 'failed' : isWarning ? 'warning' : 'passed';
  const title = isRejected
    ? 'Verification failed — the invoice and the report do not match'
    : isWarning
    ? 'Verified with minor differences'
    : 'Verified — the invoice matches the medical report';

  return (
    <div className="summary-container">
      <div className="summary-header">
        <h2>Review Your Claim Details</h2>
        <p>Please verify your information before final submission.</p>
      </div>

      {verification && (
        <div className={`verification-banner ${tone}`} role="status">
          <div className="verification-head">
            <span className="verification-icon" aria-hidden="true">
              {isRejected ? '×' : isWarning ? '!' : '✓'}
            </span>
            <div>
              <strong>{title}</strong>
              {verification.Confidence != null && (
                <small>AI confidence: {verification.Confidence}%</small>
              )}
            </div>
          </div>

          {verification.ValidationMessage && (
            <p className="verification-message">{verification.ValidationMessage}</p>
          )}

          {verification.Discrepancies?.length > 0 && (
            <ul className="discrepancy-list">
              {verification.Discrepancies.map((item, index) => (
                <li key={index}>
                  <span className={`severity ${item.severity || 'low'}`}>
                    {(item.severity || 'low') === 'high' ? 'HIGH' : 'LOW'}
                  </span>
                  <div>
                    <strong>{item.field}</strong>
                    <small>
                      Invoice: {String(item.invoice_value)} · Report: {String(item.report_value)}
                    </small>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {verification.CoverageHint && (
            <p className="coverage-hint">{verification.CoverageHint}</p>
          )}
        </div>
      )}

      <div className="summary-card">
        <Section title="Claim Overview">
          <Row label="Claim ID" value={claim.ClaimRef || `#${claim.ClaimID}`} />
          {claim.ClaimRef && <Row label="Reference No" value={`#${claim.ClaimID}`} />}
          <Row label="Claim Status" value={claim.ClaimStatus} />
          <Row label="Claim Type" value={claim.ClaimType} />
          <Row label="Submitted At" value={claim.CreatedAt} />
        </Section>

        <Section title="Member Details">
          <Row field="PatientName" label="Patient Name" value={isEditing ? draftValues.PatientName : displayValues.PatientName} originalValue={claim.PatientName} isEditing={isEditing} onChange={updateDraft} />
          {claim.AccountHolderName && claim.AccountHolderName !== claim.PatientName && <Row label="Submitted By" value={claim.AccountHolderName} />}
          <Row label="Member ID" value={claim.MemberId} />
          <Row label="National ID" value={claim.NationalId} />
          <Row label="Policy Number" value={claim.PolicyNumber} />
          <Row label="Insurance Company" value={claim.InsuranceCompany} />
        </Section>

        <Section title="Provider Details">
          <Row field="HospitalName" label="Hospital Name" value={isEditing ? draftValues.HospitalName : displayValues.HospitalName} originalValue={claim.HospitalName} isEditing={isEditing} onChange={updateDraft} />
          <Row field="ProviderName" label="Service Provider" value={isEditing ? draftValues.ProviderName : displayValues.ProviderName} originalValue={claim.ProviderName} isEditing={isEditing} onChange={updateDraft} />
          <Row label="Provider Type" value={claim.ProviderType} />
          <Row label="City" value={claim.City} />
          <Row field="Department" label="Department" value={isEditing ? draftValues.Department : displayValues.Department} originalValue={claim.Department} isEditing={isEditing} onChange={updateDraft} />
          <Row field="DoctorName" label="Doctor Name" value={isEditing ? draftValues.DoctorName : displayValues.DoctorName} originalValue={claim.DoctorName} isEditing={isEditing} onChange={updateDraft} />
        </Section>

        <Section title="Medical Details">
          <Row field="DiagnosisCode" label="Diagnosis Code" value={isEditing ? draftValues.DiagnosisCode : displayValues.DiagnosisCode} originalValue={claim.DiagnosisCode} isEditing={isEditing} onChange={updateDraft} />
          <Row field="DiagnosisDescription" label="Diagnosis Description" value={isEditing ? draftValues.DiagnosisDescription : displayValues.DiagnosisDescription} originalValue={claim.DiagnosisDescription} isEditing={isEditing} onChange={updateDraft} multiline />
          <Row field="ClinicalSummary" label="Clinical Summary" value={isEditing ? draftValues.ClinicalSummary : displayValues.ClinicalSummary} originalValue={claim.ClinicalSummary} isEditing={isEditing} onChange={updateDraft} multiline />
        </Section>

        <Section title="Invoice Details">
          <Row field="InvoiceNumber" label="Invoice Number" value={isEditing ? draftValues.InvoiceNumber : displayValues.InvoiceNumber} originalValue={claim.InvoiceNumber} isEditing={isEditing} onChange={updateDraft} />
          <Row field="InvoiceDate" label="Invoice Date" value={isEditing ? draftValues.InvoiceDate : displayValues.InvoiceDate} originalValue={claim.InvoiceDate} isEditing={isEditing} onChange={updateDraft} type="date" />
          <Row field="ServiceDate" label="Service Date" value={isEditing ? draftValues.ServiceDate : displayValues.ServiceDate} originalValue={claim.ServiceDate} isEditing={isEditing} onChange={updateDraft} type="date" />
          <Row field="TotalAmount" label="Total Amount (SAR)" value={isEditing ? draftValues.TotalAmount : displayValues.TotalAmount} originalValue={claim.TotalAmount} isEditing={isEditing} onChange={updateDraft} type="number" formatValue={formatAmount} />
        </Section>

        {claim.Documents && claim.Documents.length > 0 && (
          <Section title="Documents">
            <div className="summary-item documents-item">
              <span className="document-list">
                {claim.Documents.map((doc) => (
                  <span className="document-chip" key={doc.DocumentID}>
                    {doc.DocumentType}: {doc.FileName}
                  </span>
                ))}
              </span>
            </div>
          </Section>
        )}
      </div>

      {saveMessage && <p className="summary-success" role="status">{saveMessage}</p>}
      {saveError && <p className="field-error summary-save-error" role="alert">{saveError}</p>}

      <div className="summary-actions">
        {isEditing ? (
          <>
            <button className="edit-btn" type="button" onClick={cancelEditing} disabled={isSaving}>Cancel Editing</button>
            <button className="submit-btn" type="button" onClick={saveChanges} disabled={isSaving}>
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </>
        ) : (
          <>
            <button className="edit-btn" type="button" onClick={startEditing}>Edit Information</button>
            <button className="submit-btn" onClick={onSubmit} disabled={isRejected}>
              {isRejected ? 'Cannot Submit' : 'Confirm & Submit'}
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default Summary;
