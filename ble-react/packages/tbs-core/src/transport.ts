/** Frame-level transport port (BLE wraps with chunking). */

export interface TbsFrameTransport {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  writeFrame(frame: Uint8Array): Promise<void>;
  subscribeFrames(onFrame: (frame: Uint8Array) => void): Promise<() => void>;
}
