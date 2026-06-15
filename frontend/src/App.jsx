import { useEffect, useState } from "react";
import AdminPage from "./AdminPage";
import LabPage from "./LabPage";
import PracticePage from "./PracticePage";

function App() {
  const [route, setRoute] = useState(resolveRoute(window.location.pathname));

  useEffect(() => {
    if (window.location.pathname === "/") {
      window.history.replaceState({}, "", "/lab");
      setRoute("lab");
    }

    function handlePopState() {
      setRoute(resolveRoute(window.location.pathname));
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function navigate(nextRoute) {
    const nextPath = `/${nextRoute}${window.location.search}`;
    if (`${window.location.pathname}${window.location.search}` !== nextPath) {
      window.history.pushState({}, "", nextPath);
      setRoute(nextRoute);
    }
  }

  if (route === "admin") {
    return <AdminPage navigate={navigate} />;
  }

  if (route === "practice") {
    return <PracticePage navigate={navigate} />;
  }

  return <LabPage navigate={navigate} />;
}

function resolveRoute(pathname) {
  if (pathname === "/admin") {
    return "admin";
  }
  if (pathname === "/practice") {
    return "practice";
  }
  return "lab";
}

export default App;
