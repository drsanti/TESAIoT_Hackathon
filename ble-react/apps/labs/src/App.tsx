import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { BleSessionProvider } from "./hooks/useBleSession";
import { HomePage } from "./pages/HomePage";
import { BleStepDiagPage } from "./diag/BleStepDiagPage";
import { Lab01Page } from "./labs/01-secure-context/Lab01Page";
import { Lab02Page } from "./labs/02-request-device/Lab02Page";
import { Lab03Page } from "./labs/03-gatt-link/Lab03Page";
import { Lab04Page } from "./labs/04-go-live/Lab04Page";
import { Lab05Page } from "./labs/05-stream/Lab05Page";
import { Lab06Page } from "./labs/06-focus-sensor/Lab06Page";
import { Lab07Page } from "./labs/07-imu-env/Lab07Page";
import { Lab08Page } from "./labs/08-pots-buttons/Lab08Page";
import { Lab09Page } from "./labs/09-dashboard/Lab09Page";
import { Lab10Page } from "./labs/10-your-app/Lab10Page";

function SessionLayout() {
  return (
    <BleSessionProvider>
      <Outlet />
    </BleSessionProvider>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <header className="topbar">
          <div>
            <div className="brand">TESAIoT · BLE tutorial</div>
            <div className="brand-sub">Web Bluetooth · host Node bridge · EVT-first</div>
          </div>
          <div className="muted">localhost:5174 · bridge :9788</div>
        </header>
        <Routes>
          {/* Fresh diag — outside shared session */}
          <Route path="/diag" element={<BleStepDiagPage />} />
          <Route element={<SessionLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/labs/01" element={<Lab01Page />} />
            <Route path="/labs/02" element={<Lab02Page />} />
            <Route path="/labs/03" element={<Lab03Page />} />
            <Route path="/labs/04" element={<Lab04Page />} />
            <Route path="/labs/05" element={<Lab05Page />} />
            <Route path="/labs/06" element={<Lab06Page />} />
            <Route path="/labs/07" element={<Lab07Page />} />
            <Route path="/labs/08" element={<Lab08Page />} />
            <Route path="/labs/09" element={<Lab09Page />} />
            <Route path="/labs/10" element={<Lab10Page />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </div>
    </BrowserRouter>
  );
}
