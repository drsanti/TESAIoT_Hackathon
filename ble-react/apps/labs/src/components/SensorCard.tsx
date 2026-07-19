import type { ReactNode } from "react";
import {
  formatSwBtnState,
  SENSOR_ADC_POT,
  SENSOR_BMI270,
  SENSOR_BMM350,
  SENSOR_DPS368,
  SENSOR_NAMES,
  SENSOR_SHT40,
  SENSOR_SW_BTN,
  type SensorSample,
} from "@ternion/tbs-core";

function fmt(n: number | undefined, digits = 2): string {
  if (n === undefined || Number.isNaN(n)) return "—";
  return n.toFixed(digits);
}

/** One labeled group; values on a single horizontal row. */
function FieldGroup({
  label,
  fields,
  entries,
  digits = 2,
}: {
  label: string;
  fields: Record<string, number>;
  entries: { key: string; short: string }[];
  digits?: number;
}) {
  const present = entries.some((e) => fields[e.key] !== undefined);
  if (!present) {
    return (
      <div className="field-group">
        <div className="field-group-label">{label}</div>
        <div className="field-group-values muted">—</div>
      </div>
    );
  }
  return (
    <div className="field-group">
      <div className="field-group-label">{label}</div>
      <div className="field-group-values">
        {entries.map((e) => (
          <span key={e.key} className="field-chip">
            <span className="field-chip-key">{e.short}</span>
            <span className="field-chip-val">{fmt(fields[e.key], digits)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

function FieldRows({ fields, keys }: { fields: Record<string, number>; keys: string[] }) {
  return (
    <div className="fields">
      {keys.map((k) => (
        <div key={k}>
          <span>{k}</span> {fmt(fields[k])}
        </div>
      ))}
    </div>
  );
}

export function SensorCard({
  sensorId,
  sample,
  count = 0,
}: {
  sensorId: number;
  sample?: SensorSample;
  count?: number;
}) {
  const title = SENSOR_NAMES[sensorId] ?? `sensor ${sensorId}`;
  const fields = sample?.fields ?? {};

  let body: ReactNode;
  if (!sample) {
    body = <p className="muted">Waiting for EVT…</p>;
  } else if (sensorId === SENSOR_BMI270) {
    body = (
      <div className="field-groups">
        <FieldGroup
          label="Accel"
          fields={fields}
          entries={[
            { key: "accelX", short: "X" },
            { key: "accelY", short: "Y" },
            { key: "accelZ", short: "Z" },
          ]}
        />
        <FieldGroup
          label="Gyro"
          fields={fields}
          entries={[
            { key: "gyroX", short: "X" },
            { key: "gyroY", short: "Y" },
            { key: "gyroZ", short: "Z" },
          ]}
        />
        <FieldGroup
          label="Temp"
          fields={fields}
          entries={[{ key: "temperatureC", short: "°C" }]}
        />
        <FieldGroup
          label="Euler (rad)"
          fields={fields}
          entries={[
            { key: "headingRad", short: "heading" },
            { key: "pitchRad", short: "pitch" },
            { key: "rollRad", short: "roll" },
          ]}
        />
        <FieldGroup
          label="Quaternion"
          fields={fields}
          entries={[
            { key: "quatW", short: "W" },
            { key: "quatX", short: "X" },
            { key: "quatY", short: "Y" },
            { key: "quatZ", short: "Z" },
          ]}
          digits={4}
        />
      </div>
    );
  } else if (sensorId === SENSOR_BMM350) {
    body = (
      <div className="field-groups">
        <FieldGroup
          label="Mag"
          fields={fields}
          entries={[
            { key: "magX", short: "X" },
            { key: "magY", short: "Y" },
            { key: "magZ", short: "Z" },
          ]}
        />
        <FieldGroup
          label="Temp"
          fields={fields}
          entries={[{ key: "temperatureC", short: "°C" }]}
        />
      </div>
    );
  } else if (sensorId === SENSOR_SHT40) {
    body = (
      <div className="field-groups">
        <FieldGroup
          label="Environment"
          fields={fields}
          entries={[
            { key: "temperatureC", short: "°C" },
            { key: "humidityPct", short: "%RH" },
          ]}
        />
      </div>
    );
  } else if (sensorId === SENSOR_DPS368) {
    body = (
      <div className="field-groups">
        <FieldGroup
          label="Pressure"
          fields={fields}
          entries={[
            { key: "pressureHpa", short: "hPa" },
            { key: "temperatureC", short: "°C" },
          ]}
        />
      </div>
    );
  } else if (sensorId === SENSOR_ADC_POT) {
    body = (
      <div className="field-groups">
        <FieldGroup
          label="Pots (mV)"
          fields={fields}
          entries={[
            { key: "pot1_mv", short: "1" },
            { key: "pot2_mv", short: "2" },
            { key: "pot3_mv", short: "3" },
            { key: "pot4_mv", short: "4" },
          ]}
          digits={0}
        />
      </div>
    );
  } else if (sensorId === SENSOR_SW_BTN) {
    body = (
      <div className="field-groups">
        <div className="field-group">
          <div className="field-group-label">Buttons</div>
          <div className="field-group-values">
            <span className="field-chip">
              <span className="field-chip-key">state</span>
              <span className="field-chip-val">{formatSwBtnState(fields.state ?? 0)}</span>
            </span>
            <span className="field-chip">
              <span className="field-chip-key">btn0</span>
              <span className="field-chip-val">{fields.btn0_count ?? "—"}</span>
            </span>
            <span className="field-chip">
              <span className="field-chip-key">btn1</span>
              <span className="field-chip-val">{fields.btn1_count ?? "—"}</span>
            </span>
            <span className="field-chip">
              <span className="field-chip-key">btn2</span>
              <span className="field-chip-val">{fields.btn2_count ?? "—"}</span>
            </span>
          </div>
        </div>
      </div>
    );
  } else {
    body = <FieldRows fields={fields} keys={Object.keys(fields)} />;
  }

  return (
    <div className="sensor-card">
      <h3>
        <span>{title}</span>
        <span className="count">n={count}</span>
      </h3>
      {body}
      {sample ? (
        <p className="muted" style={{ margin: "0.5rem 0 0", fontSize: "0.75rem" }}>
          ctr={sample.counter} · deviceMs={sample.deviceMs} · mask=0x{sample.mask.toString(16)}
        </p>
      ) : null}
    </div>
  );
}
