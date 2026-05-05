import { useState } from "react";
import { ReplayViewer } from "@/components/ReplayViewer";
import { EditorPage } from "@/editor/EditorPage";
import { SpriteCalibratorPage } from "@/sprites/SpriteCalibratorPage";
import { CartographerPage } from "@/cartographer/CartographerPage";

type Tab = "viewer" | "editor" | "sprites" | "cartographer";

function initialTab(): Tab {
  const tab = new URLSearchParams(window.location.search).get("tab");
  return tab === "editor" || tab === "sprites" || tab === "cartographer" ? tab : "viewer";
}

export default function App() {
  const [tab, setTab] = useState<Tab>(() => initialTab());

  function selectTab(next: Tab): void {
    setTab(next);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", next);
    window.history.replaceState(null, "", url);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100dvh",
        minHeight: 0,
        background: "#0d1117",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 0,
          background: "#161b22",
          borderBottom: "1px solid #21262d",
          flexShrink: 0,
        }}
      >
        {(["viewer", "editor", "sprites", "cartographer"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => selectTab(t)}
            style={{
              padding: "8px 20px",
              background: tab === t ? "#1f2937" : "transparent",
              border: "none",
              borderBottom: tab === t ? "2px solid #4a90e2" : "2px solid transparent",
              color: tab === t ? "#cdd9e5" : "#6e7681",
              fontFamily: "monospace",
              fontSize: 13,
              cursor: "pointer",
              textTransform: "capitalize",
            }}
          >
            {t}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: "hidden" }}>
        {tab === "viewer" && <ReplayViewer />}
        {tab === "editor" && <EditorPage />}
        {tab === "sprites" && <SpriteCalibratorPage />}
        {tab === "cartographer" && <CartographerPage />}
      </div>
    </div>
  );
}
