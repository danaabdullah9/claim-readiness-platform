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

        <p className="welcome-label">Bupa Arabia</p>

        <h1>
          Welcome to
          <span> Care Flow</span>
        </h1>

        <p className="welcome-description">
          A smarter and easier way to prepare, review, and submit your
          reimbursement claims.
        </p>

        <div className="welcome-actions">
          <button className="welcome-button" onClick={onGetStarted}>
            Member Portal
          </button>
          <button
            className="welcome-button welcome-employee-button"
            onClick={onEmployeePortal}
          >
            Employee Portal
          </button>
        </div>

        <p className="welcome-note">
          Upload your documents and let the system prepare your claim.
        </p>
      </main>
    </div>
  );
}

export default Welcome;
