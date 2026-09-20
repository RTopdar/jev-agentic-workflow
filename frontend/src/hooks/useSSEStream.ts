import { useEffect, useRef } from "react";

export function useSSEStream(
  url: string | null,
  onToken: (token: string) => void,
  onDone: () => void
): void {
  const onTokenRef = useRef(onToken);
  const onDoneRef = useRef(onDone);
  onTokenRef.current = onToken;
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!url) return;

    const source = new EventSource(url);
    source.onmessage = (event) => {
      onTokenRef.current(event.data);
    };
    source.addEventListener("done", () => {
      onDoneRef.current();
      source.close();
    });
    source.onerror = () => {
      source.close();
    };

    return () => source.close();
  }, [url]);
}
