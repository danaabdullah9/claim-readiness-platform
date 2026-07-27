import { useState } from "react";
import "./Login.css";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(event) {
    event.preventDefault();

    if (!email || !password) {
      setError("Please enter your email and password.");
      return;
    }

    setError("");
    console.log("Email:", email);
    console.log("Password:", password);

    alert("Login submitted successfully.");
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <p className="login-label">Claims Management</p>
          <h1>Claim Readiness Platform</h1>
          <p>Sign in to review and manage insurance claims.</p>
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
        </form>
      </div>
    </div>
  );
}

export default Login;