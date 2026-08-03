import React, { useEffect, useState } from 'react';
import './Summary.css';

const API_BASE_URL = "http://127.0.0.1:8000";

function formatAmount(amount) {
  if (amount === null || amount === undefined) return '';
  return `${Number(amount).toFixed(2)} SAR`;
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

  return (
    <div className="summary-container">
      <h2>Review Your Claim Details</h2>
      <p>Please verify your information before final submission.</p>

      <div className="summary-card">
        <div className="summary-item">
          <strong>Claim ID:</strong> <span>{claim.ClaimID}</span>
        </div>
        <div className="summary-item">
          <strong>Claim Status:</strong> <span>{claim.ClaimStatus}</span>
        </div>
        <div className="summary-item">
          <strong>Patient Name:</strong> <span>{claim.PatientName}</span>
        </div>
        {claim.AccountHolderName && claim.AccountHolderName !== claim.PatientName && (
          <div className="summary-item">
            <strong>Submitted By:</strong> <span>{claim.AccountHolderName}</span>
          </div>
        )}
        <div className="summary-item">
          <strong>National ID:</strong> <span>{claim.NationalId}</span>
        </div>
        <div className="summary-item">
          <strong>Invoice Number:</strong> <span>{claim.InvoiceNumber}</span>
        </div>
        <div className="summary-item">
          <strong>Invoice Date:</strong> <span>{claim.InvoiceDate}</span>
        </div>
        <div className="summary-item">
          <strong>Hospital Name:</strong> <span>{claim.HospitalName}</span>
        </div>
        <div className="summary-item">
          <strong>Provider Type:</strong> <span>{claim.ProviderType}</span>
        </div>
        {claim.City && (
          <div className="summary-item">
            <strong>City:</strong> <span>{claim.City}</span>
          </div>
        )}
        <div className="summary-item">
          <strong>Diagnosis Code:</strong> <span>{claim.DiagnosisCode}</span>
        </div>
        <div className="summary-item">
          <strong>Diagnosis Description:</strong> <span>{claim.DiagnosisDescription}</span>
        </div>
        <div className="summary-item">
          <strong>Doctor Name:</strong> <span>{claim.DoctorName}</span>
        </div>
        <div className="summary-item">
          <strong>Clinical Summary:</strong> <span className="clinical-text">{claim.ClinicalSummary}</span>
        </div>
        <div className="summary-item highlight">
          <strong>Total Amount:</strong> <span>{formatAmount(claim.TotalAmount)}</span>
        </div>
        <div className="summary-item">
          <strong>Submitted At:</strong> <span>{claim.CreatedAt}</span>
        </div>
        {claim.Documents && claim.Documents.length > 0 && (
          <div className="summary-item">
            <strong>Documents:</strong>
            <span>
              {claim.Documents.map((doc) => `${doc.DocumentType}: ${doc.FileName}`).join(', ')}
            </span>
          </div>
        )}
      </div>

      <div className="summary-actions">
        <button className="edit-btn" onClick={onEdit}>Back to Edit</button>
        <button className="submit-btn" onClick={onSubmit}>Confirm & Submit</button>
      </div>
    </div>
  );
};

export default Summary;
