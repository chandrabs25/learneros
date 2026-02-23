import {loadFont as loadInter} from "@remotion/google-fonts/Inter";
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

const {fontFamily} = loadInter("normal", {
  weights: ["300", "400", "500", "600", "700", "800"],
  subsets: ["latin"],
});

const chapterNav = [
  "5.1. Introduction",
  "5.1.1. The Scalar Product",
  "5.2. Notions of Work and Kinetic Energy: The Work-Energy Theorem",
  "5.3. Work",
  "5.4. KINETIC ENERGY",
  "5.5. WORK DONE BY A VARIABLE FORCE",
  "5.7. THE CONCEPT OF POTENTIAL ENERGY",
  "5.8. THE CONSERVATION OF MECHANICAL ENERGY",
  "5.9. THE POTENTIAL ENERGY OF A SPRING",
];

const insights = [
  {
    tag: "Misconception",
    color: "#dc2626",
    bg: "#fee2e2",
    title: "Energy Conservation",
    body: "Student treats conservation of mechanical energy as an increase in total energy, instead of constant total energy with conversion between kinetic and potential forms.",
  },
  {
    tag: "Partial Understanding",
    color: "#d97706",
    bg: "#fef3c7",
    title: "Work_Energy_Theorem",
    body: "Student can apply the work-energy theorem in simple constant-force cases, but struggles to connect it consistently with changes in potential energy.",
  },
  {
    tag: "Competency",
    color: "#15803d",
    bg: "#dcfce7",
    title: "Kinetic_Energy",
    body: "Student correctly relates kinetic energy to speed and recognizes how equal work produces specific speed relationships.",
  },
];

