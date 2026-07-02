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

// EventSource reconnects on its own after transient drops; only give up after
// this many consecutive failures without a successful message in between.
const MAX_CONSECUTIVE_ERRORS = 3;

export function useScanProgress({ mode, apiBaseUrl, enabled, onEvent, onError }: Options) {
  useEffect(() => {
    if (mode !== "api" || !enabled) return;

    const eventSource = createScanEventSource(apiBaseUrl);
    let consecutiveErrors = 0;

    eventSource.onmessage = (message) => {
      consecutiveErrors = 0;
      onEvent(parseScanProgressEvent(message.data));
    };

    eventSource.addEventListener("scan_progress", (message) => {
      consecutiveErrors = 0;
      onEvent(parseScanProgressEvent(message instanceof MessageEvent ? message.data : ""));
    });

    eventSource.onerror = () => {
      consecutiveErrors += 1;
      if (eventSource.readyState === EventSource.CLOSED || consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        onError("SSE connection failed. Using mock progress until backend is available.");
        eventSource.close();
      }
      // Otherwise the browser is retrying the connection; let it.
    };

    return () => {
      eventSource.close();
    };
  }, [apiBaseUrl, enabled, mode, onError, onEvent]);
}
