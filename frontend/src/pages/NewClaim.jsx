import { useRef, useState } from "react";
import "./NewClaim.css";

const claimTypes = [
  {
    value: "Inpatient and Surgery",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 20v-9a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9M4 16h16M8 9V5h4v4M10 3v4M8 5h4" />
      </svg>
    ),
  },
  {
    value: "Dental",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8.5 3.5c1.4 0 2.2.8 3.5.8s2.1-.8 3.5-.8c2.2 0 4 1.9 4 4.4 0 2.2-1 3.8-1.5 5.7-.8 3-1.3 6.9-3.2 6.9-1.5 0-1.2-5.4-2.8-5.4s-1.3 5.4-2.8 5.4c-1.9 0-2.4-3.9-3.2-6.9-.5-1.9-1.5-3.5-1.5-5.7 0-2.5 1.8-4.4 4-4.4Z" />
      </svg>
    ),
  },
  {
    value: "Optical",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M3 13h2M19 13h2M9 13h6M9 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM23 13a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM5 9l2-4M19 9l-2-4" />
      </svg>
    ),
  },
  {
    value: "Others / Outpatient",
    icon: (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 8v8M8 12h8" />
      </svg>
    ),
  },
];

function UploadField({ id, label, file, onChange, onRemove }) {
  const inputRef = useRef(null);

  return (
    <div className="upload-field">
      <div className="upload-heading">
        <label htmlFor={id}>{label}</label>
        <span>Required</span>
      </div>

      <div className={`upload-area${file ? " has-file" : ""}`}>
        <svg className="upload-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 16V4M8 8l4-4 4 4M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" />
        </svg>

        {file ? (
          <>
            <p className="file-name">{file.name}</p>
            <p className="upload-help">Your document is ready.</p>
            <div className="file-actions">
              <button type="button" onClick={() => inputRef.current?.click()}>
                Replace
              </button>
              <button type="button" onClick={onRemove}>
                Remove
              </button>
            </div>
          </>
        ) : (
          <>
            <p>Select or drop your {label.toLowerCase()} here</p>
            <p className="upload-help">PDF, PNG, JPG, or JPEG. One file only.</p>
            <button
              type="button"
              className="choose-file-button"
              onClick={() => inputRef.current?.click()}
            >
              Choose file
            </button>
          </>
        )}

        <input
          ref={inputRef}
          id={id}
          className="visually-hidden"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
          onChange={onChange}
        />
      </div>
    </div>
  );
}

const API_BASE_URL = "http://127.0.0.1:8000";

// 1. Added onSubmitClaim to the props here
function NewClaim({ onBack, onSubmitClaim }) {
  const [selectedClaimType, setSelectedClaimType] = useState("");
  const [invoiceFile, setInvoiceFile] = useState(null);
  const [prescriptionFile, setPrescriptionFile] = useState(null);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isComplete =
    Boolean(selectedClaimType) && Boolean(invoiceFile) && Boolean(prescriptionFile);

  function selectClaimType(claimType) {
    setSelectedClaimType(claimType);
    setHasInteracted(true);
    setSuccessMessage("");
  }

  function updateFile(setFile) {
    return (event) => {
      setFile(event.target.files?.[0] ?? null);
      setHasInteracted(true);
      setSuccessMessage("");
      event.target.value = "";
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setHasInteracted(true);
    setSubmitError("");

    if (!isComplete || isSubmitting) {
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("invoice", invoiceFile);
      formData.append("report", prescriptionFile);

      const response = await fetch(`${API_BASE_URL}/api/analyze-claim`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        const detail =
          typeof result.detail === "string"
            ? result.detail
            : result.detail?.message || "Failed to submit the claim.";
        throw new Error(detail);
      }

      setSuccessMessage("Documents added successfully.");

      // 2. Trigger the summary page transition using the claim saved by the backend
      if (onSubmitClaim) {
        onSubmitClaim(result.claim_id);
      }
    } catch (err) {
      setSubmitError(err.message || "Cannot connect to backend.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="new-claim-page">
      <main className="new-claim-card">
        <button type="button" className="back-button" onClick={onBack}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m15 18-6-6 6-6" />
          </svg>
          Back
        </button>

        <header className="new-claim-header">
          <p className="new-claim-label">Claims Management</p>
          <h1>New Claim</h1>
          <h2>Claim Details</h2>
          <p>Please select the claim type and upload the required documents.</p>
        </header>

        <form onSubmit={handleSubmit} noValidate>
          <fieldset className="claim-type-section">
            <legend>Claim type</legend>
            <div className="claim-type-grid">
              {claimTypes.map((claimType) => {
                const isSelected = selectedClaimType === claimType.value;

                return (
                  <button
                    key={claimType.value}
                    type="button"
                    className={`claim-type-card${isSelected ? " selected" : ""}`}
                    aria-pressed={isSelected}
                    onClick={() => selectClaimType(claimType.value)}
                  >
                    <span className="claim-type-icon">{claimType.icon}</span>
                    <span>{claimType.value}</span>
                  </button>
                );
              })}
            </div>
            {hasInteracted && !selectedClaimType && (
              <p className="field-error">Please select a claim type.</p>
            )}
          </fieldset>

          <section className="documents-section" aria-labelledby="documents-title">
            <div className="section-heading">
              <h2 id="documents-title">Documents</h2>
              <p>Add one file for each required document.</p>
            </div>

            <UploadField
              id="invoice"
              label="Invoice"
              file={invoiceFile}
              onChange={updateFile(setInvoiceFile)}
              onRemove={() => {
                setInvoiceFile(null);
                setHasInteracted(true);
                setSuccessMessage("");
              }}
            />
            {hasInteracted && !invoiceFile && (
              <p className="field-error">Please upload an invoice.</p>
            )}

            <UploadField
              id="medical-prescription"
              label="Medical Prescription"
              file={prescriptionFile}
              onChange={updateFile(setPrescriptionFile)}
              onRemove={() => {
                setPrescriptionFile(null);
                setHasInteracted(true);
                setSuccessMessage("");
              }}
            />
            {hasInteracted && !prescriptionFile && (
              <p className="field-error">
                Please upload a medical prescription.
              </p>
            )}
          </section>

          {successMessage && (
            <p className="success-message" role="status">
              {successMessage}
            </p>
          )}

          {submitError && (
            <p className="field-error" role="alert">
              {submitError}
            </p>
          )}

          <div className="new-claim-actions">
            <button type="button" className="secondary-button" onClick={onBack}>
              Back
            </button>
            <button
              type="submit"
              className="continue-button"
              disabled={!isComplete || isSubmitting}
            >
              {isSubmitting ? "Analyzing..." : "Continue"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default NewClaim;