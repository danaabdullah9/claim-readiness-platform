import { useRef, useState } from "react";
import SubmissionSuccess from "./SubmissionSuccess";
import "./NewClaim.css";

const API_BASE_URL = "http://127.0.0.1:8001";

function NewClaim({ onBack, onSubmitClaim, userId }) {
  const [files, setFiles] = useState([]);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [rejections, setRejections] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Added state to control the success popup overlay
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const isComplete = files.length > 0;
  const uploadedCount = files.length;

  function addFiles(incoming) {
    const added = Array.from(incoming || []);
    if (added.length === 0) return;

    setFiles((current) => {
      const merged = [...current];
      added.forEach((file) => {
        // نفس الملف مرتين لا يضيف معلومة، فنتجاهله بدل إرساله للتحليل
        const duplicate = merged.some(
          (existing) =>
            existing.name === file.name &&
            existing.size === file.size &&
            existing.lastModified === file.lastModified,
        );
        if (!duplicate && merged.length < 8) merged.push(file);
      });
      return merged;
    });

    setHasInteracted(true);
    setSuccessMessage("");
    setRejections([]);
    setSubmitError("");
  }

  function removeFile(index) {
    setFiles((current) => current.filter((_, position) => position !== index));
    setRejections([]);
    setSubmitError("");
  }

  function onDrop(event) {
    event.preventDefault();
    setIsDragging(false);
    addFiles(event.dataTransfer?.files);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setHasInteracted(true);
    setSubmitError("");
    setRejections([]);

    if (!isComplete || isSubmitting) {
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      files.forEach((file) => formData.append("files", file));
      if (userId) {
        formData.append("user_id", userId);
      }

      const response = await fetch(`${API_BASE_URL}/api/analyze-claim`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        const reasons = result.detail?.rejections;
        if (Array.isArray(reasons) && reasons.length > 0) {
          setRejections(reasons);
          return;
        }

        const detail =
          typeof result.detail === "string"
            ? result.detail
            : result.detail?.message || "Failed to submit the claim.";
        throw new Error(detail);
      }

      setSuccessMessage("Documents added successfully.");

      // Trigger the success modal popup instead of immediately transitioning away
      setIsSubmitted(true);

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
          <p className="new-claim-greeting">Welcome back</p>
          <h1>Start a New Claim</h1>
          <p>Let's prepare your reimbursement claim.</p>
        </header>

        <ol className="claim-progress" aria-label="Claim submission progress">
          {[
            "Upload Documents",
            "AI Review",
            "Verify Information",
            "Submit Claim",
          ].map((step, index) => (
            <li key={step} className={index === 0 ? "active" : ""} aria-current={index === 0 ? "step" : undefined}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
            </li>
          ))}
        </ol>

        <form onSubmit={handleSubmit} noValidate>
          <section className="documents-section" aria-labelledby="documents-title">
            <div className="section-heading">
              <div>
                <h2 id="documents-title">Documents</h2>
                <span className="required-count">Invoice + medical report</span>
              </div>
              <p>{uploadedCount} file{uploadedCount === 1 ? "" : "s"} attached</p>
            </div>

            <p className="dropzone-hint">
              Attach the invoice, the medical report, and anything else related to this
              treatment. If a single document already contains the billing and the clinical
              details, that one file is enough — we check the information, not the number of
              files.
            </p>

            <div
              className={`dropzone${isDragging ? " is-dragging" : ""}`}
              onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input
                id="claim-files"
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.webp"
                onChange={(event) => { addFiles(event.target.files); event.target.value = ""; }}
              />
              <label htmlFor="claim-files">
                <span className="dropzone-icon" aria-hidden="true">↑</span>
                <strong>Drop your files here, or browse</strong>
                <small>PDF, PNG or JPG · up to 8 files</small>
              </label>
            </div>

            {files.length > 0 && (
              <ul className="file-list">
                {files.map((file, index) => (
                  <li key={`${file.name}-${file.lastModified}`}>
                    <span className="file-icon" aria-hidden="true">▤</span>
                    <span className="file-meta">
                      <strong>{file.name}</strong>
                      <small>{(file.size / 1024).toFixed(0)} KB</small>
                    </span>
                    <button
                      type="button"
                      className="file-remove"
                      aria-label={`Remove ${file.name}`}
                      onClick={() => removeFile(index)}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {hasInteracted && files.length === 0 && (
              <p className="field-error">Attach at least one document to continue.</p>
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

          {rejections.length > 0 && (
            <section className="rejection-panel" role="alert" aria-labelledby="rejection-title">
              <div className="rejection-head">
                <span className="rejection-icon" aria-hidden="true">×</span>
                <div>
                  <strong id="rejection-title">
                    This claim cannot be submitted
                  </strong>
                  <small>
                    {rejections.length === 1
                      ? "1 issue was found in the uploaded documents."
                      : `${rejections.length} issues were found in the uploaded documents.`}
                  </small>
                </div>
              </div>

              <ol className="rejection-list">
                {rejections.map((item, index) => (
                  <li key={item.code + index}>
                    <strong>{item.title}</strong>
                    <p>{item.detail}</p>
                  </li>
                ))}
              </ol>

              <p className="rejection-footer">
                Please correct the documents and upload them again. Nothing was saved.
              </p>
            </section>
          )}

          <div className="new-claim-actions">
            {!isComplete && (
              <p>Upload all required documents to continue.</p>
            )}
            <button
              type="submit"
              className="continue-button"
              disabled={!isComplete || isSubmitting}
            >
              {isSubmitting ? "Analyzing..." : "Continue"}
            </button>
          </div>
        </form>

        {/* Display the Success Popup Modal once submission finishes successfully */}
        {isSubmitted && (
          <SubmissionSuccess onClose={() => window.location.reload()} />
        )}
      </main>
    </div>
  );
}

export default NewClaim;