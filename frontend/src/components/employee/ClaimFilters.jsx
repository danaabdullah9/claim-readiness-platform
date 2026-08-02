const quickFilters = ["All Claims", "My Claims", "High Priority", "Missing Documents", "Ready", "Completed", "Today", "This Week", "Last 30 Days"];

function ClaimFilters({ search, onSearchChange, activeFilter, onFilterChange, resultCount, totalCount }) {
  return (
    <div className="employee-filters">
      <div className="employee-search-row">
        <div className="employee-search-field">
          <span aria-hidden="true">⌕</span>
          <label className="employee-visually-hidden" htmlFor="employee-claim-search">Search claims</label>
          <input id="employee-claim-search" type="search" value={search} onChange={(event) => onSearchChange(event.target.value)} placeholder="Search claim ID, member, national ID, policy or provider" />
        </div>
        <p aria-live="polite">Showing <strong>{resultCount}</strong> of <strong>{totalCount}</strong> Claims</p>
      </div>
      <div className="employee-filter-list" aria-label="Quick filters">
        {quickFilters.map((filter) => (
          <button key={filter} type="button" className={activeFilter === filter ? "is-active" : ""} aria-pressed={activeFilter === filter} onClick={() => onFilterChange(filter)}>{filter}</button>
        ))}
      </div>
    </div>
  );
}

export default ClaimFilters;
