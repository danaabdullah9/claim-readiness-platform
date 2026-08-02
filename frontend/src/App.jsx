import { useState } from "react";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import NewClaim from "./pages/NewClaim";
import Summary from "./pages/Summary";

function App() {
  const debugParams = new URLSearchParams(window.location.search);
  const debugClaimId = debugParams.get("debugClaimId");
  const [currentPage, setCurrentPage] = useState(debugClaimId ? "summary" : "welcome");
  const [claimId, setClaimId] = useState(debugClaimId ? Number(debugClaimId) : null);

  if (currentPage === "login") {
    return <Login onLogin={() => setCurrentPage("newClaim")} />;
  }

  if (currentPage === "newClaim") {
    return (
      <NewClaim
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
      <Summary
        claimId={claimId}
        onEdit={() => setCurrentPage("newClaim")}
        onSubmit={() => {
          alert("Claim submitted successfully!");
          setCurrentPage("welcome");
        }}
      />
    );
  }

  return <Welcome onGetStarted={() => setCurrentPage("login")} />;
}

export default App;