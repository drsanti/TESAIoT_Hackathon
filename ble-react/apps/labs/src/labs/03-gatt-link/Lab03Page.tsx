import { formatLinkSnapshot, linkMtuHint } from "@ternion/tbs-core";
import { ConnectBar } from "../../components/ConnectBar";
import { adjacentLabs } from "../../labCatalog";
import { useBleSession } from "../../hooks/useBleSession";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";
import { Link } from "react-router-dom";

export function Lab03Page() {
  const { chars, link, readLink, phase } = useBleSession();
  const linked = phase === "linked" || phase === "live";
  const mtuHint = link ? linkMtuHint(link) : null;
  const { prevPath, nextPath } = adjacentLabs("03");
  const hasRx = chars.some((c) => c.label === "BS_RX");
  const hasTx = chars.some((c) => c.label === "BS_TX");
  const hasLink = chars.some((c) => c.label === "BS_LINK");

  const steps: TutorialStepDef[] = [
    {
      id: "connect",
      title: "Connect GATT",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          After the chooser, <code>gatt.connect()</code> opens the ATT link. On Windows Chrome the
          link can drop in a few milliseconds if the board was never paired at the OS level — host
          tools may still work. Prefer system Chrome/Edge and pair <code>TESAIoT-*</code> first.
        </p>
      ),
      do: <ConnectBar hint="Always pick the board fresh in the chooser (address may rotate)." />,
      callout: (
        <Callout variant="warn" title="Connect drops immediately?">
          Open <Link to="/diag">/diag</Link> → Run all 1→6 after Windows Bluetooth pair + soft-blue
          RESET.
        </Callout>
      ),
      checks: [
        {
          id: "linked",
          label: "Session phase is linked or live",
          pass: linked,
        },
      ],
    },
    {
      id: "chars",
      title: "Discover BS2 characteristics",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          The teaching service exposes <strong>BS_RX</strong> (host→device writes),{" "}
          <strong>BS_TX</strong> (device→host notifies), and <strong>BS_LINK</strong> (status
          snapshot). Discovery should start immediately after connect.
        </p>
      ),
      do:
        chars.length === 0 ? (
          <p className="muted">Connect first — characteristics appear here.</p>
        ) : (
          <ul className="checklist">
            {chars.map((c) => (
              <li key={c.uuid}>
                <strong>{c.label}</strong> — {c.properties.join(", ") || "(none)"}
                <div className="muted mono" style={{ fontSize: "0.75rem" }}>
                  {c.uuid}
                </div>
              </li>
            ))}
          </ul>
        ),
      checks: [
        { id: "rx", label: "BS_RX discovered", pass: hasRx },
        { id: "tx", label: "BS_TX discovered", pass: hasTx },
        { id: "linkChar", label: "BS_LINK discovered", pass: hasLink },
      ],
    },
    {
      id: "read-link",
      title: "Read BS_LINK",
      why: (
        <p className="step-why" style={{ margin: 0 }}>
          BS_LINK is a small status characteristic (connection state, MTU, drop counters). Reading
          it proves the ATT path works before you enable notifications.
        </p>
      ),
      do: (
        <div>
          <div className="btn-row">
            <button type="button" disabled={!linked} onClick={() => void readLink()}>
              Re-read BS_LINK
            </button>
          </div>
          {link ? (
            <>
              <p className="ok" style={{ marginTop: "0.75rem" }}>
                {formatLinkSnapshot(link)}
              </p>
              {mtuHint ? <p className="muted">{mtuHint}</p> : null}
            </>
          ) : (
            <p className="muted" style={{ marginTop: "0.65rem" }}>
              No snapshot yet — connect usually reads LINK once automatically.
            </p>
          )}
        </div>
      ),
      checks: [
        {
          id: "snapshot",
          label: "BS_LINK snapshot received (state / mtu / drops)",
          pass: link != null,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="03"
      title="Open the GATT link"
      subtitle="Connect, discover the BitStream BLE service, and read the link snapshot."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    />
  );
}
