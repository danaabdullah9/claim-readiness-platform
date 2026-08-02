import { useMemo, useState } from "react";
import SummaryCards from "../../components/employee/SummaryCards";
import ClaimFilters from "../../components/employee/ClaimFilters";
import ClaimsTable from "../../components/employee/ClaimsTable";
import EmployeeLogin from "../../components/employee/EmployeeLogin";
import { demoEmployees, employeeClaims } from "../../data/employeeClaims";
import "./EmployeeDashboard.css";

const DAY = 24 * 60 * 60 * 1000;

function matchesFilter(claim, filter) {
  const age = (new Date("2026-08-02T12:00:00") - new Date(`${claim.submissionDate}T12:00:00`)) / DAY;
  if (filter === "My Claims") return true;
  if (filter === "Pending Review") return ["Pending Review", "Under Review"].includes(claim.status);
  if (filter === "Waiting for Member") return claim.status === "Waiting for Member";
  if (filter === "High Priority") return claim.priority === "High";
  if (filter === "Missing Documents") return claim.missingDocuments.length > 0;
  if (filter === "Ready") return claim.status === "Ready for Submission";
  if (filter === "Completed") return claim.status === "Completed";
  if (filter === "Today") return age === 0;
  if (filter === "This Week") return age >= 0 && age <= 7;
  if (filter === "Last 30 Days") return age >= 0 && age <= 30;
  return true;
}

function EmployeeDashboard({ onOpenClaim }) {
  const [employee, setEmployee] = useState(() => {
    const storedEmployeeId = localStorage.getItem("careflow-demo-employee");
    return demoEmployees.find((item) => item.id === storedEmployeeId) ?? null;
  });
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("All Claims");

  const assignedClaims = useMemo(
    () => employeeClaims.filter((claim) => claim.assignedTo === employee?.name),
    [employee],
  );

  const filteredClaims = useMemo(() => {
    const term = search.trim().toLowerCase();
    return assignedClaims.filter((claim) => {
      const searchable = [claim.id, claim.member.name, claim.member.nationalId, claim.member.policyNumber, claim.provider].join(" ").toLowerCase();
      return (!term || searchable.includes(term)) && matchesFilter(claim, activeFilter);
    });
  }, [assignedClaims, search, activeFilter]);

  const counts = {
    assigned: assignedClaims.length,
    pending: assignedClaims.filter((claim) => ["Pending Review", "Under Review", "Missing Documents"].includes(claim.status)).length,
    waiting: assignedClaims.filter((claim) => claim.status === "Waiting for Member").length,
    ready: assignedClaims.filter((claim) => claim.status === "Ready for Submission").length,
    completed: assignedClaims.filter((claim) => claim.status === "Completed" && claim.completionDate === "2026-08-02").length,
  };

  function handleLogin(selectedEmployee) {
    localStorage.setItem("careflow-demo-employee", selectedEmployee.id);
    setEmployee(selectedEmployee);
    setSearch("");
    setActiveFilter("All Claims");
  }

  function handleLogout() {
    localStorage.removeItem("careflow-demo-employee");
    setEmployee(null);
    setSearch("");
    setActiveFilter("All Claims");
  }

  if (!employee) {
    return <EmployeeLogin employees={demoEmployees} onLogin={handleLogin} />;
  }

  return (
    <div className="employee-dashboard-page">
      <header className="employee-topbar">
        <a className="employee-brand" href="#/employee" aria-label="Care Flow employee dashboard"><span>care</span><strong>flow</strong></a>
        <div className="employee-profile"><div><strong>{employee.name}</strong><span>{employee.role}</span></div><span className="employee-avatar" aria-hidden="true">{employee.name.split(" ").map((part) => part[0]).join("")}</span><button type="button" className="employee-logout-button" onClick={handleLogout}>Logout</button></div>
      </header>
      <main className="employee-dashboard-main">
        <section className="employee-dashboard-intro">
          <div><p className="employee-eyebrow">Claims operations</p><h1>Employee Dashboard</h1><p>Welcome back, {employee.name.split(" ")[0]}. You have <strong>{counts.assigned} claims</strong> currently assigned to you.</p></div>
          <span className="employee-date">02 August 2026</span>
        </section>
        <SummaryCards counts={counts} activeFilter={activeFilter} onFilterChange={setActiveFilter} />
        <section className="employee-work-queue" aria-labelledby="work-queue-title">
          <div className="employee-queue-heading"><div><p className="employee-eyebrow">Assigned claims</p><h2 id="work-queue-title">My Work Queue</h2></div><p>Review and process reimbursement claims requiring attention.</p></div>
          <ClaimFilters search={search} onSearchChange={setSearch} activeFilter={activeFilter} onFilterChange={setActiveFilter} resultCount={filteredClaims.length} totalCount={employee.totalClaims} />
          <ClaimsTable claims={filteredClaims} onOpenClaim={onOpenClaim} />
        </section>
      </main>
    </div>
  );
}

export default EmployeeDashboard;
