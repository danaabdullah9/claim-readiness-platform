import { useEffect, useMemo, useState } from "react";
import {
  fetchUserCorrections,
  submitUserCorrections,
} from "../services/userCorrections";
import "./UserCorrectionsPanel.css";

const FIELD_GROUPS = [
  ["PatientName", "Patient Name"],
  ["MemberId", "Member ID"],
  ["NationalId", "National ID"],
  ["PolicyNumber", "Policy Number"],
  ["InsuranceCompany", "Insurance Company"],
  ["InvoiceNumber", "Invoice Number"],
  ["InvoiceDate", "Invoice Date"],
  ["ServiceDate", "Service Date"],
  ["HospitalName", "Hospital Name"],
  ["ProviderName", "Service Provider"],
  ["ProviderType", "Provider Type"],
  ["City", "City"],
  ["DiagnosisCode", "Diagnosis Code"],
  ["DiagnosisDescription", "Diagnosis Description"],
  ["Department", "Department"],
  ["DoctorName", "Doctor Name"],
  ["ClinicalSummary", "Clinical Summary"],
  ["TotalAmount", "Total Amount (SAR)"],
];

function CorrectionField({ field, label, originalValue, value, onChange }) {
  const isLongText = field === "ClinicalSummary" || field === "DiagnosisDescription";
  const Input = isLongText ? "textarea" : "input";

  return (
    <div className="correction-field">
      <label htmlFor={`correction-${field}`}>{label}</label>
      <div className="correction-value-block">
        <small>AI Extracted Value</small>
        <span>{String(originalValue ?? "Not extracted")}</span>
      </div>
      <span className="correction-arrow" aria-hidden="true">↓</span>
      <Input
        id={`correction-${field}`}
        value={value.correctedValue}
        onChange={(event) => onChange(field, "correctedValue", event.target.value)}
        placeholder="User corrected value"
        rows={isLongText ? 3 : undefined}
      />
      <input
        aria-label={`Reason for correcting ${label}`}
        value={value.reason}
        onChange={(event) => onChange(field, "reason", event.target.value)}
        placeholder="Optional reason for correction"
      />
    </div>
  );
}

export default function UserCorrectionsPanel({ claim, claimId }) {
  const emptyValues = useMemo(
    () => Object.fromEntries(FIELD_GROUPS.map(([field]) => [field, { correctedValue: "", reason: "" }])),
    [],
  );
  const [isOpen, setIsOpen] = useState(false);
  const [values, setValues] = useState(emptyValues);
  const [submitted, setSubmitted] = useState(null);
  const [error, setError] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    let active = true;
    fetchUserCorrections(claimId)
      .then((record) => {
        if (active) setSubmitted(record);
      })
      .catch(() => {
        // A correction lookup must never block review of the original claim.
      });
    return () => { active = false; };
  }, [claimId]);

  function updateValue(field, property, value) {
    setValues((current) => ({
      ...current,
      [field]: { ...current[field], [property]: value },
    }));
  }

  function cancel() {
    setValues(emptyValues);
    setError("");
    setIsOpen(false);
  }

  async function submit(event) {
    event.preventDefault();
    const corrections = FIELD_GROUPS
      .filter(([field]) => values[field].correctedValue.trim())
      .map(([field]) => ({ field, ...values[field] }));

    if (!corrections.length) {
      setError("Enter at least one corrected value.");
      return;
    }

    setIsSaving(true);
    setError("");
    try {
      const record = await submitUserCorrections(claimId, corrections);
      setSubmitted(record);
      setValues(emptyValues);
      setIsOpen(false);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="corrections-panel" aria-labelledby="corrections-title">
      <div className="corrections-heading">
        <div>
          <h3 id="corrections-title">User Corrections</h3>
          <p>AI extracted values remain unchanged.</p>
        </div>
        {submitted && <span className="corrections-badge">User Corrections Pending</span>}
      </div>

      {submitted && (
        <div className="correction-summary">
          {submitted.corrections.map((item) => (
            <div className="correction-summary-row" key={item.field}>
              <strong>{FIELD_GROUPS.find(([field]) => field === item.field)?.[1] || item.field}</strong>
              <span><small>AI:</small> {String(item.originalValue ?? "Not extracted")}</span>
              <span><small>User:</small> {item.correctedValue}</span>
              {item.reason && <span><small>Reason:</small> {item.reason}</span>}
            </div>
          ))}
        </div>
      )}

      {!isOpen ? (
        <button className="report-incorrect-btn" type="button" onClick={() => setIsOpen(true)}>
          Report Incorrect Information
        </button>
      ) : (
        <form onSubmit={submit}>
          <p className="correction-instructions">Only fill in fields that need correction.</p>
          {FIELD_GROUPS.map(([field, label]) => (
            <CorrectionField
              key={field}
              field={field}
              label={label}
              originalValue={claim[field]}
              value={values[field]}
              onChange={updateValue}
            />
          ))}
          {error && <p className="field-error" role="alert">{error}</p>}
          <div className="correction-actions">
            <button className="edit-btn" type="button" onClick={cancel} disabled={isSaving}>Cancel</button>
            <button className="submit-btn" type="submit" disabled={isSaving}>
              {isSaving ? "Submitting..." : "Submit Corrections"}
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
