import React, { useState } from "react";

function StatusTracker() {
  const [applicants, setApplicants] = useState([
    { name: "John Doe", status: "Pending" },
    { name: "Jane Smith", status: "Verified" },
    { name: "Mike Johnson", status: "Rejected" },
  ]);

  return (
    <div className="status-tracker">
      <h2>Applicant Status</h2>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {applicants.map((applicant, index) => (
            <tr key={index}>
              <td>{applicant.name}</td>
              <td>{applicant.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default StatusTracker;
