import { ImageResponse } from "next/og";

export const alt = "Goalgebra — Football Analytics & prédictions IA";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OG() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", padding: 72, background: "#0a0e15", color: "#e9edf4" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 44, fontWeight: 700 }}>
          <div style={{ width: 72, height: 72, borderRadius: 18, background: "#111723", display: "flex", alignItems: "center", justifyContent: "center", border: "2px solid #2bb5a5" }}>
            <div style={{ width: 22, height: 22, borderRadius: 11, background: "#2bb5a5" }} />
          </div>
          Goal<span style={{ color: "#2bb5a5" }}>gebra</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ fontSize: 64, fontWeight: 700, lineHeight: 1.1 }}>Football Analytics & probabilités IA</div>
          <div style={{ fontSize: 30, color: "#a3adbf" }}>Matchs du jour · statistiques · classements · modèle transparent</div>
        </div>
        <div style={{ display: "flex", height: 14, borderRadius: 7, overflow: "hidden", gap: 4 }}>
          <div style={{ width: "52%", background: "#4b93ec" }} /><div style={{ width: "26%", background: "#8d8b84" }} /><div style={{ width: "22%", background: "#e0662f" }} />
        </div>
      </div>
    ),
    size,
  );
}
