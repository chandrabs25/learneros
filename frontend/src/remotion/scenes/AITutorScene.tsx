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

export const AITutorScene = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const inAnim = spring({
    frame,
    fps,
    config: {damping: 200},
    durationInFrames: Math.round(0.8 * fps),
  });

  const replyIn = interpolate(frame, [1.2 * fps, 2.2 * fps], [0, 1], {
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
            A
          </div>
          <div style={{fontFamily: displayFont, fontWeight: 700, fontSize: 30, letterSpacing: 0.8}}>LearnerOS</div>
        </div>
        <div style={{display: "flex", alignItems: "center", gap: 24}}>
          <div style={{display: "flex", gap: 32, color: "#64748b", fontWeight: 600}}>
            <span>Home</span>
            <span>Insights</span>
            <span style={{color: "#0f172a", fontWeight: 700}}>LearnerOS Tutor</span>
          </div>
          <div
            style={{
              width: 1,
              alignSelf: "stretch",
              backgroundColor: "rgba(15,23,42,0.12)",
            }}
          />
          <div style={{textAlign: "right"}}>
            <div style={{fontWeight: 700, color: "#0f172a"}}>Samanapalli Srichandra</div>
            <div
              style={{
                fontWeight: 700,
                color: "#64748b",
                letterSpacing: 1.8,
                fontSize: 11,
                textTransform: "uppercase",
              }}
            >
              Sign Out
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
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDdl1KtreC36hZx-99tI_W3yldSl4WD9Z06Sw8GjVTpQd8nuoJE0QHyJEUIrdK6KYhgFpp3cOKfxAYlfTDarijSNHRXMXRMMtRWR7Kf-6tByG9HaHLbHENyQrwnwlqWRWZzSdnOzIokl7vVjzUdU1tdIXvIbDeVSLYcQPreCUjrpFN-z_rahPGN6RT4gmN4WumbKZL6KrKJczzisDWXq-1Pz3LpJR4CGy_XLKXozu9Y8e4NVGGK8sz0_N4qLjjz-2JLatDFUjMqATR3"
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
          display: "flex",
          transform: `translateY(${interpolate(inAnim, [0, 1], [14, 0])}px)`,
          opacity: interpolate(inAnim, [0, 1], [0, 1]),
        }}
      >
        <aside style={{width: 320, borderRight: "1px solid #e2e8f0", backgroundColor: "#fff", padding: 16}}>
          <div style={{fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 700, marginBottom: 10}}>
            Matched Insights
          </div>

          {[
            ["COMPETENCY", "Work_Energy_Theorem", "Student demonstrates comprehensive understanding of the work-energy theorem: they grasp the foundational derivation showing that change in kinetic energy equals work done.", "#fb923c"],
            ["COMPETENCY", "Kinetic_Energy", "Student demonstrates solid understanding of kinetic energy relationships and correctly maps work to speed changes.", "#fb923c"],
            ["PARTIAL UNDERSTANDING", "Conservative_Force", "Student recognizes potential energy definitions but confuses conserved total energy with energy transfer.", "#f59e0b"],
          ].map(([tag, title, desc, tagColor], i) => (
            <div key={String(i)} style={{border: "1px solid #f3d1b6", borderRadius: 12, padding: 10, marginBottom: 10, backgroundColor: "#fffaf6"}}>
              <div style={{display: "flex", gap: 6, alignItems: "center"}}>
                <span style={{fontSize: 10, color: String(tagColor), fontWeight: 700, textTransform: "uppercase"}}>{tag}</span>
                <span style={{fontSize: 10, color: "#94a3b8"}}>conceptual</span>
              </div>
              <div style={{marginTop: 4, fontSize: 14, fontWeight: 700}}>{title}</div>
              <div style={{marginTop: 4, fontSize: 12, color: "#475569", lineHeight: 1.45}}>{desc}</div>
            </div>
          ))}

          <button
            style={{
              marginTop: 8,
              width: "100%",
              border: "2px dashed #cbd5e1",
              borderRadius: 10,
              padding: "10px 10px",
              backgroundColor: "#fff",
              color: "#334155",
              fontWeight: 700,
              fontSize: 12,
              textAlign: "left",
            }}
          >
            N + New Exploration
          </button>
        </aside>

        <section style={{flex: 1, display: "flex", flexDirection: "column", backgroundColor: "#f9fafb"}}>
          <div style={{flex: 1, padding: "16px 28px", display: "flex", flexDirection: "column", gap: 12, overflow: "hidden"}}>
            <div
              style={{
                alignSelf: "flex-start",
                backgroundColor: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: 20,
                borderTopLeftRadius: 8,
                padding: "14px 16px",
                maxWidth: 760,
                boxShadow: "0 6px 16px -12px rgba(15,23,42,0.28)",
                fontSize: 16,
                color: "#334155",
                lineHeight: 1.45,
              }}
            >
              How can I assist your learning today? I can explain any topic and personalize based on your
              active insights when relevant.
            </div>
            <div
              style={{
                alignSelf: "flex-end",
                backgroundColor: "#0f172a",
                borderRadius: 20,
                borderBottomRightRadius: 8,
                padding: "14px 16px",
                maxWidth: 760,
                color: "#fff",
                fontSize: 16,
                lineHeight: 1.4,
              }}
            >
              how does the work energy theorem relate to kinetic energy
            </div>

            <div
              style={{
                alignSelf: "flex-start",
                backgroundColor: "#fff",
                border: "1px solid #e2e8f0",
                borderRadius: 20,
                borderTopLeftRadius: 8,
                padding: "14px 16px",
                maxWidth: 760,
                boxShadow: "0 6px 16px -12px rgba(15,23,42,0.28)",
                fontSize: 14,
                color: "#1f2937",
                lineHeight: 1.55,
                opacity: interpolate(replyIn, [0, 1], [0, 1]),
                transform: `translateY(${interpolate(replyIn, [0, 1], [16, 0])}px)`,
              }}
            >
              <p style={{margin: 0}}>
                The <b>work-energy theorem</b> states that net work done on an object equals the change in
                kinetic energy.
              </p>
              <p style={{margin: "10px 0 0 0", fontFamily: "monospace", color: "#1d4ed8"}}>W_net = ΔK = K_f - K_i</p>
              <p style={{margin: "10px 0 0 0"}}>
                If net work is positive, kinetic energy increases (object speeds up). If net work is
                negative, kinetic energy decreases (object slows down). This relation remains valid for
                variable forces when integrated over displacement.
              </p>
              <ul style={{margin: "10px 0 0 18px", padding: 0}}>
                <li>Positive work → speed increases</li>
                <li>Negative work → speed decreases</li>
                <li>Zero net work → kinetic energy stays constant</li>
              </ul>
            </div>
          </div>

          <div style={{padding: "14px 28px 16px 28px"}}>
            <div
              style={{
                position: "relative",
                borderRadius: 999,
                backgroundColor: "#fff",
                border: "1px solid #e2e8f0",
                boxShadow: "0 12px 20px -16px rgba(15,23,42,0.35)",
              }}
            >
              <input
                value=""
                readOnly
                placeholder="Ask me anything about any subject..."
                style={{
                  width: "100%",
                  border: "none",
                  background: "transparent",
                  outline: "none",
                  padding: "18px 62px 18px 24px",
                  color: "#334155",
                  fontSize: 15,
                }}
              />
              <button
                style={{
                  position: "absolute",
                  right: 8,
                  top: 8,
                  width: 42,
                  height: 42,
                  borderRadius: 999,
                  border: "none",
                  backgroundColor: "#f48c71",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: 20,
                }}
              >
                ↑
              </button>
            </div>
          </div>
        </section>

        <aside style={{width: 320, borderLeft: "1px solid #e2e8f0", backgroundColor: "#fff", padding: 16}}>
          <div style={{fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 700, marginBottom: 10}}>
            Matched Concepts
          </div>
          {[
            ["Work_Energy_Theorem", "COMPETENCY", "2 matches"],
            ["Kinetic_Energy", "COMPETENCY", "1 match"],
            ["Conservative_Force", "PARTIAL UNDERSTANDING", "1 match"],
            ["Work", "COMPETENCY", "1 match"],
          ].map(([name, tag, count]) => (
            <div key={String(name)} style={{border: "1px solid #e2e8f0", borderRadius: 12, padding: 10, marginBottom: 10, backgroundColor: "#f8fafc"}}>
              <div style={{fontSize: 14, fontWeight: 700}}>{name}</div>
              <div style={{marginTop: 3, fontSize: 12, color: "#64748b"}}>
                <b>{tag}</b> {count}
              </div>
            </div>
          ))}
        </aside>
      </div>
    </AbsoluteFill>
  );
};
