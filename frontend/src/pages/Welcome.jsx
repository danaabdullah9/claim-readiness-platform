import "./Welcome.css";

function Welcome({ onGetStarted }) {
  return (
    <div className="welcome-page">
      <div className="welcome-background-shape shape-one"></div>
      <div className="welcome-background-shape shape-two"></div>

      <main className="welcome-content">
        <div className="welcome-logo">
          <span>BUPA</span>
          <small>ARABIA</small>
        </div>

        <p className="welcome-label">Claims Management</p>

        <h1>
          Welcome to
          <span> Claim Readiness Platform</span>
        </h1>

        <p className="welcome-description">
          A smarter and easier way to prepare, review, and submit your
          reimbursement claims.
        </p>

       <button 
       className="welcome-button" 
       onClick={onGetStarted}
      >
  Get Started
</button>

        <p className="welcome-note">
          Upload your documents and let the system prepare your claim.
        </p>
      </main>
    </div>
  );
}

export default Welcome;