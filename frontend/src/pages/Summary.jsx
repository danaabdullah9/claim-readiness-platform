import React, { useEffect, useState } from 'react';
import './Summary.css';

const API_BASE_URL = "http://127.0.0.1:8001";

function formatAmount(amount) {
  if (amount === null || amount === undefined) return '';
  return `${Number(amount).toFixed(2)} SAR`;
}

function Row({ label, value }) {
  if (value === null || value === undefined || value === '') return null;
  return (
    <div className="summary-item">
      <strong>{label}:</strong> <span>{value}</span>
    </div>
  );
}

const Summary = ({ claimId, onSubmit, onEdit }) => {
  const [claim, setClaim] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!claimId) {
      setIsLoading(false);
      setError("No claim was submitted.");
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

        if (!isCancelled) {
          setClaim(result.data);
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
        <p className="summary-group-title">Claim</p>
        <Row label="Claim ID" value={claim.ClaimRef || `#${claim.ClaimID}`} />
        {claim.ClaimRef && <Row label="Reference No" value={`#${claim.ClaimID}`} />}
        <Row label="Claim Status" value={claim.ClaimStatus} />
        <Row label="Claim Type" value={claim.ClaimType} />

        <p className="summary-group-title">Member</p>
        <Row label="Patient Name" value={claim.PatientName} />
        {claim.AccountHolderName && claim.AccountHolderName !== claim.PatientName && (
          <Row label="Submitted By" value={claim.AccountHolderName} />
        )}
        <Row label="Member ID" value={claim.MemberId} />
        <Row label="National ID" value={claim.NationalId} />
        <Row label="Policy Number" value={claim.PolicyNumber} />
        <Row label="Insurance Company" value={claim.InsuranceCompany} />

        <p className="summary-group-title">Invoice</p>
        <Row label="Invoice Number" value={claim.InvoiceNumber} />
        <Row label="Invoice Date" value={claim.InvoiceDate} />
        <Row label="Service Date" value={claim.ServiceDate} />
        <Row label="Hospital Name" value={claim.HospitalName} />
        <Row label="Service Provider" value={claim.ProviderName} />
        <Row label="Provider Type" value={claim.ProviderType} />
        <Row label="City" value={claim.City} />

        <p className="summary-group-title">Medical</p>
        <Row label="Diagnosis Code" value={claim.DiagnosisCode} />
        <Row label="Diagnosis Description" value={claim.DiagnosisDescription} />
        <Row label="Department" value={claim.Department} />
        <Row label="Doctor Name" value={claim.DoctorName} />
        {claim.ClinicalSummary && (
          <div className="summary-item">
            <strong>Clinical Summary:</strong>
            <span className="clinical-text">{claim.ClinicalSummary}</span>
          </div>
        )}

        <div className="summary-item highlight">
          <strong>Total Amount:</strong> <span>{formatAmount(claim.TotalAmount)}</span>
        </div>

        <Row label="Submitted At" value={claim.CreatedAt} />

        {claim.Documents && claim.Documents.length > 0 && (
          <div className="summary-item">
            <strong>Documents:</strong>
            <span className="document-list">
              {claim.Documents.map((doc) => (
                <span className="document-chip" key={doc.DocumentID}>
                  {doc.DocumentType}: {doc.FileName}
                </span>
              ))}
            </span>
          </div>
        )}
      </div>

      <div className="summary-actions">
        <button className="edit-btn" onClick={onEdit}>Back to Edit</button>
        <button className="submit-btn" onClick={onSubmit} disabled={isRejected}>
          {isRejected ? 'Cannot Submit' : 'Confirm & Submit'}
        </button>
      </div>
    </div>
  );
};

export default Summary;