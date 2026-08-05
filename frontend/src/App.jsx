import { useState } from "react";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import NewClaim from "./pages/NewClaim";
import Summary from "./pages/Summary";
// Employee dashboard navigation (isolated from the existing member claim flow).
import EmployeeDashboard from "./pages/employee/EmployeeDashboard";
import ClaimReview from "./pages/employee/ClaimReview";
import SubmissionSuccess from "./pages/SubmissionSuccess";

function App() {
  const [currentPage, setCurrentPage] = useState(
    window.location.hash === "#/employee" ? "employeeDashboard" : "welcome",
  );
  const [claimId, setClaimId] = useState(null);
  const [userId, setUserId] = useState(null);
  // Employee dashboard navigation state. Existing page transitions remain unchanged.
  const [selectedEmployeeClaim, setSelectedEmployeeClaim] = useState(null);

  // State to control your custom success popup modal
  const [isSubmitted, setIsSubmitted] = useState(false);

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
    return (
      <Login
        onLogin={(user) => {
          setUserId(user.id);
          setCurrentPage("newClaim");
        }}
      />
    );
  }

  if (currentPage === "newClaim") {
    return (
      <NewClaim
        userId={userId}
        onBack={() => setCurrentPage("login")}
        onSubmitClaim={(newClaimId) => {
          setClaimId(newClaimId);
          setCurrentPage("summary");
        }}
      />
    );
  }

  if (currentPage === "summary") {
    return (
      <div style={{ position: "relative" }}>
        <Summary
          claimId={claimId}
          onEdit={() => setCurrentPage("newClaim")}
          onSubmit={() => {
            // Trigger your custom success popup modal instead of an alert
            setIsSubmitted(true);
          }}
        />

        {/* Custom Submission Success Modal Popup */}
        {isSubmitted && (
          <SubmissionSuccess
            onClose={() => {
              setIsSubmitted(false);
              setCurrentPage("welcome");
            }}
          />
        )}
      </div>
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