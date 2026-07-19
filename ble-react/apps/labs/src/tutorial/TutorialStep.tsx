import type { TutorialStepDef } from "./types";
import { StepChecklist } from "./StepChecklist";

export function TutorialStep({ step }: { step: TutorialStepDef }) {
  const allPass = step.checks.length > 0 && step.checks.every((c) => c.pass);

  return (
    <article className="step-card">
      <h2>{step.title}</h2>

      <div className="step-section">
        <span className="step-label">Why</span>
        <div className="step-why">{step.why}</div>
      </div>

      {step.do ? (
        <div className="step-section">
          <span className="step-label">Do</span>
          {step.do}
        </div>
      ) : null}

      {step.callout}

      <div className="step-section">
        <span className="step-label">Check</span>
        <StepChecklist checks={step.checks} />
        {allPass ? (
          <p className="ok" style={{ margin: "0.65rem 0 0", fontWeight: 600, fontSize: "0.9rem" }}>
            Step complete
          </p>
        ) : null}
      </div>
    </article>
  );
}
