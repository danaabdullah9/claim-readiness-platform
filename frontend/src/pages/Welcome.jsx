import "./Welcome.css";
import bupaLogo from "../assets/bupa-logo.png";

function Welcome({ onGetStarted, onEmployeePortal }) {
  return (
    <div className="welcome-page">
      <div className="welcome-background-shape shape-one"></div>
      <div className="welcome-background-shape shape-two"></div>

      <main className="welcome-content">
        <img
          className="welcome-logo"
          src={bupaLogo}
          alt="Bupa Arabia"
        />

        <div className="welcome-brand" aria-label="Care Flow">
          <span>care</span><strong>flow</strong>
        </div>

        <h1>Welcome</h1>

        <p className="welcome-description">
          A smarter way to prepare, review, and submit reimbursement claims.
        </p>

        <div className="welcome-actions">
          <section className="welcome-portal-card">
            <div>
              <h2>Member Portal</h2>
              <p>Submit a new claim and review your claim information.</p>
            </div>
            <button className="welcome-button" onClick={onGetStarted}>
              Continue as Member
            </button>
          </section>

          <section className="welcome-portal-card">
            <div>
              <h2>Employee Portal</h2>
              <p>Review assigned claims and verify submitted information.</p>
            </div>
            <button
              className="welcome-button welcome-employee-button"
              onClick={onEmployeePortal}
            >
              Continue as Employee
            </button>
          </section>
        </div>
      </main>
    </div>
  );
}

export default Welcome;
