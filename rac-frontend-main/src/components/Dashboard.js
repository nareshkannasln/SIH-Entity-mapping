import React from "react";

function Dashboard() {
  return (
    <div className="dashboard">
      <h2>Admin Dashboard</h2>
      <p>View the performance of the document verification process below:</p>
      {/* Replace with your Power BI report URL */}
      <iframe
        title="Power BI Dashboard"
        width="100%"
        height="500px"
        src="https://app.powerbi.com/reportEmbed?reportId=YOUR_REPORT_ID&autoAuth=true"
        frameBorder="0"
      ></iframe>
    </div>
  );
}

export default Dashboard;
