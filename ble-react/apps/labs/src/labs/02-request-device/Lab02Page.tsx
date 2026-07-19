import { useState } from "react";
import { BS2_BLE_ADV_NAME_PREFIX, BS2_BLE_SERVICE_UUID } from "@ternion/tbs-core";
import { adjacentLabs } from "../../labCatalog";
import { detectWebBluetoothSupport } from "../../transport/web-bluetooth";
import { Callout, TutorialShell, type TutorialStepDef } from "../../tutorial";

export function Lab02Page() {
  const [name, setName] = useState<string | null>(null);
  const [id, setId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { prevPath, nextPath } = adjacentLabs("02");

  const onRequest = async () => {
    setError(null);
    setBusy(true);
    try {
      const support = detectWebBluetoothSupport();
      if (!support.supported) throw new Error(support.reason);
      const device = await navigator.bluetooth.requestDevice({
        filters: [{ namePrefix: BS2_BLE_ADV_NAME_PREFIX }],
        optionalServices: [BS2_BLE_SERVICE_UUID],
      });
      setName(device.name ?? "(unnamed)");
      setId(device.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const steps: TutorialStepDef[] = [
    {
      id: "gesture",
      title: "User gesture required",
      why: (
        <>
          <p className="step-why" style={{ margin: 0 }}>
            Chrome will not open the Bluetooth chooser unless the call to{" "}
            <code>requestDevice</code> happens from a <strong>click</strong> (or similar user
            gesture). Filters keep the list short: name prefix{" "}
            <code>{BS2_BLE_ADV_NAME_PREFIX}</code>.
          </p>
          <p className="step-why" style={{ margin: "0.5rem 0 0" }}>
            This chapter only <em>picks</em> the peripheral. Chapter 03 opens GATT. Always use a
            fresh picker — BLE addresses can rotate (RPA).
          </p>
        </>
      ),
      do: (
        <div>
          <div className="btn-row">
            <button className="primary" type="button" disabled={busy} onClick={() => void onRequest()}>
              {busy ? "Waiting for picker…" : "Request device"}
            </button>
          </div>
          {name ? (
            <dl className="kv" style={{ marginTop: "1rem" }}>
              <dt>Name</dt>
              <dd className="ok">{name}</dd>
              <dt>Id</dt>
              <dd className="mono">{id}</dd>
            </dl>
          ) : null}
          {error ? <p className="err">{error}</p> : null}
        </div>
      ),
      callout: (
        <Callout variant="info" title="Board not in the list?">
          Press board <strong>RESET</strong> until the TFT is soft-blue (advertising). Close other
          BLE centrals (nRF Connect, Python labs).
        </Callout>
      ),
      checks: [
        {
          id: "picked",
          label: "A TESAIoT-* device was selected in the browser picker",
          pass: name != null,
        },
      ],
    },
  ];

  return (
    <TutorialShell
      labId="02"
      title="Pick the board"
      subtitle="Practice the Web Bluetooth chooser without connecting GATT yet."
      steps={steps}
      prevPath={prevPath}
      nextPath={nextPath}
    />
  );
}
