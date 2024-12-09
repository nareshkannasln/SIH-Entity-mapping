import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./LoginPage.css";

function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleLogin = () => {
    if (!username || !password) {
      setError("Please enter both username and password.");
      return;
    }

    setError(""); // Clear error
    navigate("/applicant"); // Navigate to applicant dashboard
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">RAC DRDO Portal</h1>
        <p className="login-subtitle">Secure Login for Applicants</p>

        <input
          className="input-field"
          type="text"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="input-field"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button className="login-button" onClick={handleLogin}>
          Login
        </button>

        {error && <p className="error-message">{error}</p>}
      </div>
    </div>
  );
}

export default LoginPage;
