import { useState } from "react";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import NewClaim from "./pages/NewClaim";
import Summary from "./pages/Summary";
// Employee dashboard navigation (isolated from the existing member claim flow).
import EmployeeDashboard from "./pages/employee/EmployeeDashboard";
import ClaimReview from "./pages/employee/ClaimReview";

function App() {
  const [currentPage, setCurrentPage] = useState(
    window.location.hash === "#/employee" ? "employeeDashboard" : "welcome",
  );
  const [formData, setFormData] = useState({});
  // Employee dashboard navigation state. Existing page transitions remain unchanged.
  const [selectedEmployeeClaim, setSelectedEmployeeClaim] = useState(null);

  if (currentPage === "employeeDashboard") {
    return (
      <EmployeeDashboard
        onOpenClaim={(claim) => {
          setSelectedEmployeeClaim(claim);
          setCurrentPage("employeeClaimReview");
        }}
      />
    );
  }

  if (currentPage === "employeeClaimReview" && selectedEmployeeClaim) {
    return (
      <ClaimReview
        claim={selectedEmployeeClaim}
        onBack={() => setCurrentPage("employeeDashboard")}
      />
    );
  }
  // End employee dashboard navigation.

  if (currentPage === "login") {
    return <Login onLogin={() => setCurrentPage("newClaim")} />;
  }

  if (currentPage === "newClaim") {
    return (
      <NewClaim 
        onBack={() => setCurrentPage("login")} 
        onSubmitClaim={(data) => {
          setFormData(data);
          setCurrentPage("summary");
        }} 
      />
    );
  }

  if (currentPage === "summary") {
    return (
      <Summary 
        formData={formData} 
        onEdit={() => setCurrentPage("newClaim")} 
        onSubmit={() => {
          alert("Claim submitted successfully!");
          setCurrentPage("welcome");
        }} 
      />
    );
  }

  return (
    <Welcome
      onGetStarted={() => setCurrentPage("login")}
      onEmployeePortal={() => {
        window.location.hash = "#/employee";
        setCurrentPage("employeeDashboard");
      }}
    />
  );
}

export default App;
