const formatMoney = (amount, currency) => new Intl.NumberFormat("en-SA", { style: "currency", currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
const formatDate = (date) => new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(`${date}T12:00:00`));

function ClaimsTable({ claims, onOpenClaim }) {
  return (
    <div className="employee-table-scroll">
      <table className="employee-claims-table">
        <caption className="employee-visually-hidden">Assigned reimbursement claims</caption>
        <thead><tr><th>Claim ID</th><th>Member Name</th><th>Insurance Company</th><th>Claim Type</th><th>Service Type</th><th>Submission Date</th><th>Claim Amount</th><th>Priority</th><th>Status</th><th>Assigned To</th><th>Readiness Progress</th><th>Actions</th></tr></thead>
        <tbody>
          {claims.length ? claims.map((claim) => (
            <tr key={claim.id} className={claim.priority === "High" ? "employee-high-priority-row" : ""}>
              <td data-label="Claim ID"><strong className="employee-claim-id">{claim.id}</strong></td>
              <td data-label="Member">{claim.member.name}</td><td data-label="Insurer">Bupa</td><td data-label="Claim Type">{claim.claimType}</td><td data-label="Service Type">{claim.serviceType}</td><td data-label="Submitted">{formatDate(claim.submissionDate)}</td><td data-label="Amount"><strong>{formatMoney(claim.amount, claim.currency)}</strong></td>
              <td data-label="Priority"><span className={`employee-badge employee-priority-${claim.priority.toLowerCase()}`}>{claim.priority}</span></td>
              <td data-label="Status"><span className={`employee-badge employee-status-${claim.status.toLowerCase().replaceAll(" ", "-")}`}>{claim.status}</span></td>
              <td data-label="Assigned To">{claim.assignedTo}</td>
              <td data-label="Readiness"><div className="employee-progress-label"><span>{claim.readiness}%</span></div><div className="employee-progress"><span style={{ width: `${claim.readiness}%` }} /></div></td>
              <td data-label="Action"><button type="button" className="employee-table-action" onClick={() => onOpenClaim(claim)}>{claim.status === "Pending Review" ? "Review" : "Open"}<span aria-hidden="true">→</span></button></td>
            </tr>
          )) : <tr><td colSpan="12" className="employee-empty-state">No claims match the selected filters.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default ClaimsTable;