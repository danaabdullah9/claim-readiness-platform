import { useState } from "react";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import NewClaim from "./pages/NewClaim";
import Summary from "./pages/Summary";

function App() {
  const [currentPage, setCurrentPage] = useState("welcome");
  const [formData, setFormData] = useState({});

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

  return <Welcome onGetStarted={() => setCurrentPage("login")} />;
}

export default App;