import React from "react";

function HomePage() {
  return (
    <div className="homepage">
      <h1>Welcome to the Document Verification System</h1>
      <p>
        This system allows applicants to upload documents for verification. 
        Once uploaded, their data is verified and any mismatches are flagged.
      </p>
      <p>
        <strong>Applicant Portal:</strong> Upload documents and track the status of your application.
      </p>
      <p>
        <strong>Admin Portal:</strong> Review applicant submissions, run reports, and manage the verification process.
      </p>
    </div>
  );
}

export default HomePage;
