import { useEffect, useState } from "react";
import AdminPage from "./AdminPage";
import LabPage from "./LabPage";

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

  return <LabPage navigate={navigate} />;
}

function resolveRoute(pathname) {
  return pathname === "/admin" ? "admin" : "lab";
}

export default App;
