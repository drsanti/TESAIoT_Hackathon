import { Link } from "react-router-dom";
import { LAB_CATALOG } from "../labCatalog";
import { useBleSession } from "../hooks/useBleSession";
import { useChapterProgress } from "../tutorial";

export function HomePage() {
  const { phase, device } = useBleSession();
  const { isComplete, clearProgress } = useChapterProgress();
  const doneCount = LAB_CATALOG.filter((l) => isComplete(l.id)).length;

  return (
    <div>
      <section className="path-hero">
        <h1>TESAIoT BLE tutorial</h1>
        <p className="lede">
          Interactive Web Bluetooth lessons — connect the DevKit, enable notifications, and decode
          live <code>EVT_SENSOR</code> data step by step. Use system Chrome or Edge on{" "}
          <code>localhost:5174</code>.
        </p>
      </section>

      <div className="path-tools">
        <Link className="tool-card" to="/diag">
          <span className="label">Bring-up</span>
          <span className="title">BLE step diagnostic</span>
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            Isolated GATT steps — use when Connect drops on Windows.
          </span>
        </Link>
        <div className="tool-card" style={{ cursor: "default" }}>
          <span className="label">Shared session</span>
          <span className="title">
            {phase}
            {device ? ` · ${device.name}` : ""}
          </span>
          <span className="muted" style={{ fontSize: "0.85rem" }}>
            Progress: {doneCount}/{LAB_CATALOG.length} chapters
            {doneCount > 0 ? (
              <>
                {" · "}
                <button
                  type="button"
                  style={{ padding: "0.15rem 0.45rem", fontSize: "0.8rem" }}
                  onClick={clearProgress}
                >
                  Reset progress
                </button>
              </>
            ) : null}
          </span>
        </div>
      </div>

      <h2 style={{ margin: "0 0 0.65rem", fontSize: "0.85rem", letterSpacing: "0.04em", textTransform: "uppercase", color: "var(--muted)" }}>
        Learning path
      </h2>
      <div className="path-list">
        {LAB_CATALOG.map((lab) => {
          const done = isComplete(lab.id);
          return (
            <Link
              key={lab.id}
              className={`path-item ${done ? "complete" : ""}`}
              to={lab.path}
            >
              <span className="num">{lab.id}</span>
              <div>
                <div className="title">{lab.title}</div>
                <p className="blurb">{lab.blurb}</p>
              </div>
              <span className={`status-pill ${done ? "done" : ""}`}>
                {done ? "Done" : "Start"}
              </span>
            </Link>
          );
        })}
      </div>

      <p className="muted" style={{ marginTop: "1.75rem", fontSize: "0.85rem" }}>
        Docs: <code>docs/LABS.md</code> · Windows Web Bluetooth:{" "}
        <code>docs/WEB_BLUETOOTH_WINDOWS.md</code>
      </p>
    </div>
  );
}
