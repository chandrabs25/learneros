import {loadFont as loadInter} from "@remotion/google-fonts/Inter";
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

const {fontFamily: displayFont} = loadInter("normal", {
  weights: ["500", "600", "700", "800"],
  subsets: ["latin"],
});
const {fontFamily: bodyFont} = loadInter("normal", {
  weights: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
});

const chapters = [
  {id: "03", title: "Motion in a Plane", sections: "12 Sections", exercises: "22 Exercises"},
  {id: "04", title: "Laws of Motion", sections: "14 Sections", exercises: "23 Exercises"},
  {id: "05", title: "Work, Energy and Power", sections: "13 Sections", exercises: "23 Exercises", active: true},
  {id: "06", title: "Systems of Particles and Rotational Motion", sections: "16 Sections", exercises: "17 Exercises"},
  {id: "07", title: "Gravitation", sections: "13 Sections", exercises: "21 Exercises"},
  {id: "08", title: "Mechanical Properties of Solids", sections: "-- Sections", exercises: "16 Exercises"},
];

export const PhysicsChapterScene = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const sceneIn = spring({
    frame,
    fps,
    config: {damping: 200},
    durationInFrames: Math.round(0.8 * fps),
  });
  const explorePress = interpolate(frame, [2.15 * fps, 2.35 * fps, 2.6 * fps], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{backgroundColor: "#F8FAFC", fontFamily: bodyFont, color: "#0f172a"}}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 116,
          backgroundColor: "#ffffff",
          borderBottom: "1px solid #e2e8f0",
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 52,
          left: 80,
          right: 80,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
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
          <div style={{fontFamily: displayFont, fontWeight: 700, fontSize: 30, letterSpacing: 0.2}}>LearnerOS</div>
        </div>
        <div style={{display: "flex", alignItems: "center", gap: 24}}>
          <div style={{display: "flex", gap: 32, color: "#64748b", fontWeight: 600, fontSize: 13}}>
            <span style={{color: "#0f172a"}}>Home</span>
            <span>Insights</span>
            <span>LearnerOS Tutor</span>
          </div>
          <div
            style={{
              width: 1,
              alignSelf: "stretch",
              backgroundColor: "rgba(15,23,42,0.12)",
            }}
          />
          <div style={{textAlign: "right"}}>
            <div style={{fontWeight: 700, color: "#0f172a", fontSize: 13}}>Srichandra</div>
            <div
              style={{
                fontWeight: 700,
                color: "#64748b",
                letterSpacing: 1.8,
                fontSize: 10,
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
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCmHJzxpvyBd3pMTCmyDBMJgdGds4mzwy9uRYD65rEE5IUKEzM7culPVBI591thGDm8uyEWiJ6aBFHWs6Q6YiB4SBp-z0WVumlT8BvyTDKttbPulAz1_VjMF4wM52BQoY6fFJCQYt3wubCo68GlTL-pWSkdLTXAg9kesGaN0yYJUgaRvxYfIQzAJ5LpwNr2xh172ihkAfjykOkoaXv9QTm1qAReokLlkVyayg5C_o7sYoGfVqbHa9MJKZI8Pj68LncdBvMECeIejXrK"
              style={{
                width: "100%",
                height: "100%",
                borderRadius: 999,
                objectFit: "cover",
                filter: "grayscale(100%)",
              }}
            />
          </div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 56,
          top: 136,
          width: 420,
          bottom: 0,
          backgroundColor: "#f1f5f9",
          borderRight: "1px solid #e2e8f0",
          padding: "28px 20px 20px 20px",
          transform: `translateX(${interpolate(sceneIn, [0, 1], [-20, 0])}px)`,
          opacity: interpolate(sceneIn, [0, 1], [0, 1]),
        }}
      >
        <div style={{display: "flex", alignItems: "center", gap: 8, color: "#64748b", fontSize: 13, fontWeight: 700}}>
          <span>←</span>
          <span style={{textTransform: "uppercase", letterSpacing: 1.1}}>Back to Subjects</span>
        </div>

        <div style={{marginTop: 22, display: "flex", justifyContent: "space-between", alignItems: "end"}}>
          <div>
            <div style={{fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.4, fontWeight: 800}}>
              Subject
            </div>
            <div style={{fontFamily: displayFont, fontSize: 42, fontWeight: 700, marginTop: 6}}>Physics</div>
          </div>
          <div style={{fontSize: 12, color: "#64748b", fontWeight: 600}}>14 Chapters</div>
        </div>

        <div style={{marginTop: 18, display: "flex", flexDirection: "column", gap: 10}}>
          {chapters.map((chapter, i) => (
            <div
              key={chapter.id}
              style={{
                borderRadius: 10,
                backgroundColor: "#f8fafc",
                border: chapter.active ? "1px solid #cbd5e1" : "1px solid #dbe3ed",
                borderLeft: chapter.active ? "4px solid #0f172a" : "1px solid #dbe3ed",
                padding: "12px 14px",
                transform: `translateY(${interpolate(sceneIn, [0, 1], [8 + i * 1.2, 0])}px)`,
                opacity: interpolate(sceneIn, [0, 1], [0.4, 1]),
              }}
            >
              <div style={{fontSize: 10, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 1.3, fontWeight: 800}}>
                Chapter {chapter.id}
              </div>
              <div
                style={{
                  marginTop: 4,
                  color: chapter.active ? "#0f172a" : "#475569",
                  fontWeight: 700,
                  fontSize: 16,
                  lineHeight: 1.2,
                }}
              >
                {chapter.title}
              </div>
              <div style={{display: "flex", gap: 14, marginTop: 8}}>
                <span style={{fontSize: 10, color: "#64748b", textTransform: "uppercase", fontWeight: 600}}>
                  {chapter.sections}
                </span>
                <span style={{fontSize: 10, color: "#64748b", textTransform: "uppercase", fontWeight: 600}}>
                  {chapter.exercises}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          left: 476,
          right: 0,
          top: 136,
          bottom: 0,
          backgroundColor: "#f8fafc",
          overflow: "hidden",
          transform: `translateX(${interpolate(sceneIn, [0, 1], [20, 0])}px)`,
          opacity: interpolate(sceneIn, [0, 1], [0, 1]),
        }}
      >
        <div
          style={{
            height: 430,
            background: "linear-gradient(90deg, #DCE3F6 0%, #E3EDEB 100%)",
            padding: "34px 40px",
            display: "flex",
            alignItems: "start",
          }}
        >
          <div style={{display: "flex", gap: 8}}>
            <span
              style={{
                backgroundColor: "#000",
                color: "#fff",
                fontSize: 11,
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: 1.1,
                borderRadius: 999,
                padding: "6px 12px",
              }}
            >
              Grade 11
            </span>
            <span
              style={{
                backgroundColor: "#fff",
                color: "#334155",
                fontSize: 11,
                fontWeight: 800,
                textTransform: "uppercase",
                letterSpacing: 1.1,
                borderRadius: 999,
                padding: "6px 12px",
                border: "1px solid #e2e8f0",
              }}
            >
              Physics
            </span>
          </div>
        </div>

        <div style={{padding: "40px 40px"}}>
          <div style={{fontFamily: displayFont, fontSize: 64, lineHeight: 1.03, fontWeight: 700}}>Work, Energy and Power</div>
          <div style={{marginTop: 8, color: "#64748b", fontWeight: 500, fontSize: 13}}>Chapter 5 • Physics</div>

          <div
            style={{
              marginTop: 24,
              borderRadius: 18,
              backgroundColor: "#fff",
              border: "1px solid #e2e8f0",
              padding: 26,
              display: "flex",
              gap: 28,
            }}
          >
            <div style={{flex: 1}}>
              <div
                style={{
                  fontSize: 11,
                  color: "#94a3b8",
                  textTransform: "uppercase",
                  letterSpacing: 2,
                  fontWeight: 800,
                  marginBottom: 12,
                }}
              >
                Chapter Overview
              </div>
              <div style={{fontSize: 16, color: "#111827", lineHeight: 1.7, maxWidth: 620}}>
                This chapter introduces the fundamental concepts of work, energy, and power in physics. It
                begins by defining the scalar product (dot product) of vectors, a crucial mathematical tool for
                calculating work. Work is then defined as the force applied over a displacement and introduces
                the Work-Energy Theorem.
              </div>
            </div>

            <div style={{width: 290}}>
              <div style={{display: "flex", flexDirection: "column", gap: 14, marginBottom: 24}}>
                {[
                  ["Sections", "13"],
                  ["Exercises", "23"],
                  ["Concepts", "11"],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      paddingBottom: 10,
                      borderBottom: "1px solid #e2e8f0",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 11,
                        color: "#94a3b8",
                        textTransform: "uppercase",
                        letterSpacing: 1.2,
                        fontWeight: 800,
                      }}
                    >
                      {label}
                    </span>
                    <span style={{fontSize: 14, fontFamily: displayFont, fontWeight: 700}}>{value}</span>
                  </div>
                ))}
              </div>

              <div style={{display: "flex", flexDirection: "column", gap: 10}}>
                <button
                  style={{
                    borderRadius: 12,
                    backgroundColor: "#000",
                    color: "#fff",
                    border: "none",
                    padding: "14px 16px",
                    fontWeight: 700,
                    fontSize: 15,
                    lineHeight: 1.2,
                    transform: `scale(${interpolate(explorePress, [0, 1], [1, 0.95])})`,
                    boxShadow: `0 0 0 ${interpolate(explorePress, [0, 1], [0, 6])}px rgba(16,185,129,${interpolate(
                      explorePress,
                      [0, 1],
                      [0, 0.22],
                    )})`,
                  }}
                >
                  ▶ Explore Chapter
                </button>
                <button
                  style={{
                    borderRadius: 12,
                    backgroundColor: "#000",
                    color: "#fff",
                    border: "none",
                    padding: "14px 16px",
                    fontWeight: 700,
                    fontSize: 15,
                    lineHeight: 1.2,
                  }}
                >
                  ⛯ Knowledge Graph
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
