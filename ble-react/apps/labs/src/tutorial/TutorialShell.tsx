import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { TutorialStepDef } from "./types";
import { TutorialStep } from "./TutorialStep";
import { useChapterProgress } from "./useChapterProgress";
import { useBleSession } from "../hooks/useBleSession";

function stepComplete(step: TutorialStepDef): boolean {
  return step.checks.length > 0 && step.checks.every((c) => c.pass);
}

export function TutorialShell({
  labId,
  title,
  subtitle,
  steps,
  prevPath,
  nextPath,
  children,
}: {
  labId: string;
  title: string;
  subtitle?: string;
  steps: TutorialStepDef[];
  prevPath?: string;
  nextPath?: string;
  children?: ReactNode;
}) {
  const { phase } = useBleSession();
  const { markComplete, isComplete } = useChapterProgress();

  const chapterComplete = useMemo(
    () => steps.length > 0 && steps.every(stepComplete),
    [steps],
  );

  useEffect(() => {
    if (chapterComplete) markComplete(labId);
  }, [chapterComplete, labId, markComplete]);

  const firstIncomplete = useMemo(() => {
    const i = steps.findIndex((s) => !stepComplete(s));
    return i === -1 ? Math.max(0, steps.length - 1) : i;
  }, [steps]);

  const [manualIndex, setManualIndex] = useState<number | null>(null);
  const activeIndex = manualIndex ?? firstIncomplete;
  const active = steps[activeIndex] ?? steps[0];

  // When earlier steps become complete, follow the learner forward unless they picked a step.
  useEffect(() => {
    if (manualIndex == null) return;
    if (manualIndex > firstIncomplete) setManualIndex(null);
  }, [firstIncomplete, manualIndex]);

  return (
    <div>
      <Link className="tutorial-back" to="/">
        ← Learning path
      </Link>

      <div className="tutorial-shell">
        <aside className="tutorial-rail">
          <div className="tutorial-rail-head">
            <div className="chapter">Chapter {labId}</div>
            <h1>{title}</h1>
            <div
              className={`status-pill ${phase === "live" ? "live" : phase === "error" ? "error" : ""}`}
              style={{ marginTop: "0.65rem" }}
            >
              Session: {phase}
            </div>
            {isComplete(labId) || chapterComplete ? (
              <div className="status-pill done" style={{ marginTop: "0.4rem" }}>
                Chapter done
              </div>
            ) : null}
          </div>
          <ul className="tutorial-rail-nav">
            {steps.map((s, i) => {
              const done = stepComplete(s);
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    className={`${i === activeIndex ? "active" : ""} ${done ? "done" : ""}`}
                    onClick={() => setManualIndex(i)}
                  >
                    <span className="step-idx">{done ? "✓" : String(i + 1)}</span>
                    <span>{s.title}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <div className="tutorial-main">
          {subtitle ? <p className="tutorial-subtitle">{subtitle}</p> : null}
          {active ? <TutorialStep step={active} /> : null}
          {children}

          {chapterComplete ? (
            <div className="pass-banner" role="status">
              <span aria-hidden>✓</span>
              Chapter complete — you can continue to the next lesson.
            </div>
          ) : null}

          <div className="chapter-nav">
            {prevPath ? (
              <Link className="btn" to={prevPath}>
                ← Previous
              </Link>
            ) : (
              <span />
            )}
            {nextPath ? (
              <Link
                className={`btn ${chapterComplete ? "primary" : ""}`}
                to={nextPath}
                aria-disabled={!chapterComplete}
                onClick={(e) => {
                  if (!chapterComplete) e.preventDefault();
                }}
                style={!chapterComplete ? { opacity: 0.45, pointerEvents: "none" } : undefined}
              >
                Next chapter →
              </Link>
            ) : (
              <Link className="btn primary" to="/">
                Back to path
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
