import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import "swiper/swiper-bundle.css";
import "flatpickr/dist/flatpickr.css";
import App from "./App.tsx";
import { AppWrapper } from "./components/common/PageMeta.tsx";
import { ThemeProvider } from "./context/ThemeContext.tsx";
import { installStaleBuildRecovery, removeDevServiceWorkers } from "./components/pwa/staleBuild.ts";

if (import.meta.env.DEV) {
  removeDevServiceWorkers(); // a production service worker left on this address would serve an old build
} else {
  installStaleBuildRecovery(); // after a deploy: a missing page file -> switch to the new version, reload once
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AppWrapper>
        <App />
      </AppWrapper>
    </ThemeProvider>
  </StrictMode>,
);
