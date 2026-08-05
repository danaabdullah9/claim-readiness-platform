import { useState } from "react";
import "./Login.css";
import bupaLogo from "../assets/bupa-logo.png";


function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();

    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setError("");

    try {
      const response = await fetch("http://127.0.0.1:8001/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        onLogin(data.user);
      } else {
        setError(data.detail);
      }
    } catch (err) {
      setError("Cannot connect to backend.");
      console.error(err);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <img className="login-logo" src={bupaLogo} alt="Bupa Arabia" />
          <div className="welcome-brand login-brand" aria-label="Care Flow">
            <span>care</span><strong>flow</strong>
          </div>
          <h1>Welcome back</h1>
          <span className="login-portal-badge">Employee Portal</span>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email address</label>

            <input
              id="email"
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>

            <input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          <div className="login-options">
            <label className="remember-me">
              <input type="checkbox" />
              Remember me
            </label>

            <button type="button" className="forgot-password">
              Forgot password?
            </button>
          </div>

          {error && <p className="error-message">{error}</p>}

          <button type="submit" className="login-button">
            Sign in
          </button>

          <button
            type="button"
            className="back-to-welcome-button"
            onClick={() => {
              window.location.hash = "";
              window.location.reload();
            }}
          >
            ← Back to Welcome
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
