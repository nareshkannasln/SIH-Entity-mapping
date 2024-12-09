import React from "react";
import { Link } from "react-router-dom";
import "./AdminPage.css";

function AdminPage() {
  return (
    <div className="admin-dashboard">
      <h1>Admin Dashboard</h1>
      <div className="stats-container">
        <div className="stat-box">
          <h3>Total Applicants</h3>
          <p>120</p>
        </div>
        <div className="stat-box">
          <h3>Verified Applications</h3>
          <p>100</p>
        </div>
        <div className="stat-box">
          <h3>Pending Applications</h3>
          <p>15</p>
        </div>
        <div className="stat-box">
          <h3>Flagged Applications</h3>
          <p>5</p>
        </div>
      </div>
      <h3>Select Schemas to Verify</h3>
      <div className="schema-selector">
        <select>
          <option>Certificate 1</option>
          <option>Certificate 2</option>
          <option>Certificate 3</option>
        </select>
      </div>
      <Link to="/applicant">
        <button>View Applicants</button>
      </Link>
    </div>
  );
}

export default AdminPage;
