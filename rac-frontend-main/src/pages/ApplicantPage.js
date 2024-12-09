import React, { useState } from "react";
import { Link } from "react-router-dom"; // Importing Link for navigation
import "./ApplicantPage.css";

function ApplicantPage() {
  const [acknowledgmentNumber, setAcknowledgmentNumber] = useState("");
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");

  const handleStatusCheck = () => {
    if (!acknowledgmentNumber) {
      setError("Please enter the acknowledgment number.");
      return;
    }

    setError(""); // Reset error state

    const statuses = {
      "12345": "In Progress",
      "67890": "Under Review",
      "11223": "Verified",
      "44556": "Flagged",
    };

    if (statuses[acknowledgmentNumber]) {
      setStatus(statuses[acknowledgmentNumber]);
    } else {
      setStatus("No application found for this acknowledgment number.");
    }
  };

  return (
    <div className="applicant-dashboard">
      <h1>RAC DRDO Applicant Dashboard</h1>

      {/* Job Selection */}
      <div className="job-selection">
        <h3>Select a Job</h3>
        <select>
          <option>Junior Research Fellow (JRF)</option>
          <option>Research Associate (RA)</option>
          <option>Project Assistant</option>
        </select>

        {/* Use Link to navigate to the application form page */}
        <Link to="/application-form">
          <button>Apply</button>
        </Link>
      </div>

      {/* Application Status */}
      <div className="status-container">
        <h3>Track Your Application Status</h3>
        <p>Enter your acknowledgment number to check the application status:</p>
        <input
          type="text"
          placeholder="Enter Acknowledgment Number"
          value={acknowledgmentNumber}
          onChange={(e) => setAcknowledgmentNumber(e.target.value)}
        />
        <button onClick={handleStatusCheck}>Check Status</button>

        {error && <p className="error-message">{error}</p>}

        {status && (
          <div className="status-result">
            <h4>Status: {status}</h4>
          </div>
        )}
      </div>

      {/* Recent Trends in RAC DRDO */}
      <div className="recent-trends">
        <h3>Recent Trends in RAC DRDO</h3>
        <ul>
          <li>New job openings for 2024</li>
          <li>DRDO Research Initiatives in AI</li>
          <li>Collaboration with Indian Universities for Research</li>
        </ul>
      </div>

      {/* Job Vacancies */}
      <div className="job-vacancies">
        <h3>Current Job Vacancies</h3>
        <ul>
          <li>Junior Research Fellow (JRF) - Apply Now</li>
          <li>Research Associate (RA) - Apply Now</li>
          <li>Project Assistant - Apply Now</li>
        </ul>
      </div>

      {/* Footer */}
      <footer>
        <p>© 2024 RAC DRDO - Ministry of Defence, Government of India</p>
      </footer>
    </div>
  );
}

export default ApplicantPage;
