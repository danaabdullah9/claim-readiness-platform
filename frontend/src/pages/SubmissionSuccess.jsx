import React from 'react';
import './SubmissionSuccess.css';

export default function SubmissionSuccess({ onClose }) {
  return (
    <div className="success-overlay">
      <div className="success-modal">
        <h2 className="success-title">Claim Submitted!</h2>
        
        <div className="success-icon-container">
          <div className="success-circle">
            <svg className="success-checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
              <path className="checkmark-check" fill="none" d="M14 27 l10 10 l20 -20" />
            </svg>
          </div>
        </div>

        <p className="success-message">
          Your claim has been successfully submitted and is currently under review by the claims team.
        </p>

        {onClose && (
          <button className="success-btn" onClick={onClose}>
            Back to Dashboard
          </button>
        )}
      </div>
    </div>
  );
}