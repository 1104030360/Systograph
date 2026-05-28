import { useEffect } from "react";
import type { DataSourceMode } from "../types";
import { createScanEventSource, parseScanProgressEvent } from "../services/viewerApi";

type Options = {
  mode: DataSourceMode;
  apiBaseUrl: string;
  enabled: boolean;
  onEvent: (event: ReturnType<typeof parseScanProgressEvent>) => void;
  onError: (message: string) => void;
};

export function useScanProgress({ mode, apiBaseUrl, enabled, onEvent, onError }: Options) {
  useEffect(() => {
    if (mode !== "api" || !enabled) return;

    const eventSource = createScanEventSource(apiBaseUrl);

    eventSource.onmessage = (message) => {
      onEvent(parseScanProgressEvent(message.data));
    };

    eventSource.addEventListener("scan_progress", (message) => {
      onEvent(parseScanProgressEvent(message instanceof MessageEvent ? message.data : ""));
    });

    eventSource.onerror = () => {
      onError("SSE connection failed. Using mock progress until backend is available.");
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [apiBaseUrl, enabled, mode, onError, onEvent]);
}
