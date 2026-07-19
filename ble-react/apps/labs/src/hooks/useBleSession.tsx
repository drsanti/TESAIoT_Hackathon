import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  createTbsBleSession,
  type ConnPhase,
  type TbsBleSession,
} from "@ternion/tbs-ble-session";
import type { LinkSnapshot, SensorSample } from "@ternion/tbs-core";
import {
  createWebBluetoothTransport,
  isUserCancelledBleError,
  type CharInfo,
  type WebBluetoothTransport,
} from "../transport/web-bluetooth";
import {
  createHostBleBridgeTransport,
  type HostBleBridgeTransport,
} from "../transport/host-ble-bridge";
import {
  readBleTransportMode,
  writeBleTransportMode,
  type BleTransportMode,
} from "../transport/ble-transport-mode";

type AnyTransport = WebBluetoothTransport | HostBleBridgeTransport;

type BleContextValue = {
  phase: ConnPhase;
  device: { name: string; address: string } | null;
  link: LinkSnapshot | null;
  latest: Map<number, SensorSample>;
  counts: Map<number, number>;
  logs: string[];
  chars: CharInfo[];
  sampleTick: number;
  lastError: string | null;
  transportMode: BleTransportMode;
  setTransportMode: (mode: BleTransportMode) => void;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  goLive: (settleMs?: number) => Promise<void>;
  enableStreaming: TbsBleSession["enableStreaming"];
  ping: TbsBleSession["ping"];
  setBlePolicy: TbsBleSession["setBlePolicy"];
  applyCfgsFire: TbsBleSession["applyCfgsFire"];
  writeReqFire: TbsBleSession["writeReqFire"];
  readLink: () => Promise<LinkSnapshot>;
  clearCounts: () => void;
};

const BleContext = createContext<BleContextValue | null>(null);

