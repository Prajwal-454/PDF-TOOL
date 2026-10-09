"use client";
import { useEffect } from "react";

// Desktop app only: keeps a tiny connection open so the local engine knows the
// window is still open, and shuts itself down shortly after the window closes.
export default function DesktopSession() {
  useEffect(() => {
    if (process.env.NEXT_PUBLIC_API_BASE !== "same-origin") return;
    const es = new EventSource("/api/desktop/session");
    return () => es.close();
  }, []);
  return null;
}
