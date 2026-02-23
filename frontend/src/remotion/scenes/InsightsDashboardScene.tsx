import {loadFont as loadOutfit} from "@remotion/google-fonts/Outfit";
import {loadFont as loadSpaceGrotesk} from "@remotion/google-fonts/SpaceGrotesk";
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

const {fontFamily: displayFont} = loadSpaceGrotesk("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});
const {fontFamily: bodyFont} = loadOutfit("normal", {
  weights: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
});

export const InsightsDashboardScene = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const sceneIn = spring({
    frame,
    fps,
    config: {damping: 200},
    durationInFrames: Math.round(0.8 * fps),
  });

  const scrollY = interpolate(frame, [0, 0.9 * fps, 2.8 * fps, 4.8 * fps], [0, 0, -320, -560], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const vectorExplainPress = interpolate(frame, [5.0 * fps, 5.2 * fps, 5.45 * fps], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const vectorExplainOpen = interpolate(frame, [5.2 * fps, 5.85 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tutorPress = interpolate(frame, [6.25 * fps, 6.45 * fps, 6.7 * fps], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{backgroundColor: "#f9fafb", fontFamily: bodyFont, color: "#0f172a"}}>
      <div
        style={{
          position: "absolute",
          top: 52,
          left: 80,
          right: 80,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 20,
        }}
      >
        <div style={{display: "flex", alignItems: "center", gap: 16}}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              backgroundColor: "#000",
              color: "#fff",
              display: "grid",
              placeItems: "center",
              fontSize: 20,
            }}
          >
            ▲
          </div>
          <div style={{fontFamily: displayFont, fontWeight: 700, fontSize: 30, letterSpacing: 0.8}}>LearnerOS</div>
        </div>
        <div style={{display: "flex", alignItems: "center", gap: 24}}>
          <div style={{display: "flex", gap: 32, color: "#64748b", fontWeight: 600}}>
            <span>Home</span>
            <span style={{color: "#0f172a", fontWeight: 700}}>Insights</span>
            <span
              style={{
                transform: `scale(${interpolate(tutorPress, [0, 1], [1, 0.93])})`,
                color: interpolate(tutorPress, [0, 1], [0, 1]) > 0.2 ? "#0f172a" : "#64748b",
                textShadow: `0 0 ${interpolate(tutorPress, [0, 1], [0, 8])}px rgba(6,182,212,0.4)`,
              }}
            >
              LearnerOS Tutor
            </span>
          </div>
          <div
            style={{
              width: 1,
              alignSelf: "stretch",
              backgroundColor: "rgba(15,23,42,0.12)",
            }}
          />
          <div style={{textAlign: "right"}}>
            <div style={{fontWeight: 700, color: "#0f172a"}}>Srichandra</div>
            <div
              style={{
                fontWeight: 700,
                color: "#64748b",
                letterSpacing: 1.8,
                fontSize: 11,
                textTransform: "uppercase",
              }}
            >
              Sophomore
            </div>
          </div>
          <div
            style={{
              width: 46,
              height: 46,
              borderRadius: 999,
              border: "1px solid rgba(15,23,42,0.15)",
              padding: 2,
            }}
          >
            <Img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuA8MSw3Dg0Dj9tg-yOpepwwgdrLAGVv9z66cTVg-qEOhKYA8q4HwRoM4umd5BF2QA1IgQypisvCIoON00t_S15z3S60u9Zmhd3VmLcFtL6xXwKkLoI4vQ9YlW7pWk-wqL7Cz2U7diby1SAeI0FtJPtuLHNnX0NaAD0swp5I3agfAgpdnIMocKgNPrEzNiRiCuqi6PbFA-xG-hmF1ihmQy8IKbeIpwegdKWYUZpyQCKnHc1aIIS_urv4ThJNx7MPnR5lCCLkWyQPv8lz"
              style={{width: "100%", height: "100%", borderRadius: 999, objectFit: "cover"}}
            />
          </div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: 108,
          left: 0,
          right: 0,
          bottom: 0,
          borderTop: "1px solid #e2e8f0",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: 1240,
            margin: "0 auto",
            paddingTop: 32,
            transform: `translateY(${scrollY}px) translateY(${interpolate(sceneIn, [0, 1], [16, 0])}px)`,
            opacity: interpolate(sceneIn, [0, 1], [0, 1]),
          }}
        >
          <div style={{marginBottom: 26}}>
            <h1 style={{fontSize: 56, fontWeight: 700, lineHeight: 1.05, margin: 0}}>Learning Analysis</h1>
            <p style={{marginTop: 10, color: "#64748b", fontSize: 18}}>
              Concept-wise view of your active competencies, partial understandings, and misconceptions.
            </p>
          </div>

          <div style={{display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20, marginBottom: 30}}>
            {[
              ["#10b981", "✓", "COMPETENCIES", "3"],
              ["#f59e0b", "!", "PARTIAL UNDERSTANDINGS", "3"],
              ["#f43f5e", "○", "MISCONCEPTIONS", "4"],
            ].map(([color, icon, label, value]) => (
              <div key={String(label)} style={{backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: 16, padding: 20}}>
                <div style={{color, fontSize: 30, marginBottom: 12}}>{icon}</div>
                <div
                  style={{
                    fontSize: 11,
                    color: "#94a3b8",
                    textTransform: "uppercase",
                    letterSpacing: 1.6,
                    fontWeight: 700,
                    marginBottom: 4,
                  }}
                >
                  {label}
                </div>
                <div style={{fontSize: 62, lineHeight: 1, fontWeight: 700}}>{value}</div>
              </div>
            ))}
          </div>

          <div style={{display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18}}>
            <h2 style={{fontSize: 34, margin: 0, fontWeight: 700}}>Concept-wise Insights</h2>
            <span
              style={{
                borderRadius: 999,
                backgroundColor: "#dbeafe",
                color: "#2563eb",
                fontSize: 12,
                fontWeight: 700,
                padding: "6px 12px",
              }}
            >
              10 active insights
            </span>
          </div>

          <div style={{backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: 18, padding: 22, marginBottom: 18}}>
            <div style={{display: "flex", justifyContent: "space-between", marginBottom: 20}}>
              <div style={{fontSize: 30, fontWeight: 700}}>Work_Energy_Theorem</div>
              <div style={{fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.3, fontWeight: 700}}>3 Insights</div>
            </div>

            <div style={{display: "flex", flexDirection: "column", gap: 16}}>
              {[
                [
                  "#f59e0b",
                  "PARTIAL UNDERSTANDING",
                  "Derivation of the Principle of Conservation of Mechanical Energy",
                  "Student demonstrates clear understanding that the work-energy theorem describes work done by forces as equal to change in kinetic energy. However, student still fails to grasp the coupled nature of kinetic and potential energy changes in conservative systems.",
                ],
                [
                  "#f43f5e",
                  "MISCONCEPTION",
                  "Generalization to Three Dimensions",
                  "The student does not understand that the work-energy theorem universally relates change in kinetic energy to the dot product of net force and displacement, regardless of the angle between them.",
                ],
                [
                  "#10b981",
                  "COMPETENCY",
                  "Derivation for Constant Acceleration",
                  "The student can successfully derive the work-energy theorem for the case of constant acceleration in one dimension using kinematic equations.",
                ],
              ].map(([bar, kind, source, text], idx) => (
                <div key={String(idx)} style={{borderTop: idx === 0 ? "none" : "1px solid #e5e7eb", paddingTop: idx === 0 ? 0 : 14}}>
                  <div style={{position: "relative", border: "1px solid #e2e8f0", borderRadius: 12, backgroundColor: "#f8fafc", padding: 14}}>
                    <div
                      style={{
                        position: "absolute",
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: 5,
                        backgroundColor: String(bar),
                        borderTopLeftRadius: 12,
                        borderBottomLeftRadius: 12,
                      }}
                    />
                    <div style={{display: "flex", gap: 8, alignItems: "center"}}>
                      <span
                        style={{
                          fontSize: 10,
                          color: String(bar),
                          textTransform: "uppercase",
                          letterSpacing: 1.4,
                          fontWeight: 700,
                        }}
                      >
                        {kind}
                      </span>
                      <span
                        style={{
                          backgroundColor: "#e2e8f0",
                          color: "#64748b",
                          borderRadius: 999,
                          padding: "3px 7px",
                          fontSize: 10,
                          fontWeight: 700,
                          textTransform: "uppercase",
                        }}
                      >
                        Conceptual
                      </span>
                      <span style={{marginLeft: "auto", fontSize: 10, color: "#94a3b8", fontStyle: "italic"}}>{source}</span>
                    </div>
                    <div style={{marginTop: 10, fontSize: 15, color: "#475569", lineHeight: 1.6}}>{text}</div>
                    <div style={{marginTop: 12, display: "flex", gap: 8}}>
                      <button
                        style={{
                          borderRadius: 10,
                          border: "none",
                          backgroundColor: "#06b6d4",
                          color: "#fff",
                          padding: "8px 14px",
                          fontWeight: 700,
                          fontSize: 12,
                        }}
                      >
                        ⚡ Explain
                      </button>
                      <button
                        style={{
                          borderRadius: 10,
                          border: "none",
                          backgroundColor: "#3b82f6",
                          color: "#fff",
                          padding: "8px 14px",
                          fontWeight: 700,
                          fontSize: 12,
                        }}
                      >
                        🧪 Test
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: 18, padding: 22, marginBottom: 18}}>
            <div style={{display: "flex", justifyContent: "space-between", marginBottom: 16}}>
              <div style={{fontSize: 30, fontWeight: 700}}>Calculus</div>
              <div style={{fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.3, fontWeight: 700}}>1 Insight</div>
            </div>
            <div style={{position: "relative", border: "1px solid #e2e8f0", borderRadius: 12, backgroundColor: "#f8fafc", padding: 14}}>
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 5,
                  backgroundColor: "#f43f5e",
                  borderTopLeftRadius: 12,
                  borderBottomLeftRadius: 12,
                }}
              />
              <div style={{display: "flex", gap: 8, alignItems: "center"}}>
                <span
                  style={{
                    fontSize: 10,
                    color: "#f43f5e",
                    textTransform: "uppercase",
                    letterSpacing: 1.4,
                    fontWeight: 700,
                  }}
                >
                  MISCONCEPTION
                </span>
                <span
                  style={{
                    backgroundColor: "#e2e8f0",
                    color: "#64748b",
                    borderRadius: 999,
                    padding: "3px 7px",
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}
                >
                  Conceptual
                </span>
                <span style={{marginLeft: "auto", fontSize: 10, color: "#94a3b8", fontStyle: "italic"}}>
                  Derivation of the Principle of Conservation of Mechanical Energy
                </span>
              </div>
              <div style={{marginTop: 10, fontSize: 15, color: "#475569", lineHeight: 1.6}}>
                Student does not appreciate how differential and integral calculus extends physical laws
                from constant-force cases to variable-force quantities.
              </div>
              <div style={{marginTop: 12, display: "flex", gap: 8}}>
                <button
                  style={{
                    borderRadius: 10,
                    border: "none",
                    backgroundColor: "#06b6d4",
                    color: "#fff",
                    padding: "8px 14px",
                    fontWeight: 700,
                    fontSize: 12,
                    transform: `scale(${interpolate(vectorExplainPress, [0, 1], [1, 0.93])})`,
                    boxShadow: `0 0 0 ${interpolate(vectorExplainPress, [0, 1], [0, 6])}px rgba(6,182,212,${interpolate(
                      vectorExplainPress,
                      [0, 1],
                      [0, 0.2],
                    )})`,
                  }}
                >
                  ⚡ Explain
                </button>
                <button
                  style={{
                    borderRadius: 10,
                    border: "none",
                    backgroundColor: "#3b82f6",
                    color: "#fff",
                    padding: "8px 14px",
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  🧪 Test
                </button>
              </div>
              <div
                style={{
                  marginTop: 12,
                  backgroundColor: "#dff4f7",
                  border: "1px solid #a5e4ec",
                  borderRadius: 10,
                  padding: "0 12px",
                  overflow: "hidden",
                  maxHeight: interpolate(vectorExplainOpen, [0, 1], [0, 190]),
                  opacity: interpolate(vectorExplainOpen, [0, 1], [0, 1]),
                }}
              >
                <div style={{padding: "12px 0 12px 0", fontSize: 14, color: "#1f2937", lineHeight: 1.55}}>
                  Work is defined using the scalar (dot) product because it measures how much force acts
                  along displacement. The cross product gives a vector perpendicular to both inputs, so it
                  cannot represent scalar work.
                  <ul style={{margin: "8px 0 0 16px", padding: 0}}>
                    <li>Dot product returns a scalar quantity suitable for work.</li>
                    <li>Angle dependence is captured by cosθ in F·d.</li>
                    <li>Cross product is used for torque/area orientation, not work.</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div style={{backgroundColor: "#fff", border: "1px solid #e5e7eb", borderRadius: 18, padding: 22, marginBottom: 40}}>
            <div style={{display: "flex", justifyContent: "space-between", marginBottom: 16}}>
              <div style={{fontSize: 30, fontWeight: 700}}>Vectors</div>
              <div style={{fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.3, fontWeight: 700}}>1 Insight</div>
            </div>
            <div style={{position: "relative", border: "1px solid #e2e8f0", borderRadius: 12, backgroundColor: "#f8fafc", padding: 14}}>
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 5,
                  backgroundColor: "#f43f5e",
                  borderTopLeftRadius: 12,
                  borderBottomLeftRadius: 12,
                }}
              />
              <div style={{display: "flex", gap: 8, alignItems: "center"}}>
                <span
                  style={{
                    fontSize: 10,
                    color: "#f43f5e",
                    textTransform: "uppercase",
                    letterSpacing: 1.4,
                    fontWeight: 700,
                  }}
                >
                  MISCONCEPTION
                </span>
                <span
                  style={{
                    backgroundColor: "#e2e8f0",
                    color: "#64748b",
                    borderRadius: 999,
                    padding: "3px 7px",
                    fontSize: 10,
                    fontWeight: 700,
                    textTransform: "uppercase",
                  }}
                >
                  Conceptual
                </span>
                <span style={{marginLeft: "auto", fontSize: 10, color: "#94a3b8", fontStyle: "italic"}}>
                  Generalization to Three Dimensions
                </span>
              </div>
              <div style={{marginTop: 10, fontSize: 15, color: "#475569", lineHeight: 1.6}}>
                Student demonstrates confusion between vector operations, specifically not distinguishing
                scalar dot product from vector cross product for work calculations.
              </div>
              <div style={{marginTop: 12, display: "flex", gap: 8}}>
                <button
                  style={{
                    borderRadius: 10,
                    border: "none",
                    backgroundColor: "#06b6d4",
                    color: "#fff",
                    padding: "8px 14px",
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  ⚡ Explain
                </button>
                <button
                  style={{
                    borderRadius: 10,
                    border: "none",
                    backgroundColor: "#3b82f6",
                    color: "#fff",
                    padding: "8px 14px",
                    fontWeight: 700,
                    fontSize: 12,
                  }}
                >
                  🧪 Test
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
