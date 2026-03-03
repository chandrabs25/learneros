import { loadFont as loadOutfit } from "@remotion/google-fonts/Outfit";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";

const { fontFamily: displayFont } = loadSpaceGrotesk("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});
const { fontFamily: bodyFont } = loadOutfit("normal", {
  weights: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
});

const cards = [
  { level: "09", label: "Freshman", status: "Level 09", locked: false },
  {
    level: "10",
    label: "Sophomore",
    status: "Current Level",
    progress: "78% PROGRESS COMPLETED",
    locked: false,
  },
  { level: "11", label: "Junior", status: "Level 11", locked: true },
  { level: "12", label: "Senior", status: "Level 12", locked: true },
];

export const OpeningHubScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const intro = spring({
    frame,
    fps,
    config: { damping: 200 },
    durationInFrames: Math.round(1.2 * fps),
  });

  const swipeOffset = interpolate(
    frame,
    [0, 1.1 * fps, 1.45 * fps, 8 * fps],
    [0, -446, -446, -446],
    {
      easing: Easing.inOut(Easing.cubic),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  const cardWidth = 390;
  const cardGap = 56;
  const centerX = 1280;
  const centerCardIndex = 1;
  const currentIndex = Math.max(
    0,
    Math.min(
      cards.length - 1,
      Math.round(centerCardIndex - swipeOffset / (cardWidth + cardGap)),
    ),
  );
  const selectedIndex = frame >= 2.2 * fps ? 2 : currentIndex;
  const pressProgress = interpolate(frame, [1.95 * fps, 2.1 * fps, 2.2 * fps], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  const swipeFade = interpolate(frame, [2.2 * fps, 2.5 * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

  const cardExpandProgress = interpolate(frame, [2.2 * fps, 3.2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: `rgba(252, 252, 249, ${swipeFade})`,
        color: "#0f172a",
        fontFamily: bodyFont,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 85% -5%, rgba(100,116,139,0.10), transparent 38%), radial-gradient(circle at 6% 96%, rgba(20,184,166,0.10), transparent 35%)",
          opacity: swipeFade,
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
          opacity: swipeFade,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <Img src={staticFile("learneros-logo.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
          <div
            style={{
              fontFamily: displayFont,
              fontWeight: 700,
              fontSize: 30,
              letterSpacing: 0.8,
            }}
          >
            LearnerOS
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <div style={{ display: "flex", gap: 32, color: "#64748b", fontWeight: 600 }}>
            <span style={{ color: "#0f172a" }}>Home</span>
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
          <div style={{ textAlign: "right" }}>
            <div style={{ fontWeight: 700, color: "#0f172a" }}>Srichandra</div>
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
          top: 226,
          left: 104,
          transform: `translateY(${interpolate(intro, [0, 1], [34, 0])}px)`,
          opacity: interpolate(intro, [0, 1], [0, 1]) * swipeFade,
        }}
      >
        <h1
          style={{
            margin: 0,
            fontFamily: displayFont,
            fontWeight: 700,
            fontSize: 90,
            lineHeight: 1.05,
            letterSpacing: -2,
          }}
        >
          Where are we
          <br />
          <span style={{ color: "#64748b" }}>starting today?</span>
        </h1>
        <p
          style={{
            marginTop: 30,
            borderLeft: "4px solid #14b8a6",
            paddingLeft: 18,
            maxWidth: 540,
            color: "#64748b",
            fontSize: 31,
            lineHeight: 1.28,
            fontWeight: 500,
          }}
        >
          Select your grade level to dive back into your academic journey.
        </p>
      </div>

      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
          clipPath: `inset(0 0 0 ${interpolate(cardExpandProgress, [0, 1], [50, 0])}%)`,
        }}
      >
        {cards.map((card, i) => {
          const x =
            centerX -
            cardWidth / 2 +
            (i - centerCardIndex) * (cardWidth + cardGap) +
            swipeOffset;
          const distanceFromCenter = Math.abs(
            (i - centerCardIndex) * (cardWidth + cardGap) + swipeOffset,
          );
          const normalizedDistance = interpolate(
            distanceFromCenter,
            [0, cardWidth + cardGap],
            [0, 1],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            },
          );
          const cardScale = interpolate(normalizedDistance, [0, 1], [1.05, 0.93]);
          const isActive = selectedIndex === i;

          const isGrade11 = i === 2;
          const targetCardOpacity = isGrade11 ? 1 : swipeFade; // Grade 11 stays solid, others fade aggressively
          const baseCardOpacity = interpolate(normalizedDistance, [0, 1], [1, 0.62]);
          const finalCardOpacity = frame >= 2.2 * fps ? (isActive ? 1 : swipeFade) : baseCardOpacity;

          const currentX = isGrade11 ? interpolate(cardExpandProgress, [0, 1], [x, 0]) : x;
          const currentTop = isGrade11 ? interpolate(cardExpandProgress, [0, 1], [220, 0]) : 220;
          const currentWidth = isGrade11 ? interpolate(cardExpandProgress, [0, 1], [cardWidth, 1920]) : cardWidth;
          const currentHeight = isGrade11 ? interpolate(cardExpandProgress, [0, 1], [640, 1080]) : 640;
          const currentScale = isGrade11 ? interpolate(cardExpandProgress, [0, 1], [cardScale, 1]) : cardScale;
          const currentBorderRadius = isGrade11 ? interpolate(cardExpandProgress, [0, 1], [32, 36]) : 32;
          const currentZIndex = isGrade11 && cardExpandProgress > 0 ? 50 : 1;

          const contentOpacity = isGrade11 ? interpolate(cardExpandProgress, [0, 0.4], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) : 1;

          return (
            <div
              key={card.level}
              style={{
                position: "absolute",
                top: currentTop,
                left: currentX,
                width: currentWidth,
                height: currentHeight,
                borderRadius: currentBorderRadius,
                overflow: "hidden",
                border: "1px solid rgba(15,23,42,0.06)",
                backgroundColor: isActive ? "#ffffff" : "#f1f5f9",
                boxShadow: isActive
                  ? "0 30px 60px -22px rgba(15,23,42,0.26)"
                  : "0 14px 30px -20px rgba(15,23,42,0.22)",
                transform: `scale(${currentScale})`,
                opacity: finalCardOpacity,
                zIndex: currentZIndex,
                filter: (isActive || i === 1 ? "grayscale(0%)" : `grayscale(${normalizedDistance})`),
              }}
            >
              <div style={{ position: "absolute", inset: 0, opacity: contentOpacity }}>
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background:
                      "linear-gradient(125deg, rgba(15,23,42,0.045), rgba(255,255,255,0.02))",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: 28,
                    left: 28,
                    right: 28,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{
                      borderRadius: 999,
                      border:
                        isActive
                          ? "none"
                          : "1px solid rgba(15,23,42,0.12)",
                      backgroundColor: isActive ? "#000" : "transparent",
                      color: isActive ? "#fff" : "#64748b",
                      padding: isActive ? "6px 14px" : "6px 12px",
                      fontSize: 11,
                      letterSpacing: 1.8,
                      textTransform: "uppercase",
                      fontWeight: 700,
                    }}
                  >
                    {card.status}
                  </span>
                  {isActive ? (
                    <div style={{ display: "flex", gap: 6 }}>
                      <span
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: 999,
                          backgroundColor: "#14b8a6",
                        }}
                      />
                      <span
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: 999,
                          backgroundColor: "rgba(15,23,42,0.12)",
                        }}
                      />
                      <span
                        style={{
                          width: 7,
                          height: 7,
                          borderRadius: 999,
                          backgroundColor: "rgba(15,23,42,0.12)",
                        }}
                      />
                    </div>
                  ) : null}
                </div>
                <div
                  style={{
                    position: "absolute",
                    left: 28,
                    right: 28,
                    bottom: 28,
                  }}
                >
                  <div
                    style={{
                      fontFamily: displayFont,
                      color: card.level === "10" ? "#000" : "rgba(100,116,139,0.6)",
                      fontWeight: 700,
                      fontSize: 210,
                      lineHeight: 0.72,
                      letterSpacing: -5,
                    }}
                  >
                    {card.level}
                  </div>
                  <div
                    style={{
                      marginTop: 34,
                      borderTop: "1px solid rgba(15,23,42,0.07)",
                      paddingTop: 24,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div
                        style={{
                          fontFamily: displayFont,
                          color: "#0f172a",
                          fontWeight: 700,
                          fontSize: 35,
                          textTransform: "uppercase",
                          letterSpacing: -0.5,
                        }}
                      >
                        {card.label}
                      </div>
                      {card.progress ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            marginTop: 10,
                            gap: 8,
                            color: "#64748b",
                            fontSize: 12,
                            fontWeight: 700,
                            letterSpacing: 1.1,
                          }}
                        >
                          <span
                            style={{
                              width: 8,
                              height: 8,
                              borderRadius: 999,
                              backgroundColor: "#14b8a6",
                            }}
                          />
                          {card.progress}
                        </div>
                      ) : null}
                      {card.locked ? (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            marginTop: 10,
                            color: "#64748b",
                            fontSize: 12,
                            textTransform: "uppercase",
                            letterSpacing: 1.3,
                            fontWeight: 700,
                          }}
                        >
                          <span>Locked</span>
                        </div>
                      ) : null}
                    </div>
                    <div
                      style={{
                        width: isActive ? 54 : 42,
                        height: isActive ? 54 : 42,
                        borderRadius: 999,
                        backgroundColor: isActive ? "#14b8a6" : "transparent",
                        border:
                          isActive
                            ? "none"
                            : "1px solid rgba(15,23,42,0.08)",
                        display: "grid",
                        placeItems: "center",
                        color: isActive ? "#fff" : "#64748b",
                        fontSize: 20,
                        fontWeight: 700,
                        transform:
                          isActive && i === 2
                            ? `scale(${interpolate(pressProgress, [0, 1], [1, 0.88])})`
                            : "scale(1)",
                        boxShadow:
                          isActive && i === 2
                            ? `0 0 0 ${interpolate(pressProgress, [0, 1], [0, 10])}px rgba(20,184,166,${interpolate(pressProgress, [0, 1], [0, 0.16])})`
                            : "none",
                      }}
                    >
                      →
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 56,
          left: 1200,
          width: 620,
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-start",
          gap: 20,
          opacity: interpolate(frame, [0, fps], [0, 1]) * swipeFade,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 46,
            color: "#64748b",
            fontSize: 40,
          }}
        >
          <span>‹</span>
          <div
            style={{
              borderRadius: 999,
              border: "1px solid rgba(15,23,42,0.05)",
              backgroundColor: "rgba(255,255,255,0.65)",
              padding: "12px 26px",
              display: "flex",
              gap: 8,
              alignItems: "center",
            }}
          >
            {cards.map((_, i) => (
              <span
                key={String(i)}
                style={{
                  width: i === selectedIndex ? 42 : 8,
                  height: 8,
                  borderRadius: 999,
                  backgroundColor: i === selectedIndex ? "#14b8a6" : "rgba(15,23,42,0.2)",
                }}
              />
            ))}
          </div>
          <span>›</span>
        </div>
        <div
          style={{
            color: "#64748b",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 4,
            textTransform: "uppercase",
          }}
        >
          Swipe or use arrows to navigate
        </div>
      </div>
    </AbsoluteFill>
  );
};
