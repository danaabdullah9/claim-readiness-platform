const cardConfig = [
  ["Assigned to Me", "assigned", "briefcase"],
  ["Pending Review", "pending", "clock"],
  ["Waiting for Member", "waiting", "person"],
  ["Ready for Submission", "ready", "check"],
  ["Completed Today", "completed", "spark"],
];

const filterMap = {
  assigned: "My Claims",
  pending: "Pending Review",
  waiting: "Waiting for Member",
  ready: "Ready",
  completed: "Completed",
};

function SummaryCards({ counts, activeFilter, onFilterChange }) {
  return (
    <section className="employee-summary-grid" aria-label="Claims summary">
      {cardConfig.map(([label, key, icon]) => (
        <button
          type="button"
          className={`employee-summary-card${activeFilter === filterMap[key] ? " is-active" : ""}`}
          key={key}
          aria-pressed={activeFilter === filterMap[key]}
          onClick={() => onFilterChange(filterMap[key])}
        >
          <span className={`employee-summary-icon employee-icon-${icon}`} aria-hidden="true" />
          <div>
            <p>{label}</p>
            <strong>{counts[key]}</strong>
          </div>
        </button>
      ))}
    </section>
  );
}

export default SummaryCards;
