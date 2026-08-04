import { useRef, useState } from "react";
import "./NewClaim.css";

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

const API_BASE_URL = "http://127.0.0.1:8001";

// 1. Added onSubmitClaim to the props here
function NewClaim({ onBack, onSubmitClaim, userId }) {
  const [invoiceFile, setInvoiceFile] = useState(null);
  const [prescriptionFile, setPrescriptionFile] = useState(null);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [rejections, setRejections] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isComplete = Boolean(invoiceFile) && Boolean(prescriptionFile);

  function updateFile(setFile) {
    return (event) => {
      setFile(event.target.files?.[0] ?? null);
      setHasInteracted(true);
      setSuccessMessage("");
      setRejections([]);
      setSubmitError("");
      event.target.value = "";
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setHasInteracted(true);
    setSubmitError("");
    setRejections([]);

    if (!isComplete || isSubmitting) {
      return;
    }

    // حارس: نفس الملف في الخانتين = الفاتورة ما تنقرأ أبدًا
    if (
      invoiceFile.name === prescriptionFile.name &&
      invoiceFile.size === prescriptionFile.size &&
      invoiceFile.lastModified === prescriptionFile.lastModified
    ) {
      setSubmitError(
        "You uploaded the same file twice. Please add the invoice in the Invoice field."
      );
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();
      formData.append("invoice", invoiceFile);
      formData.append("report", prescriptionFile);
      if (userId) {
        formData.append("user_id", userId);
      }

      const response = await fetch(`${API_BASE_URL}/api/analyze-claim`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        // 422 مع قائمة أسباب = المطالبة رُفضت بقواعد القبول، فنعرضها ولا ننتقل
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
          <p>Upload the required documents. Claim details will be extracted automatically.</p>
        </header>

        <form onSubmit={handleSubmit} noValidate>
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

          {/* أسباب رفض المطالبة: تُعرض هنا ولا يُسمح بالانتقال لصفحة الملخص */}
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
