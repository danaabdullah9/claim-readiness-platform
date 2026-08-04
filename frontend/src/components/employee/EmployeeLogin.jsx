import { useState } from "react";
import "./EmployeeLogin.css";

function EmployeeLogin({ employees, onLogin }) {
  const [employeeId, setEmployeeId] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const normalizedId = employeeId.trim().toUpperCase();
    const employee = employees.find((item) => item.id === normalizedId);

    if (!employee) {
      setError(normalizedId ? "Employee ID not recognized." : "Please enter your Employee ID.");
      return;
    }

    setError("");
    onLogin(employee);
  }

  function handleBackToWelcome() {
    window.location.hash = "";
    window.location.reload();
  }

  return (
    <div className="employee-login-page">
      <main className="employee-login-card">
        <div className="welcome-brand employee-login-brand" aria-label="Care Flow"><span>care</span><strong>flow</strong></div>
        <h1>Employee Login</h1>
        <form onSubmit={handleSubmit} noValidate>
          <label className="employee-login-field-label" htmlFor="employee-id">Employee ID</label>
          <input id="employee-id" type="text" value={employeeId} onChange={(event) => { setEmployeeId(event.target.value); setError(""); }} placeholder="Enter your Employee ID" autoComplete="off" autoFocus aria-describedby={error ? "employee-login-error" : undefined} />
          {error && <p className="employee-login-error" id="employee-login-error" role="alert">{error}</p>}
          <button type="submit">Continue to Dashboard</button>
        </form>
        <section className="employee-access-card" aria-labelledby="employee-access-title">
          <h2 id="employee-access-title">Employee Access</h2>
          <p>Enter your assigned Employee ID to access your dashboard.</p>
          <p>If you do not know your Employee ID, please contact your administrator.</p>
        </section>
        <a className="employee-back-to-welcome" href="" onClick={handleBackToWelcome}>← Back</a>
      </main>
    </div>
  );
}

export default EmployeeLogin;
