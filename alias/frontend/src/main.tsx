import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/global.scss";

// Enable hot reload
if (import.meta.hot) {
  import.meta.hot.accept();
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
