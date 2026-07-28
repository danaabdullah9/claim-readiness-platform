import { useState } from "react";
import Welcome from "./pages/Welcome";
import Login from "./pages/Login";
import NewClaim from "./pages/NewClaim";

function App() {
  const [currentPage, setCurrentPage] = useState("welcome");

  if (currentPage === "login") {
    return <Login onLogin={() => setCurrentPage("newClaim")} />;
  }

  if (currentPage === "newClaim") {
    return <NewClaim onBack={() => setCurrentPage("login")} />;
  }

  return <Welcome onGetStarted={() => setCurrentPage("login")} />;
}

export default App;

