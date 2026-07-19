import type { TutorialCheck } from "./types";

export function StepChecklist({ checks }: { checks: TutorialCheck[] }) {
  return (
    <ul className="check-list">
      {checks.map((c) => (
        <li key={c.id} className={c.pass ? "pass" : undefined}>
          <span className="check-mark" aria-hidden>
            {c.pass ? "✓" : ""}
          </span>
          <span>{c.label}</span>
        </li>
      ))}
    </ul>
  );
}
