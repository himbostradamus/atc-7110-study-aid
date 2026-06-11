import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

function showUpdateNotice(registration) {
  if (document.getElementById("atc-update-notice")) return;
  const notice = document.createElement("div");
  notice.id = "atc-update-notice";
  notice.setAttribute("role", "status");
  notice.style.cssText = [
    "position:fixed",
    "left:max(12px,env(safe-area-inset-left))",
    "right:max(12px,env(safe-area-inset-right))",
    "bottom:max(12px,env(safe-area-inset-bottom))",
    "z-index:9999",
    "display:flex",
    "align-items:center",
    "justify-content:space-between",
    "gap:12px",
    "padding:12px 14px",
    "background:#11120e",
    "color:#f1ead7",
    "border:1px solid rgba(226,219,193,.34)",
    "font:13px 'Share Tech Mono',ui-monospace,monospace",
  ].join(";");
  notice.innerHTML = "<span>New study-aid version available.</span>";
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "REFRESH";
  button.style.cssText = [
    "min-height:40px",
    "padding:0 14px",
    "border:0",
    "background:#d8a21c",
    "color:#090a08",
    "font:700 12px 'Share Tech Mono',ui-monospace,monospace",
    "letter-spacing:.08em",
  ].join(";");
  button.onclick = () => registration.waiting?.postMessage({ type: "SKIP_WAITING" });
  notice.appendChild(button);
  document.body.appendChild(notice);
}

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", async () => {
    try {
      const registration = await navigator.serviceWorker.register(
        `${import.meta.env.BASE_URL}sw.js`,
      );
      if (registration.waiting) showUpdateNotice(registration);
      registration.addEventListener("updatefound", () => {
        const worker = registration.installing;
        worker?.addEventListener("statechange", () => {
          if (worker.state === "installed" && navigator.serviceWorker.controller) {
            showUpdateNotice(registration);
          }
        });
      });
      let refreshing = false;
      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (refreshing) return;
        refreshing = true;
        window.location.reload();
      });
    } catch (error) {
      console.warn("Offline support could not be initialized.", error);
    }
  });
}
