import React from 'react';
import './Summary.css';

const Summary = ({ formData, onSubmit, onEdit }) => {
  return (
    <div className="summary-container">
      <h2>Review Your Claim Details</h2>
      <p>Please verify your information before final submission.</p>

      <div className="summary-card">
        <div className="summary-item">
          <strong>Member ID:</strong> <span>{formData.MemberId}</span>
        </div>
        <div className="summary-item">
          <strong>National ID:</strong> <span>{formData.NationalId}</span>
        </div>
        <div className="summary-item">
          <strong>Patient Name:</strong> <span>{formData.PatientName}</span>
        </div>
        <div className="summary-item">
          <strong>Invoice Number:</strong> <span>{formData.InvoiceNumber}</span>
        </div>
        <div className="summary-item">
          <strong>Invoice Date:</strong> <span>{formData.InvoiceDate}</span>
        </div>
        <div className="summary-item">
          <strong>Hospital Name:</strong> <span>{formData.HospitalName}</span>
        </div>
        <div className="summary-item">
          <strong>Diagnosis Code:</strong> <span>{formData.DiagnosisCode}</span>
        </div>
        <div className="summary-item">
          <strong>Diagnosis Description:</strong> <span>{formData.DiagnosisDescription}</span>
        </div>
        <div className="summary-item">
          <strong>Doctor Name:</strong> <span>{formData.DoctorName}</span>
        </div>
        <div className="summary-item">
          <strong>Clinical Summary:</strong> <span className="clinical-text">{formData.ClinicalSummary}</span>
        </div>
        <div className="summary-item highlight">
          <strong>Total Amount:</strong> <span>{formData.TotalAmount}</span>
        </div>
      </div>

      <div className="summary-actions">
        <button className="edit-btn" onClick={onEdit}>Back to Edit</button>
        <button className="submit-btn" onClick={onSubmit}>Confirm & Submit</button>
      </div>
    </div>
  );
};

export default Summary;