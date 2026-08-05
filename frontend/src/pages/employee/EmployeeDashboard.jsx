import { useCallback, useEffect, useMemo, useState } from "react";
import SummaryCards from "../../components/employee/SummaryCards";
import ClaimFilters from "../../components/employee/ClaimFilters";
import ClaimsTable from "../../components/employee/ClaimsTable";
import EmployeeLogin from "../../components/employee/EmployeeLogin";
import { demoEmployees } from "../../data/employeeClaims";
import "./EmployeeDashboard.css";

const API_BASE_URL = "http://127.0.0.1:8001";
const DAY = 24 * 60 * 60 * 1000;

function daysOld(claim) {
  if (!claim.submissionDate) return Number.POSITIVE_INFINITY;
  const submitted = new Date(`${claim.submissionDate}T12:00:00`);
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  return Math.round((today - submitted) / DAY);
}

function matchesFilter(claim, filter) {
  const age = daysOld(claim);
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

  // المطالبات الحقيقية من قاعدة البيانات بدل الملف الوهمي
  const [claims, setClaims] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState("");

  const loadClaims = useCallback(async () => {
    if (!employee) return;

    setIsLoading(true);
    setLoadError("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/employee/claims`);
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Failed to load claims.");
      }

      // ما فيه عمود تكليف في السكيمة، فكل المطالبات معروضة للموظف الحالي
      setClaims(
        (result.data || []).map((claim) => ({ ...claim, assignedTo: employee.name })),
      );
    } catch (err) {
      setLoadError(err.message || "Cannot connect to backend.");
      setClaims([]);
    } finally {
      setIsLoading(false);
    }
  }, [employee]);

  useEffect(() => {
    loadClaims();
  }, [loadClaims]);

  const filteredClaims = useMemo(() => {
    const term = search.trim().toLowerCase();
    return claims.filter((claim) => {
      const searchable = [
        claim.id,
        claim.member.name,
        claim.member.nationalId,
        claim.member.policyNumber,
        claim.invoiceNumber,
        claim.provider,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return (!term || searchable.includes(term)) && matchesFilter(claim, activeFilter);
    });
  }, [claims, search, activeFilter]);

  const counts = {
    assigned: claims.length,
    pending: claims.filter((claim) => ["Pending Review", "Under Review", "Missing Documents"].includes(claim.status)).length,
    waiting: claims.filter((claim) => claim.status === "Waiting for Member").length,
    ready: claims.filter((claim) => claim.status === "Ready for Submission").length,
    completed: claims.filter((claim) => claim.status === "Completed").length,
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
    setClaims([]);
    setSearch("");
    setActiveFilter("All Claims");
  }

  if (!employee) {
    return <EmployeeLogin employees={demoEmployees} onLogin={handleLogin} />;
  }

  const today = new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "long", year: "numeric" }).format(new Date());

  return (
    <div className="employee-dashboard-page">
      <header className="employee-topbar">
        <a className="employee-brand" href="#/employee" aria-label="Care Flow employee dashboard"><span>care</span><strong>flow</strong></a>
        <div className="employee-profile"><div><strong>{employee.name}</strong><span>{employee.role}</span></div><span className="employee-avatar" aria-hidden="true">{employee.name.split(" ").map((part) => part[0]).join("")}</span><button type="button" className="employee-logout-button" onClick={handleLogout}>Logout</button></div>
      </header>
      <main className="employee-dashboard-main">
        <section className="employee-dashboard-intro">
          <div className="employee-dashboard-copy"><h1>Employee Dashboard</h1><p>Welcome back, {employee.name.split(" ")[0]}.</p></div>
          <span className="employee-date">{today}</span>
        </section>
        <SummaryCards counts={counts} activeFilter={activeFilter} onFilterChange={setActiveFilter} />
        <section className="employee-work-queue" aria-labelledby="work-queue-title">
          <div className="employee-queue-heading"><h2 id="work-queue-title">Submitted Claims</h2><button type="button" className="employee-table-action" onClick={loadClaims} disabled={isLoading}>{isLoading ? "Refreshing…" : "Refresh"}</button></div>
          {loadError && <div className="employee-notice" role="alert"><span>!</span>{loadError}</div>}
          <ClaimFilters search={search} onSearchChange={setSearch} activeFilter={activeFilter} onFilterChange={setActiveFilter} resultCount={filteredClaims.length} totalCount={claims.length} />
          <ClaimsTable claims={filteredClaims} onOpenClaim={onOpenClaim} />
        </section>
      </main>
    </div>
  );
}

export default EmployeeDashboard;
