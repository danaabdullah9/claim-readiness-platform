import { useRef } from "react";
import "./Welcome.css";
import bupaLogo from "../assets/bupa-logo.png";
import heroImage from "../assets/welcome-healthcare-hero-v3.png";

function Welcome({ onGetStarted, onEmployeePortal }) {
  const portalSectionRef = useRef(null);
  function scrollToPortals() {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    portalSectionRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
  }

  return (
    <div className="welcome-page">
      <header className="welcome-header">
        <div className="welcome-header-inner">
          <img className="welcome-logo" src={bupaLogo} alt="Bupa Arabia" />
          <span className="welcome-header-divider" aria-hidden="true" />
          <div className="welcome-brand" aria-label="Careflow"><span>care</span><strong>flow</strong></div>
        </div>
      </header>

      <main>
        <section className="welcome-hero" style={{ backgroundImage: `url(${heroImage})` }}>
          <div className="welcome-hero-overlay" aria-hidden="true" />
          <div className="welcome-hero-inner">
            <article className="welcome-hero-card">
              <h1>
                <span>Bupa Arabia App</span>
                Prepare, review and track your reimbursement claims with confidence.
              </h1>
            </article>
            <button className="welcome-scroll-button" onClick={scrollToPortals} aria-label="Scroll to portal selection">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
            </button>
          </div>
        </section>

        <section className="welcome-portals" ref={portalSectionRef} tabIndex="-1">
          <div className="welcome-section-heading">
            <p className="welcome-kicker">Your Careflow experience</p>
            <h2>Choose how you want to continue</h2>
          </div>
          <div className="welcome-actions">
            <section className="welcome-portal-card">
              <div><h3>Member Portal</h3><p>Submit a new claim and review your claim information.</p></div>
              <button className="welcome-button" onClick={onGetStarted}>Continue as Member</button>
            </section>
            <section className="welcome-portal-card">
              <div><h3>Employee Portal</h3><p>Review assigned claims and verify submitted information.</p></div>
              <button className="welcome-button welcome-employee-button" onClick={onEmployeePortal}>Continue as Employee</button>
            </section>
          </div>
        </section>
      </main>
    </div>
  );
}

export default Welcome;
