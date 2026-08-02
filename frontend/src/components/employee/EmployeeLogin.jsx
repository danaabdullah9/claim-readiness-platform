import { useState } from "react";

function EmployeeLogin({ employees, onLogin }) {
  const [employeeId, setEmployeeId] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    const normalizedId = employeeId.trim().toUpperCase();
    const employee = employees.find((item) => item.id === normalizedId);

    if (!employee) {
      setError("Employee ID not recognized. Please use one of the demo accounts below.");
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
        <div className="employee-login-brand"><span>care</span><strong>flow</strong></div>
        <p className="employee-eyebrow">Claims operations</p>
        <h1>Employee Login</h1>
        <p className="employee-login-intro">Enter your employee ID to access your assigned claims.</p>
        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="employee-id">Employee ID</label>
          <input id="employee-id" type="text" value={employeeId} onChange={(event) => { setEmployeeId(event.target.value); setError(""); }} placeholder="e.g. EMP1001" autoComplete="off" autoFocus aria-describedby={error ? "employee-login-error" : undefined} />
          {error && <p className="employee-login-error" id="employee-login-error" role="alert">{error}</p>}
          <button type="submit">Continue to Dashboard</button>
          <button type="button" className="employee-back-to-welcome" onClick={handleBackToWelcome}>← Back to Welcome</button>
        </form>
        <section className="employee-demo-accounts" aria-labelledby="demo-accounts-title">
          <div><h2 id="demo-accounts-title">Demo accounts</h2><span>No password required</span></div>
          <ul>{employees.map((employee) => <li key={employee.id}><button type="button" onClick={() => setEmployeeId(employee.id)}><strong>{employee.id}</strong><span>{employee.name}</span><small>{employee.role}</small></button></li>)}</ul>
        </section>
        <p className="employee-demo-note">Demo access only · No real authentication is performed</p>
      </main>
    </div>
  );
}

export default EmployeeLogin;