export function BleSessionProvider({ children }: { children: ReactNode }) {
  const transportRef = useRef<AnyTransport | null>(null);
  const sessionRef = useRef<TbsBleSession | null>(null);
  const connectInFlightRef = useRef(false);

  const [transportMode, setTransportModeState] = useState<BleTransportMode>(() =>
    readBleTransportMode(),
  );
  const [phase, setPhase] = useState<ConnPhase>("idle");
  const [device, setDevice] = useState<{ name: string; address: string } | null>(null);
  const [link, setLink] = useState<LinkSnapshot | null>(null);
  const [latest, setLatest] = useState(() => new Map<number, SensorSample>());
  const [counts, setCounts] = useState(() => new Map<number, number>());
  const [logs, setLogs] = useState<string[]>([]);
  const [chars, setChars] = useState<CharInfo[]>([]);
  const [sampleTick, setSampleTick] = useState(0);
  const [lastError, setLastError] = useState<string | null>(null);

  const destroySession = useCallback(async () => {
    const session = sessionRef.current;
    sessionRef.current = null;
    transportRef.current = null;
    if (session) {
      try {
        await session.disconnect();
      } catch {
        /* ignore */
      }
    }
  }, []);

  const ensureSession = useCallback(() => {
    if (sessionRef.current) return sessionRef.current;
    const mode = transportMode;
    const transport: AnyTransport =
      mode === "bridge"
        ? createHostBleBridgeTransport({
            onDisconnected: () => {
              setPhase("idle");
              setDevice(null);
              setChars([]);
              setLink(null);
              setLogs((prev) => [`[warn] Bridge / GATT disconnected`, ...prev].slice(0, 80));
            },
            onLog: (level, msg) => {
              setLogs((prev) => [`[${level}] ${msg}`, ...prev].slice(0, 80));
            },
          })
        : createWebBluetoothTransport({
            onDisconnected: () => {
              setPhase("idle");
              setDevice(null);
              setChars([]);
              setLink(null);
              setLogs((prev) => [`[warn] GATT disconnected`, ...prev].slice(0, 80));
            },
          });
    transportRef.current = transport;
    const session = createTbsBleSession(transport, {
      onPhase: setPhase,
      onLink: setLink,
      onLog: (level, msg) => {
        setLogs((prev) => [`[${level}] ${msg}`, ...prev].slice(0, 80));
      },
      onSample: (sample) => {
        setLatest((prev) => {
          const next = new Map(prev);
          next.set(sample.sensorId, sample);
          return next;
        });
        setCounts((prev) => {
          const next = new Map(prev);
          next.set(sample.sensorId, (prev.get(sample.sensorId) ?? 0) + 1);
          return next;
        });
        setSampleTick((t) => t + 1);
      },
    });
    sessionRef.current = session;
    return session;
  }, [transportMode]);

  const setTransportMode = useCallback(
    (mode: BleTransportMode) => {
      writeBleTransportMode(mode);
      setTransportModeState(mode);
      void destroySession().then(() => {
        setDevice(null);
        setChars([]);
        setLink(null);
        setPhase("idle");
        setLastError(null);
        setLogs((prev) =>
          [`[info] Transport → ${mode === "bridge" ? "host Node bridge" : "Web Bluetooth"}`, ...prev].slice(
            0,
            80,
          ),
        );
      });
    },
    [destroySession],
  );

  const connect = useCallback(async () => {
    if (connectInFlightRef.current) return;
    connectInFlightRef.current = true;
    setLastError(null);
    try {
      if (phase === "error" || phase === "idle") {
        await destroySession();
      }
      const session = ensureSession();
      try {
        await session.connect();
        setDevice(session.getDevice());
        setChars(transportRef.current?.listCharacteristics() ?? []);
        setLastError(null);
      } catch (e) {
        setDevice(null);
        setChars([]);
        if (transportMode === "web" && isUserCancelledBleError(e)) {
          setLastError(null);
          setPhase("idle");
          await destroySession();
          return;
        }
        const msg = e instanceof Error ? e.message : String(e);
        setLastError(msg);
        await destroySession();
        setPhase("error");
      }
    } finally {
      connectInFlightRef.current = false;
    }
  }, [destroySession, ensureSession, phase, transportMode]);

  const disconnect = useCallback(async () => {
    setLastError(null);
    await destroySession();
    setDevice(null);
    setChars([]);
    setLink(null);
    setPhase("idle");
  }, [destroySession]);

  const goLive = useCallback(
    async (settleMs?: number) => {
      const session = ensureSession();
      await session.goLive(settleMs);
    },
    [ensureSession],
  );

  const enableStreaming = useCallback(
    async (...args: Parameters<TbsBleSession["enableStreaming"]>) => {
      const session = ensureSession();
      await session.enableStreaming(...args);
    },
    [ensureSession],
  );

  const ping = useCallback(
    async (...args: Parameters<TbsBleSession["ping"]>) => {
      const session = ensureSession();
      return session.ping(...args);
    },
    [ensureSession],
  );

  const setBlePolicy = useCallback(
    async (...args: Parameters<TbsBleSession["setBlePolicy"]>) => {
      const session = ensureSession();
      return session.setBlePolicy(...args);
    },
    [ensureSession],
  );

  const applyCfgsFire = useCallback(
    async (...args: Parameters<TbsBleSession["applyCfgsFire"]>) => {
      const session = ensureSession();
      return session.applyCfgsFire(...args);
    },
    [ensureSession],
  );

  const writeReqFire = useCallback(
    async (...args: Parameters<TbsBleSession["writeReqFire"]>) => {
      const session = ensureSession();
      return session.writeReqFire(...args);
    },
    [ensureSession],
  );

  const readLink = useCallback(async () => {
    const session = ensureSession();
    return session.readLink();
  }, [ensureSession]);

  const clearCounts = useCallback(() => {
    setCounts(new Map());
    setLatest(new Map());
    setSampleTick(0);
  }, []);

  const value = useMemo<BleContextValue>(
    () => ({
      phase,
      device,
      link,
      latest,
      counts,
      logs,
      chars,
      sampleTick,
      lastError,
      transportMode,
      setTransportMode,
      connect,
      disconnect,
      goLive,
      enableStreaming,
      ping,
      setBlePolicy,
      applyCfgsFire,
      writeReqFire,
      readLink,
      clearCounts,
    }),
    [
      phase,
      device,
      link,
      latest,
      counts,
      logs,
      chars,
      sampleTick,
      lastError,
      transportMode,
      setTransportMode,
      connect,
      disconnect,
      goLive,
      enableStreaming,
      ping,
      setBlePolicy,
      applyCfgsFire,
      writeReqFire,
      readLink,
      clearCounts,
    ],
  );

  return <BleContext.Provider value={value}>{children}</BleContext.Provider>;
}

export function useBleSession(): BleContextValue {
  const ctx = useContext(BleContext);
  if (!ctx) throw new Error("useBleSession requires BleSessionProvider");
  return ctx;
}
