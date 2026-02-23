import {loadFont as loadInter} from "@remotion/google-fonts/Inter";
import {AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

const {fontFamily} = loadInter("normal", {
  weights: ["300", "400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

const graphNodes = [
  "Vectors",
  "Newtons Laws",
  "Work",
  "Calculus",
  "Kinetic Energy",
  "Force",
  "Work Energy Theorem",
  "Momentum",
  "Power",
] as const;

type SelectedNode = "chapter" | "Work";

type GraphSceneProps = {
  selectedNode: SelectedNode;
  showWorkClick: boolean;
};

const graphInsights = [
  {
    label: "Competency",
    color: "#15803d",
    bg: "#dcfce7",
    type: "conceptual",
    title: "Work_Energy_Theorem",
    body: "Student links net work done to kinetic-energy change and applies the theorem correctly across examples.",
    bar: "#10b981",
  },
  {
    label: "Partial Understanding",
    color: "#d97706",
    bg: "#fef3c7",
    type: "conceptual",
    title: "Conservative Forces",
    body: "Student identifies conservative-force cases but still struggles with choosing potential-energy reference points.",
    bar: "#f59e0b",
  },
  {
    label: "Misconception",
    color: "#dc2626",
    bg: "#fee2e2",
    type: "conceptual",
    title: "Mechanical Energy",
    body: "Student interprets conservation as increase in total energy, instead of conversion between K and V.",
    bar: "#f43f5e",
  },
];

const renderInsights = (mode: SelectedNode) => {
  if (mode === "Work") {
    return [
      {
        label: "Misconception",
        color: "#dc2626",
        bg: "#fee2e2",
        type: "conceptual",
        title: "Dot Product vs Cross Product",
        body: "Student confuses cross product with dot product while defining work in force-displacement context.",
        bar: "#f43f5e",
      },
      {
        label: "Competency",
        color: "#15803d",
        bg: "#dcfce7",
        type: "conceptual",
        title: "Definition of Work",
        body: "Student correctly applies W = F·s and interprets units and direction in standard examples.",
        bar: "#10b981",
      },
    ];
  }

  return graphInsights;
};

const GraphSceneBase: React.FC<GraphSceneProps> = ({selectedNode, showWorkClick}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const inAnim = spring({
    frame,
    fps,
    config: {damping: 200},
    durationInFrames: Math.round(0.8 * fps),
  });

  const centerPulse = interpolate(frame % Math.round(1.8 * fps), [0, 0.9 * fps, 1.8 * fps], [1, 1.09, 1], {
    easing: Easing.inOut(Easing.quad),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const workBlink = interpolate(frame % Math.round(1.1 * fps), [0, 0.55 * fps, 1.1 * fps], [0.2, 0.85, 0.2], {
    easing: Easing.inOut(Easing.quad),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const workClick = interpolate(frame, [2.05 * fps, 2.25 * fps, 2.5 * fps], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  const centerX = 660;
  const centerY = 540;
  const radius = 280;

  const selectedTitle = selectedNode === "Work" ? "Work" : "Work, Energy and Power";
  const selectedSubtitle = selectedNode === "Work" ? "Prerequisite Concept" : "Chapter Overview";

  return (
    <AbsoluteFill style={{fontFamily, backgroundColor: "#f9fafb", color: "#0f172a"}}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 72,
          borderBottom: "1px solid #e2e8f0",
          backgroundColor: "#fff",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          zIndex: 20,
        }}
      >
        <div style={{display: "flex", alignItems: "center", gap: 12}}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              backgroundColor: "#000",
              color: "#fff",
              display: "grid",
              placeItems: "center",
              fontWeight: 700,
              fontSize: 16,
            }}
          >
            △
          </div>
          <div style={{fontWeight: 700, fontSize: 34}}>LearnerOS</div>
        </div>
        <div style={{display: "flex", alignItems: "center", gap: 18}}>
          <div style={{textAlign: "right", fontSize: 11, textTransform: "uppercase", letterSpacing: 1.1}}>
            <div style={{fontWeight: 800}}>Samanapalli Srichandra</div>
            <div style={{color: "#64748b", marginTop: 2}}>Sign Out</div>
          </div>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 999,
              background: "linear-gradient(135deg, #34d399, #0d9488)",
              color: "#fff",
              display: "grid",
              placeItems: "center",
              fontSize: 10,
              fontWeight: 700,
            }}
          >
            SAMA
          </div>
        </div>
      </div>

      <div style={{position: "absolute", top: 72, left: 0, right: 480, bottom: 0, overflow: "hidden"}}>
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "radial-gradient(#e5e7eb 1px, transparent 1px), radial-gradient(#e5e7eb 1px, transparent 1px)",
            backgroundSize: "24px 24px, 24px 24px",
            backgroundPosition: "0 0, 12px 12px",
          }}
        />
        <div style={{position: "absolute", top: 24, left: 24}}>
          <button
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: 999,
              padding: "10px 14px",
              backgroundColor: "#fff",
              fontSize: 12,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            ← BACK TO TEXTBOOK
          </button>
        </div>
        <div
          style={{
            position: "absolute",
            top: 24,
            left: "50%",
            transform: "translateX(-50%)",
            border: "1px solid #e2e8f0",
            borderRadius: 999,
            padding: "9px 14px",
            backgroundColor: "#fff",
            fontSize: 12,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span style={{color: "#0d9488", fontWeight: 700}}>i</span>
          Select any node to view insights and 3D animations
        </div>

        <svg style={{position: "absolute", inset: 0, width: "100%", height: "100%"}}>
          {graphNodes.map((_, i) => {
            const a = -Math.PI / 2 + (i / graphNodes.length) * Math.PI * 2;
            const x = centerX + Math.cos(a) * radius;
            const y = centerY + Math.sin(a) * radius;
            return <line key={`line-${String(i)}`} x1={centerX} y1={centerY} x2={x} y2={y} stroke="#e2e8f0" strokeWidth={1.2} />;
          })}
        </svg>

        <div
          style={{
            position: "absolute",
            left: centerX - 64,
            top: centerY - 64,
            width: 128,
            height: 128,
            borderRadius: 999,
            backgroundColor: "#fff",
            border: "4px solid #0d9488",
            display: "grid",
            placeItems: "center",
            transform: `scale(${selectedNode === "chapter" ? centerPulse : 1})`,
            boxShadow: `0 0 0 10px rgba(13,148,136,${selectedNode === "chapter" ? 0.1 : 0.03})`,
          }}
        >
          <span style={{fontSize: 46, color: "#0d9488"}}>💡</span>
        </div>
        <div
          style={{
            position: "absolute",
            left: centerX - 132,
            top: centerY + 76,
            width: 264,
            borderRadius: 999,
            backgroundColor: "#111827",
            color: "#fff",
            textAlign: "center",
            padding: "7px 12px",
            boxShadow: "0 10px 22px -15px rgba(17,24,39,0.7)",
          }}
        >
          <div style={{fontSize: 10, fontWeight: 700, letterSpacing: 1.2, textTransform: "uppercase", opacity: 0.7}}>
            Chapter 5
          </div>
          <div style={{fontSize: 12, fontWeight: 700, textTransform: "uppercase"}}>Work, Energy and Power</div>
        </div>

        {graphNodes.map((name, i) => {
          const a = -Math.PI / 2 + (i / graphNodes.length) * Math.PI * 2;
          const x = centerX + Math.cos(a) * radius;
          const y = centerY + Math.sin(a) * radius;
          const delay = i * 2;
          const nodeIn = spring({
            frame: frame - delay,
            fps,
            config: {damping: 200},
            durationInFrames: Math.round(0.6 * fps),
          });

          const isWork = name === "Work";
          const isSelected = selectedNode === "Work" && isWork;
          const workScale = showWorkClick && isWork ? interpolate(workClick, [0, 1], [1, 0.9]) : 1;

          return (
            <div
              key={name}
              style={{
                position: "absolute",
                left: x - 32,
                top: y - 32,
                transform: `scale(${interpolate(nodeIn, [0, 1], [0.84, 1]) * workScale})`,
                opacity: interpolate(nodeIn, [0, 1], [0, 1]),
              }}
            >
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 999,
                  backgroundColor: "#fff",
                  border: isSelected ? "2px solid #0d9488" : "1px solid #dbe3ed",
                  display: "grid",
                  placeItems: "center",
                  boxShadow: isSelected
                    ? `0 0 0 8px rgba(13,148,136,${workBlink}), 0 6px 16px -12px rgba(15,23,42,0.35)`
                    : "0 6px 16px -12px rgba(15,23,42,0.35)",
                }}
              >
                <span style={{color: isSelected ? "#0d9488" : "#64748b", fontSize: 26}}>⚗</span>
              </div>
              <div
                style={{
                  marginTop: 8,
                  marginLeft: "50%",
                  transform: "translateX(-50%)",
                  whiteSpace: "nowrap",
                  backgroundColor: isSelected ? "#000" : "#fff",
                  color: isSelected ? "#fff" : "#111827",
                  border: "1px solid #e2e8f0",
                  borderRadius: 999,
                  padding: "4px 10px",
                  fontSize: 10,
                  fontWeight: 700,
                  textTransform: "uppercase",
                }}
              >
                {name}
              </div>
            </div>
          );
        })}
      </div>

      <aside
        style={{
          position: "absolute",
          top: 72,
          right: 0,
          width: 480,
          bottom: 0,
          backgroundColor: "#fff",
          borderLeft: "1px solid #e2e8f0",
          padding: 26,
          transform: `translateX(${interpolate(inAnim, [0, 1], [28, 0])}px)`,
          opacity: interpolate(inAnim, [0, 1], [0, 1]),
          boxShadow: "-18px 0 28px -28px rgba(15,23,42,0.35)",
        }}
      >
        <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
          <div style={{display: "flex", gap: 8, alignItems: "center"}}>
            <span
              style={{
                backgroundColor: "#111827",
                color: "#fff",
                fontSize: 10,
                fontWeight: 700,
                padding: "5px 8px",
                borderRadius: 6,
                textTransform: "uppercase",
                letterSpacing: 1,
              }}
            >
              Insights
            </span>
            <span style={{fontSize: 24, fontWeight: 700}}>Node Profile</span>
          </div>
          <button style={{border: "none", background: "none", color: "#64748b", fontSize: 22}}>×</button>
        </div>

        <div style={{marginTop: 20}}>
          <div style={{fontSize: 56, fontWeight: 800, lineHeight: 1.05}}>{selectedTitle}</div>
          <div style={{marginTop: 8, fontSize: 11, color: "#0d9488", textTransform: "uppercase", letterSpacing: 2, fontWeight: 700}}>
            {selectedSubtitle}
          </div>
        </div>

        {selectedNode === "Work" ? (
          <button
            style={{
              marginTop: 18,
              border: "none",
              borderRadius: 12,
              backgroundColor: "#000",
              color: "#fff",
              padding: "12px 14px",
              width: "100%",
              textAlign: "left",
              fontSize: 16,
              fontWeight: 700,
            }}
          >
            ◉ View 3D Animation
          </button>
        ) : null}

        <div style={{display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 22}}>
          {[
            ["Competency", selectedNode === "Work" ? "1" : "3", "#10b981"],
            ["Partial Understanding", selectedNode === "Work" ? "0" : "3", "#f59e0b"],
            ["Misconception", selectedNode === "Work" ? "1" : "4", "#f43f5e"],
          ].map(([label, value, color]) => (
            <div key={String(label)} style={{border: "1px solid #e2e8f0", backgroundColor: "#f8fafc", borderRadius: 10, padding: 12}}>
              <div style={{fontSize: 9, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1, fontWeight: 700}}>
                {label}
              </div>
              <div style={{marginTop: 8, fontSize: 38, lineHeight: 1, fontWeight: 800, color}}>{value}</div>
            </div>
          ))}
        </div>

        <div style={{marginTop: 24}}>
          <div style={{display: "flex", gap: 8, alignItems: "center"}}>
            <span style={{color: "#0d9488", fontSize: 16}}>✦</span>
            <span style={{fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: 1.5, fontWeight: 700}}>
              Learning Insights
            </span>
          </div>
          <div style={{marginTop: 10, display: "flex", flexDirection: "column", gap: 10}}>
            {renderInsights(selectedNode).map((insight) => (
              <div key={insight.title} style={{border: "1px solid #e2e8f0", borderRadius: 14, padding: 14, position: "relative"}}>
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 6,
                    backgroundColor: insight.bar,
                    borderTopLeftRadius: 14,
                    borderBottomLeftRadius: 14,
                  }}
                />
                <div style={{display: "flex", justifyContent: "space-between", marginLeft: 10, alignItems: "center"}}>
                  <span
                    style={{
                      fontSize: 10,
                      color: insight.color,
                      textTransform: "uppercase",
                      letterSpacing: 1.2,
                      fontWeight: 700,
                      backgroundColor: insight.bg,
                      padding: "4px 7px",
                      borderRadius: 999,
                    }}
                  >
                    {insight.label}
                  </span>
                  <span style={{fontSize: 10, color: "#94a3b8", textTransform: "uppercase"}}>{insight.type}</span>
                </div>
                <div style={{marginTop: 9, marginLeft: 10, fontSize: 13, fontWeight: 700}}>{insight.title}</div>
                <div style={{marginTop: 7, marginLeft: 10, fontSize: 12, color: "#475569", lineHeight: 1.5}}>{insight.body}</div>
              </div>
            ))}
          </div>
        </div>
      </aside>
    </AbsoluteFill>
  );
};

export const KnowledgeGraphScene = () => {
  return <GraphSceneBase selectedNode="chapter" showWorkClick={true} />;
};

export const KnowledgeGraphWorkScene = () => {
  return <GraphSceneBase selectedNode="Work" showWorkClick={false} />;
};
