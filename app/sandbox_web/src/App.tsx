import { useState } from "react";
import { ReplayViewer } from "@/components/ReplayViewer";
import { EditorPage } from "@/editor/EditorPage";
import { SpriteCalibratorPage } from "@/sprites/SpriteCalibratorPage";

type Tab = "viewer" | "editor" | "sprites";

export default function App() {
  const [tab, setTab] = useState<Tab>("viewer");

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
        {(["viewer", "editor", "sprites"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
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
      </div>
    </div>
  );
}
