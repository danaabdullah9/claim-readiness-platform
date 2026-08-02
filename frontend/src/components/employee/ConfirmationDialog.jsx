import { useEffect } from "react";

function ConfirmationDialog({ action, claimId, onConfirm, onCancel }) {
  useEffect(() => {
    if (!action) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [action, onCancel]);

  if (!action) return null;

  return (
    <div className="employee-modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}>
      <section className="employee-modal employee-confirmation-modal" role="alertdialog" aria-modal="true" aria-labelledby="employee-confirm-title" aria-describedby="employee-confirm-description">
        <span className="employee-confirm-icon" aria-hidden="true">?</span>
        <h2 id="employee-confirm-title">Confirm {action.label}</h2>
        <p id="employee-confirm-description">Are you sure you want to {action.prompt} claim <strong>{claimId}</strong>?</p>
        <div><button type="button" onClick={onCancel}>Cancel</button><button type="button" className={action.tone === "danger" ? "is-danger" : "is-primary"} onClick={onConfirm}>Confirm {action.label}</button></div>
      </section>
    </div>
  );
}

export default ConfirmationDialog;
