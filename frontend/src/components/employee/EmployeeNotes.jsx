function EmployeeNotes({ value, onChange }) {
  return (
    <section className="employee-review-card" aria-labelledby="notes-title">
      <div className="employee-section-heading"><div><p className="employee-eyebrow">Internal only</p><h2 id="notes-title">Employee Notes</h2></div></div>
      <label className="employee-visually-hidden" htmlFor="employee-review-notes">Internal review notes</label>
      <textarea id="employee-review-notes" value={value} onChange={(event) => onChange(event.target.value)} rows="5" placeholder="Add findings, follow-up details, or a handoff note…" />
      <p className="employee-field-note">Notes are temporary and will not be saved to the backend.</p>
    </section>
  );
}

export default EmployeeNotes;
