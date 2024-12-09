import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./SignupPage.css"; // Custom CSS for consistent styling with LoginPage

function SignupPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleSignup = () => {
    if (!username || !password || !confirmPassword) {
      setMessage("Please fill in all fields.");
      return;
    }
    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    setMessage("Signup successful! Redirecting to login...");
    setTimeout(() => {
      navigate("/login");
    }, 2000);
  };

  return (
    <div className="signup-container">
      <div className="form-card">
        <h1 className="form-title">Applicant Signup</h1>
        <p className="form-subtitle">Create your account to apply for RAC DRDO jobs</p>

        <input
          className="form-input"
          type="text"
          placeholder="Enter Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          className="form-input"
          type="password"
          placeholder="Enter Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <input
          className="form-input"
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
        />

        <button className="form-button" onClick={handleSignup}>
          Sign Up
        </button>

        {message && <p className="form-message">{message}</p>}

        <p className="redirect-text">
          Already have an account? <a href="/login">Login here</a>.
        </p>
      </div>
    </div>
  );
}

export default SignupPage;
