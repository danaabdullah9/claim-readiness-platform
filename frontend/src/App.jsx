import { useState } from "react";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import NewClaim from "./pages/NewClaim";
import Summary from "./pages/Summary";
// Employee dashboard navigation (isolated from the existing member claim flow).
import EmployeeDashboard from "./pages/employee/EmployeeDashboard";
import ClaimReview from "./pages/employee/ClaimReview";
import SubmissionSuccess from "./pages/SubmissionSuccess";
import CustomerDashboard from "./pages/CustomerDashboard";

function initialCustomerPage() {
  if (window.location.hash === "#/dashboard") return "customerDashboard";
  if (window.location.hash === "#/new-claim") return "newClaim";
  return "welcome";
}

function App() {
  const [currentPage, setCurrentPage] = useState(
    window.location.hash === "#/employee" ? "employeeDashboard" : initialCustomerPage(),
  );
  const [claimId, setClaimId] = useState(null);
  const [userId, setUserId] = useState(null);
  const [customer, setCustomer] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("careflow-customer")); } catch { return null; }
  });
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
          setCustomer(user);
          sessionStorage.setItem("careflow-customer", JSON.stringify(user));
          window.location.hash = "#/dashboard";
          setCurrentPage("customerDashboard");
        }}
      />
    );
  }

  if (currentPage === "customerDashboard") {
    return <CustomerDashboard user={customer} onStartClaim={() => {
      window.location.hash = "#/new-claim";
      setCurrentPage("newClaim");
    }} onSignOut={() => {
      sessionStorage.removeItem("careflow-customer");
      setCustomer(null);
      setUserId(null);
      window.location.hash = "";
      setCurrentPage("welcome");
    }} />;
  }

  if (currentPage === "newClaim") {
    return (
      <NewClaim
        userId={userId}
        onBack={() => {
          window.location.hash = "#/dashboard";
          setCurrentPage("customerDashboard");
        }}
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
          setIsSubmitted(true);
        }}
      />

      {isSubmitted && (
        <SubmissionSuccess
          onClose={() => {
            setIsSubmitted(false);
            window.location.hash = "#/dashboard";
            setCurrentPage("customerDashboard");
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