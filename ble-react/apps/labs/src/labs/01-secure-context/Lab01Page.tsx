import { useMemo } from "react";
import { Link } from "react-router-dom";
import { adjacentLabs } from "../../labCatalog";
import { detectWebBluetoothSupport } from "../../transport/web-bluetooth";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

export function Lab01Page() {
  const support = useMemo(() => detectWebBluetoothSupport(), []);
  const { prevPath, nextPath } = adjacentLabs("01");
  const href = typeof window !== "undefined" ? window.location.href : "";

  const steps: TutorialStepDef[] = [
    {
      id: "secure",
      title: "Secure context",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          Web Bluetooth only works in a <strong>secure context</strong> —{" "}
          <code>https://</code> or <code>http://localhost</code>. Opening a built{" "}
          <code>file://</code> page will fail even in Chrome.
        </p>
      ),
      checks: [
        {
          id: "sc",
          label: `This page is a secure context (${support.secureContext ? "yes" : "no"})`,
          pass: support.secureContext,
        },
      ],
    },
    {
      id: "api",
      title: "Web Bluetooth API",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          The browser must expose <code>navigator.bluetooth.requestDevice</code>. Use{" "}
          <strong>system Chrome or Edge</strong> — Safari, Firefox, and Cursor’s embedded browser
          are not enough for real WinRT BLE.
        </p>
      ),
      do: (
        <dl className="kv">
          <dt>Location</dt>
          <dd className="mono" style={{ wordBreak: "break-all" }}>
            {href}
          </dd>
          <dt>API</dt>
          <dd className={support.supported ? "ok" : "err"}>
            {support.supported ? "available" : "unavailable"}
          </dd>
        </dl>
      ),
      callout: !support.supported ? (
        <Callout variant="warn" title="Fix the browser gate">
          {support.reason}
          <ul style={{ margin: "0.4rem 0 0", paddingLeft: "1.2rem" }}>
            <li>Chrome or Edge (desktop)</li>
            <li>
              Serve with <code>pnpm dev</code> → <code>http://localhost:5174</code>
            </li>
          </ul>
        </Callout>
      ) : (
        <Callout variant="tip" title="Windows tip">
          Later chapters need an OS Bluetooth pair for <code>TESAIoT-*</code>. See{" "}
          <Link to="/diag">/diag</Link> if Connect drops immediately.
        </Callout>
      ),
      checks: [
        {
          id: "bt",
          label: "navigator.bluetooth.requestDevice is available",
          pass: support.supported,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="01"
      title="Browser ready"
      subtitle="Before any GATT work, confirm this tab can talk Bluetooth."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    />
  );
}