export const SubsectionViewerScene = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const inAnim = spring({
    frame,
    fps,
    config: {damping: 200},
    durationInFrames: Math.round(0.8 * fps),
  });

  return (
    <AbsoluteFill style={{backgroundColor: "#f8fafc", fontFamily, color: "#0f172a"}}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 78,
          backgroundColor: "#ffffff",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 30px",
        }}
      >
        <div style={{display: "flex", alignItems: "center", gap: 14}}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              backgroundColor: "#000",
              color: "#fff",
              display: "grid",
              placeItems: "center",
              fontWeight: 700,
              fontSize: 22,
            }}
          >
            Δ
          </div>
          <div style={{fontWeight: 700, fontSize: 42}}>LearnerOS</div>
        </div>

        <div style={{display: "flex", alignItems: "center", gap: 18}}>
          <div style={{textAlign: "right", fontSize: 12, textTransform: "uppercase", letterSpacing: 1.2}}>
            <div style={{fontWeight: 800, color: "#0f172a"}}>SAMANAPALLI SRICHANDRA</div>
            <div style={{color: "#64748b", marginTop: 2}}>SIGN OUT</div>
          </div>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 999,
              overflow: "hidden",
              backgroundColor: "#e2e8f0",
            }}
          >
            <Img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDBbfUHkjieC9B2Q24dNp-9AZZMZ9GJg_k8tnukn16gg8IkH_LK9EfaQbSc1mKqI3DpF83fihNQwcIPiuE_ysN0qxMwvRCXxf1SVA_Wt4eTRBXOA_PpimXKbp8lvIQFk89wTTQWooFnNSPv31iC5JV132I80QgZDTDHZXDVlal0SEv69sQNNzmN4h4TUyW3Xh0rTQNDygykFApFJm1ol9swBllMgf5rGUztg-9Ohyt3jl4fTvuiNetjbEhiM-iso3xEaljKruE0nLQy"
              style={{width: "100%", height: "100%", objectFit: "cover"}}
            />
          </div>
        </div>
      </div>

      <div style={{position: "absolute", top: 78, left: 0, right: 0, bottom: 92, display: "flex"}}>
        <aside
          style={{
            width: 345,
            borderRight: "1px solid #e2e8f0",
            backgroundColor: "#f8fafc",
            padding: 22,
            transform: `translateX(${interpolate(inAnim, [0, 1], [-16, 0])}px)`,
            opacity: interpolate(inAnim, [0, 1], [0, 1]),
          }}
        >
          <div style={{fontSize: 16, color: "#64748b", textTransform: "uppercase", letterSpacing: 2, fontWeight: 700}}>
            Chapter 5
          </div>

          <div style={{marginTop: 18, display: "flex", flexDirection: "column", gap: 10}}>
            {chapterNav.slice(0, 7).map((item) => (
              <div key={item} style={{fontSize: 13, color: "#64748b", lineHeight: 1.35}}>
                {item}
              </div>
            ))}
            <div
              style={{
                marginTop: 4,
                backgroundColor: "#ffffff",
                border: "1px solid #e2e8f0",
                borderLeft: "4px solid #10b981",
                borderRadius: 10,
                padding: 12,
              }}
            >
              <div style={{fontSize: 11, color: "#10b981", fontWeight: 800, textTransform: "uppercase"}}>Active</div>
              <div style={{marginTop: 5, fontSize: 13, fontWeight: 700, lineHeight: 1.3}}>
                5.8. THE CONSERVATION OF MECHANICAL ENERGY
              </div>
              <div style={{marginTop: 10, borderLeft: "1px solid #cbd5e1", paddingLeft: 10, display: "flex", flexDirection: "column", gap: 10}}>
                <div style={{fontSize: 12, fontWeight: 700, lineHeight: 1.35}}>• Derivation for Constant Acceleration</div>
                <div style={{fontSize: 12, color: "#64748b", lineHeight: 1.3}}>Generalization to Three Dimensions</div>
                <div style={{fontSize: 12, color: "#64748b", lineHeight: 1.3}}>Definitions and the Work-Energy Theorem</div>
                <div style={{fontSize: 12, color: "#64748b", lineHeight: 1.3}}>Worked Example: Raindrop and Resistive Force</div>
              </div>
            </div>
            {chapterNav.slice(7).map((item) => (
              <div key={item} style={{fontSize: 13, color: "#64748b", lineHeight: 1.35}}>
                {item}
              </div>
            ))}
          </div>

          <div style={{position: "absolute", left: 22, right: 22, bottom: 20, borderTop: "1px solid #e2e8f0", paddingTop: 14}}>
            <div style={{display: "flex", gap: 10, alignItems: "center"}}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 999,
                  backgroundColor: "#111827",
                  color: "#fff",
                  display: "grid",
                  placeItems: "center",
                  fontWeight: 700,
                }}
              >
                N
              </div>
              <div style={{flex: 1}}>
                <div style={{fontSize: 11, color: "#10b981", fontWeight: 800, textTransform: "uppercase", letterSpacing: 1.1}}>
                  Section Progress
                </div>
                <div style={{height: 6, borderRadius: 99, marginTop: 4, backgroundColor: "#e2e8f0"}}>
                  <div style={{width: "25%", height: "100%", backgroundColor: "#10b981", borderRadius: 99}} />
                </div>
                <div style={{fontSize: 11, color: "#94a3b8", textAlign: "right", marginTop: 3}}>1 of 4</div>
              </div>
            </div>
          </div>
        </aside>

        <main style={{flex: 1, position: "relative", backgroundColor: "#f8fafc"}}>
          <div style={{position: "absolute", left: 40, right: 432, top: 34, bottom: 0}}>
            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
              <div style={{display: "flex", alignItems: "center", gap: 10, fontSize: 15, color: "#94a3b8"}}>
                <span style={{color: "#3b82f6"}}>Hub</span>›<span style={{color: "#3b82f6"}}>Physics</span>›
                <span style={{color: "#3b82f6"}}>Chapter 5</span>›<span>Section 5.2</span>
              </div>
              <button
                style={{
                  border: "1px solid #e2e8f0",
                  borderRadius: 999,
                  padding: "8px 14px",
                  backgroundColor: "#fff",
                  fontSize: 12,
                  textTransform: "uppercase",
                  fontWeight: 700,
                  color: "#334155",
                }}
              >
                ← Back to Topics
              </button>
            </div>

            <div style={{marginTop: 26}}>
              <div
                style={{
                  display: "inline-flex",
                  gap: 8,
                  alignItems: "center",
                  fontSize: 12,
                  fontWeight: 800,
                  textTransform: "uppercase",
                  color: "#7c3aed",
                  backgroundColor: "#ede9fe",
                  borderRadius: 999,
                  padding: "7px 14px",
                  letterSpacing: 1.1,
                }}
              >
                ✦ Derivation
              </div>
              <div style={{marginTop: 18, fontSize: 62, lineHeight: 1.07, fontWeight: 800}}>Derivation for Constant Acceleration</div>
              <div style={{marginTop: 10, color: "#64748b", fontSize: 17, fontWeight: 500}}>Subsection 1 of 4</div>
            </div>

            <div style={{marginTop: 36, fontSize: 17, color: "#111827", lineHeight: 1.8, maxWidth: 890}}>
              For rectilinear motion under constant acceleration <i>a</i>, the kinematic equation is
              <span style={{fontFamily: "monospace", fontSize: 18}}> v² − u² = 2as</span>, where <i>u</i> and <i>v</i> are initial and
              final speeds and <i>s</i> is the distance. Multiplying by <i>m/2</i>, we get
              <span style={{fontFamily: "monospace", fontSize: 18}}> 1/2mv² − 1/2mu² = mas = Fs</span>. This shows that change
              in a quantity related to speed is equal to the product of force and displacement.
            </div>
          </div>

          <div
            style={{
              position: "absolute",
              right: 22,
              top: 18,
              bottom: 110,
              width: 398,
              backgroundColor: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: 20,
              boxShadow: "0 18px 30px -24px rgba(15,23,42,0.35)",
              display: "flex",
              flexDirection: "column",
            }}
          >
            <div style={{padding: 18, borderBottom: "1px solid #f1f5f9", display: "flex", justifyContent: "space-between", gap: 10}}>
              <div>
                <div style={{fontSize: 12, color: "#14b8a6", textTransform: "uppercase", letterSpacing: 1.3, fontWeight: 800}}>
                  Active Insights
                </div>
                <div style={{marginTop: 6, fontSize: 16, fontWeight: 700, lineHeight: 1.3}}>Derivation for Constant Acceleration</div>
              </div>
              <button style={{border: "none", background: "none", fontSize: 20, color: "#334155"}}>×</button>
            </div>
            <div style={{padding: 12, display: "flex", flexDirection: "column", gap: 10, overflow: "hidden"}}>
              {insights.map((item) => (
                <div key={item.title} style={{backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 14, padding: 12}}>
                  <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
                    <span
                      style={{
                        fontSize: 10,
                        fontWeight: 800,
                        color: item.color,
                        backgroundColor: item.bg,
                        padding: "4px 8px",
                        borderRadius: 999,
                        textTransform: "uppercase",
                        letterSpacing: 1,
                      }}
                    >
                      {item.tag}
                    </span>
                    <span style={{fontSize: 10, color: "#94a3b8"}}>conceptual</span>
                  </div>
                  <div style={{marginTop: 10, fontSize: 14, fontWeight: 700}}>{item.title}</div>
                  <div style={{marginTop: 6, fontSize: 12, color: "#475569", lineHeight: 1.55}}>{item.body}</div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>

      <footer
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 92,
          backgroundColor: "#ffffff",
          borderTop: "1px solid #e2e8f0",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "0 22px",
        }}
      >
        <div style={{display: "flex", gap: 10}}>
          {[
            ["#2563eb", "Concepts (2)", "💡"],
            ["#f59e0b", "Test Me", "📝"],
            ["#6366f1", "MCQ", "☑"],
            ["#facc15", "Chapter End Exercises (5)", "✎", "#111827"],
            ["#fb923c", "LearnerOS Tutor", "🤖"],
          ].map(([bg, label, icon, color]) => (
            <button
              key={String(label)}
              style={{
                borderRadius: 12,
                padding: "11px 16px",
                border: "none",
                backgroundColor: bg,
                color: color ?? "#fff",
                fontWeight: 700,
                fontSize: 14,
                display: "flex",
                gap: 8,
                alignItems: "center",
              }}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </div>

        <div style={{display: "flex", alignItems: "center", gap: 16}}>
          <div style={{display: "flex", alignItems: "center", gap: 10}}>
            <div style={{width: 78, height: 7, borderRadius: 99, backgroundColor: "#e2e8f0"}}>
              <div style={{width: "25%", height: "100%", backgroundColor: "#10b981", borderRadius: 99}} />
            </div>
            <span style={{fontSize: 13, textTransform: "uppercase", color: "#64748b", fontWeight: 700}}>1 of 4</span>
          </div>
          <button
            style={{
              borderRadius: 10,
              border: "1px solid #e2e8f0",
              backgroundColor: "#f8fafc",
              color: "#94a3b8",
              padding: "11px 20px",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            Previous
          </button>
          <button
            style={{
              borderRadius: 10,
              border: "none",
              backgroundColor: "#10b981",
              color: "#fff",
              padding: "11px 24px",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            Next →
          </button>
        </div>
      </footer>
    </AbsoluteFill>
  );
};
