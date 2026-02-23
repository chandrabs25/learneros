import {loadFont as loadOutfit} from "@remotion/google-fonts/Outfit";
import {loadFont as loadSpaceGrotesk} from "@remotion/google-fonts/SpaceGrotesk";
import {AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

const {fontFamily: displayFont} = loadSpaceGrotesk("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});
const {fontFamily: bodyFont} = loadOutfit("normal", {
  weights: ["300", "400", "500", "600", "700"],
  subsets: ["latin"],
});

type SmallCard = {
  id: string;
  title: string;
  subtitle: string;
  color: string;
  x: number;
  y: number;
  chip?: string;
  icon: string;
};

const smallCards: SmallCard[] = [
  {
    id: "bio",
    title: "Biology",
    subtitle: "Natural Sciences",
    color: "#22C55E",
    x: 250,
    y: 360,
    icon: "🧬",
  },
  {
    id: "chem",
    title: "Chemistry",
    subtitle: "Matter & Energy",
    color: "#F020B1",
    x: 620,
    y: 360,
    icon: "🧪",
  },
  {
    id: "math",
    title: "Mathematics",
    subtitle: "STEM",
    color: "#FF3366",
    x: 250,
    y: 690,
    chip: "Coming Soon",
    icon: "∑",
  },
  {
    id: "history",
    title: "History",
    subtitle: "World Cultures",
    color: "#00A3FF",
    x: 620,
    y: 690,
    chip: "Coming Soon",
    icon: "⌛",
  },
];

export const AtlasScene = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const sceneIn = spring({
    frame,
    fps,
    config: {damping: 200},
    durationInFrames: Math.round(0.8 * fps),
  });

  const pulse = interpolate(frame, [1.8 * fps, 2.6 * fps, 3.4 * fps, 4.2 * fps], [0.14, 0.26, 0.16, 0.24], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });
  const physicsPress = interpolate(frame, [0.15 * fps, 0.4 * fps, 0.75 * fps], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #F4F4F5 0%, #EEF2F5 100%)",
        fontFamily: bodyFont,
        color: "#09090B",
        transform: `scale(${interpolate(sceneIn, [0, 1], [1.02, 1])})`,
        opacity: interpolate(sceneIn, [0, 1], [0, 1]),
      }}
    >
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
        <div style={{display: "flex", alignItems: "center", gap: 24}}>
          <div style={{display: "flex", gap: 32, color: "#64748b", fontWeight: 600}}>
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
          left: 250,
          top: 180,
          display: "flex",
          alignItems: "center",
          gap: 10,
          color: "#64748B",
          fontWeight: 700,
        }}
      >
        <span style={{color: "#4F46E5"}}>Hub</span>
        <span>›</span>
        <span style={{color: "#09090B"}}>Grade 11</span>
      </div>
      <div
        style={{
          position: "absolute",
          left: 250,
          top: 222,
          fontFamily: displayFont,
          fontSize: 78,
          lineHeight: 1,
          letterSpacing: -2,
          fontWeight: 700,
          color: "#09090B",
        }}
      >
        The Atlas
      </div>

      {smallCards.map((card, i) => {
        const cardIn = spring({
          frame: frame - i * 4,
          fps,
          config: {damping: 200},
          durationInFrames: Math.round(0.7 * fps),
        });

        return (
          <div
            key={card.id}
            style={{
              position: "absolute",
              left: card.x,
              top: card.y,
              width: 340,
              height: 300,
              borderRadius: 30,
              backgroundColor: "#FFFFFF",
              border: "1px solid #E2E8F0",
              boxShadow: "0 18px 30px -22px rgba(9,9,11,0.34)",
              padding: "20px 22px",
              transform: `translateY(${interpolate(cardIn, [0, 1], [22, 0])}px) scale(${interpolate(
                cardIn,
                [0, 1],
                [0.96, 1],
              )})`,
              opacity: interpolate(cardIn, [0, 1], [0, 1]),
            }}
          >
            <div style={{display: "flex", justifyContent: "space-between", alignItems: "center"}}>
              {card.chip ? (
                <span
                  style={{
                    fontSize: 12,
                    textTransform: "uppercase",
                    letterSpacing: 1.3,
                    fontWeight: 700,
                    padding: "6px 12px",
                    borderRadius: 999,
                    backgroundColor: "#E2E8F0",
                    color: "#64748B",
                  }}
                >
                  {card.chip}
                </span>
              ) : (
                <span />
              )}
            </div>

            <div
              style={{
                position: "absolute",
                left: 22,
                right: 22,
                top: "48%",
                transform: "translateY(-50%)",
                display: "flex",
                justifyContent: "center",
                color: card.color,
                fontSize: 58,
                opacity: 0.95,
              }}
            >
              {card.icon}
            </div>

            <div style={{position: "absolute", left: 22, right: 22, bottom: 24}}>
              <div
                style={{
                  fontFamily: displayFont,
                  fontSize: 44,
                  lineHeight: 1,
                  letterSpacing: -1,
                  fontWeight: 700,
                }}
              >
                {card.title}
              </div>
              <div
                style={{
                  marginTop: 8,
                  color: "#64748B",
                  fontSize: 16,
                  textTransform: "uppercase",
                  letterSpacing: 1.2,
                  fontWeight: 700,
                }}
              >
                {card.subtitle}
              </div>
            </div>
          </div>
        );
      })}

      <div
        style={{
          position: "absolute",
          left: 990,
          top: 360,
          width: 700,
          height: 630,
          borderRadius: 30,
          backgroundColor: "#FFFFFF",
          border: "1px solid #E2E8F0",
          boxShadow: `0 34px 58px -26px rgba(9,9,11,0.28), 0 0 0 ${interpolate(
            physicsPress,
            [0, 1],
            [10, 16],
          )}px rgba(138,63,252,${pulse})`,
          transform: `translateY(${interpolate(sceneIn, [0, 1], [24, 0])}px) scale(${interpolate(
            physicsPress,
            [0, 1],
            [1, 0.965],
          )})`,
        }}
      >
        <div
          style={{
            marginTop: 44,
            marginLeft: 44,
            width: "fit-content",
            fontSize: 12,
            textTransform: "uppercase",
            letterSpacing: 1.6,
            fontWeight: 800,
            padding: "7px 12px",
            borderRadius: 999,
            backgroundColor: "#E2E8F0",
            color: "#64748B",
          }}
        >
          Priority Path
        </div>
        <div
          style={{
            marginTop: 84,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: 220,
              height: 220,
              borderRadius: 30,
              background:
                "radial-gradient(circle at 40% 42%, #29E3C8 0%, #0EA5A0 28%, #03142C 54%, #020814 100%)",
              boxShadow: "0 30px 46px -22px rgba(2,8,20,0.7)",
              display: "grid",
              placeItems: "center",
              fontSize: 120,
              color: "rgba(255,255,255,0.35)",
            }}
          >
            ◌
          </div>
        </div>
        <div style={{position: "absolute", left: 44, bottom: 46}}>
          <div style={{fontFamily: displayFont, fontSize: 54, lineHeight: 1, fontWeight: 700}}>Physics</div>
          <div style={{marginTop: 10, color: "#64748B", fontSize: 24, fontWeight: 700}}>14 Chapters</div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          right: 35,
          bottom: 30,
          width: 70,
          height: 70,
          borderRadius: 999,
          backgroundColor: "#000",
          color: "#fff",
          display: "grid",
          placeItems: "center",
          fontSize: 44,
          lineHeight: 1,
          boxShadow: "0 14px 24px -14px rgba(0,0,0,0.8)",
        }}
      >
        +
      </div>

      <div
        style={{
          position: "absolute",
          left: 20,
          bottom: 18,
          width: 42,
          height: 42,
          borderRadius: 999,
          backgroundColor: "#111827",
          border: "2px solid #4B5563",
          color: "#D1D5DB",
          display: "grid",
          placeItems: "center",
          fontSize: 18,
        }}
      >
        N
      </div>
    </AbsoluteFill>
  );
};
