import { loadFont as loadOutfit } from "@remotion/google-fonts/Outfit";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";
import {
  AbsoluteFill, Easing, Img, interpolate, interpolateColors, spring,
  useCurrentFrame,
  useVideoConfig,
  staticFile,
} from "remotion";
const { fontFamily: displayFont } = loadSpaceGrotesk("normal", {
  weights: ["500", "600", "700"],
  subsets: ["latin"],
});

// We recreate the KnowledgeGraph here so we can hook specific scene frame timing into its SVGs.
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

export const KnowledgeGraphAnimated = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // The user explicitly requested synchronization at the 275th global frame.
  // In `LearnerosPitch.tsx`, `AtlasScene` starts at global frame 93 (2.26 * 30 + 25).
  // 275 - 93 = 182 local frame.
  const syncFrame = 182;
  const isSyncReached = frame >= syncFrame;

  // Pulse the center lightbulb slowly ONLY BEFORE the sync frame
  const baseCenterPulse = interpolate(frame % Math.round(1.8 * fps), [0, 0.9 * fps, 1.8 * fps], [1, 1.05, 1], {
    easing: Easing.inOut(Easing.quad),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const centerPulse = isSyncReached ? 1 : baseCenterPulse;

  // Blink the Vectors node to draw attention before the click
  const vectorBlink = interpolate(
    frame % Math.round(1 * fps),
    [0, 0.5 * fps, 1 * fps],
    [0.1, 0.8, 0.1],
    {
      easing: Easing.inOut(Easing.quad),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  const centerX = 660; // Relative to the 1920x1080 canvas if it was full screen, but inside 700x630 card we must center it.
  // We need to fit a huge graph inside a 700x630 card. The graph's native radius is 280, meaning it spans 560x560.
  // If we set center to 350, 315 it perfectly centers inside the 700x630 container.
  const localCenterX = 350;
  const localCenterY = 315;
  const radius = 220; // Slightly smaller to fit comfortably

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
        {graphNodes.map((_, i) => {
          const a = -Math.PI / 2 + (i / graphNodes.length) * Math.PI * 2;
          const x = localCenterX + Math.cos(a) * radius;
          const y = localCenterY + Math.sin(a) * radius;
          return <line key={`line-${String(i)}`} x1={localCenterX} y1={localCenterY} x2={x} y2={y} stroke="#e2e8f0" strokeWidth={1.2} />;
        })}
      </svg>

      <div
        style={{
          position: "absolute",
          left: localCenterX - 48,
          top: localCenterY - 48,
          width: 96,
          height: 96,
          borderRadius: 999,
          backgroundColor: "#fff",
          border: isSyncReached ? "2px solid #e2e8f0" : "4px solid #0d9488",
          display: "grid",
          placeItems: "center",
          transform: `scale(${centerPulse})`,
          boxShadow: isSyncReached ? "0 6px 16px -12px rgba(15,23,42,0.35)" : `0 0 0 10px rgba(13,148,136,0.1)`,
          transition: "border 0.2s, box-shadow 0.2s, background-color 0.2s, transform 0.2s"
        }}
      >
        <span style={{ fontSize: 36, color: isSyncReached ? "#94a3b8" : "#0d9488", transition: "color 0.2s" }}>💡</span>
      </div>

      <div
        style={{
          position: "absolute",
          left: localCenterX - 110,
          top: localCenterY + 65,
          width: 220,
          borderRadius: 999,
          backgroundColor: "#111827",
          color: "#fff",
          textAlign: "center",
          padding: "5px 10px",
          boxShadow: "0 10px 22px -15px rgba(17,24,39,0.7)",
        }}
      >
        <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: 1.2, textTransform: "uppercase", opacity: 0.7 }}>
          Chapter 5
        </div>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase" }}>Work, Energy & Power</div>
      </div>

      {graphNodes.map((name, i) => {
        const a = -Math.PI / 2 + (i / graphNodes.length) * Math.PI * 2;
        const x = localCenterX + Math.cos(a) * radius;
        const y = localCenterY + Math.sin(a) * radius;
        const delay = i * 2;
        const nodeIn = spring({
          frame: frame - delay,
          fps,
          config: { damping: 200 },
          durationInFrames: Math.round(0.6 * fps),
        });

        const isVectors = name === "Vectors";
        // The blinking only happens for Vectors after the exact sync threshold (frame 275)
        const showBlink = isVectors && isSyncReached;

        return (
          <div
            key={name}
            style={{
              position: "absolute",
              left: x - 28,
              top: y - 28,
              transform: `scale(${interpolate(nodeIn, [0, 1], [0.84, 1])})`,
              opacity: interpolate(nodeIn, [0, 1], [0, 1]),
            }}
          >
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 999,
                backgroundColor: "#fff",
                border: showBlink ? "2px solid #0d9488" : "1px solid #dbe3ed",
                display: "grid",
                placeItems: "center",
                boxShadow: showBlink
                  ? `0 0 0 8px rgba(13,148,136,${vectorBlink}), 0 6px 16px -12px rgba(15,23,42,0.35)`
                  : "0 6px 16px -12px rgba(15,23,42,0.35)",
              }}
            >
              <span style={{ color: showBlink ? "#0d9488" : "#64748b", fontSize: 22 }}>⚗</span>
            </div>
            <div
              style={{
                marginTop: 6,
                marginLeft: "50%",
                transform: "translateX(-50%)",
                whiteSpace: "nowrap",
                backgroundColor: showBlink ? "#000" : "#fff",
                color: showBlink ? "#fff" : "#111827",
                border: "1px solid #e2e8f0",
                borderRadius: 999,
                padding: "3px 8px",
                fontSize: 9,
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
  );
};
const { fontFamily: bodyFont } = loadOutfit("normal", {
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

const LogoShatter = ({ frame, fps }: { frame: number; fps: number }) => {
  // New Transition Timing:
  // 25.0s - 25.5s: Screen turns completely black
  // 25.5s - 26.2s: The black screen shrinks down into a small black square
  // 26.2s - 26.8s: The black square explodes into pieces
  // 26.8s - 28.5s: The pieces reassemble into the final logo

  const blackScreenStart = 25.0 * fps;
  const shrinkStart = 25.5 * fps;
  const explodeStart = 26.2 * fps;
  const assembleStart = 26.8 * fps;
  const assembleEnd = 28.5 * fps;

  if (frame < blackScreenStart) return null;

  const GRID_SIZE = 6;
  const LOGO_W = 300;
  const PIECE_W = LOGO_W / GRID_SIZE;

  // Stable randomness using a simple pseudo-random function
  const random = (seed: number) => {
    const x = Math.sin(seed) * 10000;
    return x - Math.floor(x);
  };

  const pieces = [];
  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      const idx = row * GRID_SIZE + col;
      const rX = (random(idx * 1.1) - 0.5) * 1200;
      const rY = (random(idx * 1.2) - 0.5) * 1200;
      const rRot = (random(idx * 1.3) - 0.5) * 720;
      const rScale = random(idx * 1.4) * 0.5 + 0.5;
      const delay = random(idx * 1.5) * 0.4 * fps;

      pieces.push({ row, col, rX, rY, rRot, rScale, delay });
    }
  }

  // 1. Screen turns completely black
  const blackScreenOpacity = interpolate(frame, [blackScreenStart, blackScreenStart + 0.5 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic)
  });

  // 2. Black screen shrinks down to the logo bounds
  // We'll use a massive size (e.g. 3000px) that covers the screen and shrink it down to LOGO_W
  const shrinkScale = interpolate(frame, [shrinkStart, explodeStart], [15, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic)
  });

  // The central container for everything
  return (
    <div style={{ position: "absolute", left: 1920 / 2 - LOGO_W / 2, top: 1080 / 2 - LOGO_W / 2, width: LOGO_W, height: LOGO_W, zIndex: 100 }}>
      {/* The Shrinking Black Mass */}
      {frame < explodeStart && (
        <div style={{
          position: "absolute",
          left: 0,
          top: 0,
          width: LOGO_W,
          height: LOGO_W,
          backgroundColor: "#000",
          opacity: blackScreenOpacity,
          transform: `scale(${shrinkScale})`,
          transformOrigin: "center",
          borderRadius: interpolate(frame, [shrinkStart, explodeStart], [0, 60], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp"
          })
        }} />
      )}

      {/* The Shattering Logo Pieces */}
      {frame >= explodeStart && pieces.map((p) => {
        let x = interpolate(frame, [explodeStart, assembleStart], [LOGO_W / 2 - PIECE_W / 2, p.rX], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.exp),
        });
        let y = interpolate(frame, [explodeStart, assembleStart], [LOGO_W / 2 - PIECE_W / 2, p.rY], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.exp),
        });
        let rot = interpolate(frame, [explodeStart, assembleStart], [0, p.rRot], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        let scale = interpolate(frame, [explodeStart, assembleStart], [0, p.rScale], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.exp),
        });

        const pAssembleStart = assembleStart + p.delay;
        const pAssembleEnd = pAssembleStart + 1.0 * fps;

        x = interpolate(frame, [pAssembleStart, pAssembleEnd], [x, p.col * PIECE_W], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.inOut(Easing.cubic),
        });
        y = interpolate(frame, [pAssembleStart, pAssembleEnd], [y, p.row * PIECE_W], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.inOut(Easing.cubic),
        });
        rot = interpolate(frame, [pAssembleStart, pAssembleEnd], [rot, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.inOut(Easing.cubic),
        });
        scale = interpolate(frame, [pAssembleStart, pAssembleEnd], [scale, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.inOut(Easing.cubic),
        });

        // The pieces transition from black to the actual image texture right as they explode
        const colorFactor = interpolate(frame, [explodeStart, explodeStart + 0.3 * fps], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp"
        });

        return (
          <div
            key={`${p.row}-${p.col}`}
            style={{
              position: "absolute",
              width: PIECE_W,
              height: PIECE_W,
              left: 0,
              top: 0,
              transform: `translate(${x}px, ${y}px) rotate(${rot}deg) scale(${scale})`,
              // We simulate the pieces initially being black and then revealing the logo
              backgroundColor: colorFactor < 1 ? "#000" : "transparent",
              backgroundImage: colorFactor > 0 ? `url(${staticFile("learneros-logo.jpg")})` : "none",
              backgroundSize: `${LOGO_W}px ${LOGO_W}px`,
              backgroundPosition: `${-p.col * PIECE_W}px ${-p.row * PIECE_W}px`,
              opacity: colorFactor,
              borderRadius: interpolate(frame, [pAssembleStart, pAssembleEnd], [8, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              boxShadow: interpolate(frame, [pAssembleStart, pAssembleEnd], [10, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }) > 0 ? "0 10px 20px rgba(0,0,0,0.2)" : "none",
            }}
          >
            {/* Provide a solid black underlay that fades out to reveal the texture */}
            <div style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "#000",
              opacity: 1 - colorFactor
            }} />
          </div>
        );
      })}
    </div>
  );
};

export const AtlasScene = () => {
  const frame = useCurrentFrame();
  const { fps, width: videoWidth, height: videoHeight } = useVideoConfig();

  const sceneIn = spring({
    frame,
    fps,
    config: { damping: 200 },
    durationInFrames: Math.round(0.8 * fps),
  });

  const convergeStart = 25.0 * fps;
  const convergeEnd = 26.0 * fps;

  const convergeScale = interpolate(frame, [convergeStart, convergeEnd], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.exp),
  });

  const convergeRotate = interpolate(frame, [convergeStart, convergeEnd], [0, 90], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.in(Easing.exp),
  });

  const convergeOpacity = interpolate(
    frame,
    [convergeStart + 0.5 * fps, convergeEnd],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

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

  const endWhiteout = interpolate(frame, [2.7 * fps, 3.1 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });

  const cardFlip = interpolate(frame, [2.7 * fps, 3.1 * fps], [0, 180], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const cardContentOpacity = interpolate(cardFlip, [80, 100], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const centerMove = interpolate(frame, [3.2 * fps, 4.7 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  const graphFadeIn = interpolate(centerMove, [0.3, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Increased negative translation to slide the card to the left instead of the center
  const moveX = interpolate(centerMove, [0, 1], [0, -680]);
  const moveY = interpolate(centerMove, [0, 1], [0, -135]);

  const centerScale = interpolate(centerMove, [0, 1], [1, 1.45]);

  // Rolling text animation on the right side, starting just as the card arrives (around 4.4s)
  const textEntranceProgress = interpolate(frame, [4.4 * fps, 5.2 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic)
  });

  // Text disappears instantly at 6.0s local (= 9.0s global) when Vector node is pressed
  const textExitProgress = frame < 6.0 * fps ? 1 : 0;

  const textRollUp = interpolate(textEntranceProgress, [0, 1], [50, 0]);
  const textOpacity = textEntranceProgress * textExitProgress; // replaces textFadeIn

  // Vector Profile card appears instantly at 6.0s local (= 9.0s global) when Vector node is pressed
  const vectorProfileEntrance = frame >= 6.0 * fps ? 1 : 0;
  const vectorProfileY = 0;

  // Physics card stays visible after vector node is selected
  const graphCardVanishOpacity = 1;
  const graphCardVanishScale = 1;

  // At 11s global = 8.0s local — slow 1.5s fade so everything dissolves gracefully
  const sceneVanishStart = 8.0 * fps;
  const sceneVanishOpacity = interpolate(frame, [sceneVanishStart, sceneVanishStart + fps * 1.5], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // Misconception card position math (precise pixel calculation):
  // Card top:140, padding-top:32 → content starts at 172
  // Header 44px → 216; Vectors title (marginTop:30, h:60) → 306
  // Subtitle (marginTop:5, h:20) → 331; ViewAnim button (marginTop:24, h:52) → 407
  // Metrics row (marginTop:30, h:112) → 549; Single metric (marginTop:16, h:112) → 677
  // Inline block marginTop:24 → starts at 701
  const misconceptionCardWidth = 500;
  const misconceptionInitialLeft = videoWidth - 40 - 580 + 40; // = videoWidth - 580 (left edge of card content)
  const misconceptionInitialTop = 701;
  const misconceptionTargetTop = videoHeight / 2 - 130; // Vertically centered
  // Standalone card appears immediately alongside the Vector Profile Card at 6.0s local (9.0s global)
  // It stays fully opaque while everything else fades out
  const misconceptionVisible = frame >= 6.0 * fps ? 1 : 0;
  // 5. Flip into Input Bar and Enter Button (15.0s local = 18.0s global)
  const flipStart = 15.0 * fps;
  const flipDuration = fps * 1.5;

  const inputBarTargetTop = videoHeight - 160;
  const inputBarTargetWidth = 800;
  const inputBarTargetLeft = (videoWidth - inputBarTargetWidth - 80) / 2;
  const enterBtnWidth = 70;
  const enterBtnLeft = inputBarTargetLeft + inputBarTargetWidth + 20;

  // Slide to left and scale happens simultaneously with the vanish (8.0s local = 11.0s global)
  // Matching the vanish duration of 1.5s for a fully synchronized, smooth transition
  const misconceptionSlideStart = sceneVanishStart;
  const misconceptionSlideDuration = fps * 1.5;

  const misconceptionLeft = interpolate(
    frame,
    [misconceptionSlideStart, misconceptionSlideStart + misconceptionSlideDuration, flipStart, flipStart + flipDuration],
    [misconceptionInitialLeft, 40, 40, inputBarTargetLeft],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const misconceptionTop = interpolate(
    frame,
    [misconceptionSlideStart, misconceptionSlideStart + misconceptionSlideDuration, flipStart, flipStart + flipDuration],
    [misconceptionInitialTop, misconceptionTargetTop, misconceptionTargetTop, inputBarTargetTop],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const misconceptionScale = interpolate(
    frame,
    [misconceptionSlideStart, misconceptionSlideStart + misconceptionSlideDuration, flipStart, flipStart + flipDuration],
    [1, 2, 2, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const misconceptionWidth = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [misconceptionCardWidth, inputBarTargetWidth],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const misconceptionHeight = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [270, 80],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const misconceptionRotateX = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [0, 180],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  // SEQUENTIAL TESTING ANIMATIONS

  // 1. "Test" button is clicked at 10.0s local (13.0s global)
  const testButtonClickStart = 10.0 * fps;
  const testButtonScale = interpolate(
    frame,
    [testButtonClickStart, testButtonClickStart + fps * 0.1, testButtonClickStart + fps * 0.2],
    [1, 0.9, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // 2. MCQ appears on the right starting at 10.5s local (13.5s global)
  const mcqAppearStart = 10.5 * fps;
  const mcqOpacity = interpolate(frame, [mcqAppearStart, mcqAppearStart + fps * 0.5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const mcqFinalLeft = videoWidth - 40 - 580;
  const mcqLeft = interpolate(
    frame,
    [mcqAppearStart, mcqAppearStart + fps * 0.8, flipStart, flipStart + flipDuration],
    [videoWidth + 100, mcqFinalLeft, mcqFinalLeft, enterBtnLeft],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const mcqTop = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [misconceptionTargetTop - 50, inputBarTargetTop],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const mcqWidth = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [580, enterBtnWidth],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const mcqHeight = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [380, 70],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const mcqRotateY = interpolate(
    frame,
    [flipStart, flipStart + flipDuration],
    [0, -180],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  // 3. User selects the correct answer at 12.5s local (15.5s global)
  const answerSelectStart = 12.5 * fps;
  const correctAnswerBg = interpolateColors(
    frame,
    [answerSelectStart, answerSelectStart + fps * 0.2],
    ["#f8fafc", "#10b981"] // Gray to green
  );
  const correctAnswerText = interpolateColors(
    frame,
    [answerSelectStart, answerSelectStart + fps * 0.2],
    ["#09090b", "#ffffff"] // Black to white
  );
  const correctAnswerBorder = interpolateColors(
    frame,
    [answerSelectStart, answerSelectStart + fps * 0.2],
    ["#e2e8f0", "#10b981"] // Border to green
  );

  // 4. Misconception card transforms into Competency at 13.5s local (16.5s global)
  const transformStart = 13.5 * fps;
  const transformProgress = interpolate(frame, [transformStart, transformStart + fps * 0.5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // Interpolating colors for the transformation
  const cardBorderColor = interpolateColors(
    frame,
    [transformStart, transformStart + fps * 0.5],
    ["#ef4444", "#10b981"] // Red to Green
  );
  const cardBadgeBg = interpolateColors(
    frame,
    [transformStart, transformStart + fps * 0.5],
    ["#fef2f2", "#ecfdf5"] // Light red to light green
  );

  // 6. Typing the physics question into the Input Bar (17.0s - 18.0s local = 20.0s - 21.0s global)
  const typingStart = 17.0 * fps;
  const questionText = "What is the true difference between conservative and non-conservative forces?";
  const typingProgress = interpolate(
    frame,
    [typingStart, typingStart + fps * 1.0],
    [0, questionText.length],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.linear }
  );
  const currentText = questionText.substring(0, Math.floor(typingProgress));

  // 7. Clicking the Enter Button (18.2s local = 21.2s global)
  const enterBtnClickStart = 18.2 * fps;
  const enterBtnScale = interpolate(
    frame,
    [enterBtnClickStart, enterBtnClickStart + fps * 0.1, enterBtnClickStart + fps * 0.2],
    [1, 0.85, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // 8. Input bar and Enter btn fade/scale out (18.5s local = 21.5s global)
  const inputFadeOutStart = 18.5 * fps;
  const inputFadeOut = interpolate(
    frame,
    [inputFadeOutStart, inputFadeOutStart + fps * 0.4],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  // 9. User Message Animates Up (18.5s local = 21.5s global)
  const userMsgStart = 18.5 * fps;
  const userMsgOpacity = interpolate(
    frame,
    [userMsgStart, userMsgStart + fps * 0.5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }
  );

  const userMsgTop = interpolate(
    frame,
    [userMsgStart, userMsgStart + fps * 0.8],
    [videoHeight - 160, videoHeight - 480], // slides up from initial input bar pos
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.back(1.2)) }
  );

  // 10. AI Response Animates Up (19.5s local = 22.5s global)
  const aiMsgStart = 19.5 * fps;
  const aiMsgOpacity = interpolate(
    frame,
    [aiMsgStart, aiMsgStart + fps * 0.5],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) }
  );

  const aiMsgTop = interpolate(
    frame,
    [aiMsgStart, aiMsgStart + fps * 0.8],
    [videoHeight - 100, videoHeight - 330],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.back(1.1)) }
  );

  // 11. Side Panels Fading In (19.5s local = 22.5s global)
  const sidePanelsOpacity = interpolate(
    frame,
    [aiMsgStart, aiMsgStart + fps * 0.8],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.inOut(Easing.cubic) }
  );

  const chapterInsights = [
    {
      label: "Partial Understanding",
      color: "#d97706",
      title: "Mechanical Energy Conservation",
      body: "Student implies energy increases rather than remaining constant between forms, misunderstanding core conservation laws.",
    },
    {
      label: "Competency",
      color: "#10b981",
      title: "Work-Energy Theorem",
      body: "Student accurately links net work done to kinetic-energy change and applies the theorem correctly across examples.",
    },
    {
      label: "Misconception",
      color: "#f43f5e",
      title: "Conservative Forces",
      body: "Student struggles to identify proper potential-energy reference points in complex field scenarios.",
    },
    {
      label: "Competency",
      color: "#10b981", // Emerald
      title: "Momentum",
      body: "Successfully identifies isolated systems and applies conservation of momentum to perfectly elastic collisions.",
    },
    {
      label: "Partial Understanding",
      color: "#d97706", // Amber
      title: "Power",
      body: "Calculates average power correctly but struggles to find instantaneous power using the dot product of force and velocity.",
    }
  ];

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
      <div style={{ position: "absolute", inset: 0, transformOrigin: "center center", transform: `scale(${convergeScale}) rotate(${convergeRotate}deg)`, opacity: convergeOpacity }}>
        <div
          style={{
            position: "absolute",
            top: 52,
            left: 80,
            right: 80,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            opacity: sceneVanishOpacity,
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
            left: 250,
            top: 180,
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "#64748B",
            fontWeight: 700,
            opacity: sceneVanishOpacity,
          }}
        >
          <span style={{ color: "#4F46E5" }}>Hub</span>
          <span>›</span>
          <span style={{ color: "#09090B" }}>Grade 11</span>
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
            opacity: sceneVanishOpacity,
          }}
        >
          The Atlas
        </div>

        {smallCards.map((card, i) => {
          const cardIn = spring({
            frame: frame - i * 4,
            fps,
            config: { damping: 200 },
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
                opacity: interpolate(cardIn, [0, 1], [0, 1]) * sceneVanishOpacity,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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

              <div style={{ position: "absolute", left: 22, right: 22, bottom: 24 }}>
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

        {/* This whiteout covers everything rendered before it (title, header, small cards) when the scene ends */}
        <AbsoluteFill
          style={{
            backgroundColor: "#ffffff",
            opacity: endWhiteout,
            pointerEvents: "none",
            zIndex: 5
          }}
        />

        <div
          style={{
            position: "absolute",
            left: 990,
            top: 360,
            width: 700,
            height: 630,
            borderRadius: 30,
            backgroundColor: "#FFFFFF",
            border: "2px solid #000000", /* Added black border highlight */
            boxShadow: `0 30px 60px -15px rgba(0, 0, 0, 0.6), 0 0 0 ${interpolate(
              physicsPress,
              [0, 1],
              [10, 16],
            )
              }px rgba(0, 0, 0, ${pulse})`, /* Changed purple pulse to black pulse */
            transform: `translateX(${moveX}px) translateY(${interpolate(sceneIn, [0, 1], [24, 0]) + moveY}px) scale(${interpolate(
              physicsPress,
              [0, 1],
              [1, 0.965],
            ) * centerScale * graphCardVanishScale}) rotateY(${cardFlip}deg)`,
            opacity: graphCardVanishOpacity * sceneVanishOpacity,
            zIndex: 10,
          }}
        >
          <AbsoluteFill style={{ opacity: cardContentOpacity }}>
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
            <div style={{ position: "absolute", left: 44, bottom: 46 }}>
              <div style={{ fontFamily: displayFont, fontSize: 54, lineHeight: 1, fontWeight: 700 }}>Physics</div>
              <div style={{ marginTop: 10, color: "#64748B", fontSize: 24, fontWeight: 700 }}>14 Chapters</div>
            </div>
          </AbsoluteFill>

          {/* BACK OF CARD: The Graph Scene renders here as it centers */}
          <AbsoluteFill
            style={{
              opacity: graphFadeIn,
              transform: "rotateY(180deg)", /* counter-rotate the content so it faces forward when card is flipped */
              overflow: "hidden",
              borderRadius: 30,
              backgroundColor: "#f8fafc"
            }}
          >
            {/* The Graph Scene is natively sized to 700x630, so no wrapper is needed for scaling */}
            <KnowledgeGraphAnimated />
          </AbsoluteFill>
        </div>

        {/* NODE PROFILE TEXT: Displays purely as cascading elegant typography on the right */}
        <div
          style={{
            position: "absolute",
            right: 30,
            top: interpolate(frame, [4.4 * fps, 7.8 * fps], [350, 150], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            width: 600,
            height: interpolate(frame, [4.4 * fps, 7.8 * fps], [200, 700], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }), // Expanding height to increase visibility while scrolling
            overflow: "hidden", // Hide text as it scrolls out of this window
            opacity: textOpacity,
            zIndex: 50,
            // Fade text out cleanly at top and bottom of the container
            maskImage: "linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%)",
            WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 20%, black 80%, transparent 100%)"
          }}
        >
          <div style={{
            transform: `translateY(${interpolate(frame, [4.4 * fps, 7.8 * fps], [280, -960], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })}px)` // Continuous scroll upwards
          }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 30 }}>
              <span
                style={{
                  backgroundColor: "#1e293b",
                  color: "#f8fafc",
                  fontSize: 16,
                  fontWeight: 800,
                  padding: "8px 14px",
                  borderRadius: 6,
                  textTransform: "uppercase",
                  letterSpacing: 1.5,
                }}
              >
                Node Profile
              </span>
            </div>

            <div style={{ fontSize: 62, fontWeight: 800, lineHeight: 1.1, color: "#0f172a", marginBottom: 20, letterSpacing: -0.5 }}>
              Work, Energy and Power
            </div>
            <div style={{ fontSize: 18, color: "#14b8a6", textTransform: "uppercase", letterSpacing: 2.5, fontWeight: 800, marginBottom: 80 }}>
              Chapter Overview
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 70 }}>
              {chapterInsights.map((insight, index) => {
                return (
                  <div key={insight.title}>
                    <div style={{
                      fontSize: 18,
                      color: insight.color,
                      textTransform: "uppercase",
                      letterSpacing: 2.5,
                      fontWeight: 800,
                      marginBottom: 12
                    }}>
                      {insight.label}
                    </div>
                    <div style={{ fontSize: 32, fontWeight: 800, color: "#09090b", marginBottom: 14, letterSpacing: -0.2 }}>
                      {insight.title}
                    </div>
                    <div style={{ fontSize: 24, color: "#334155", lineHeight: 1.6, fontWeight: 500 }}>
                      {insight.body}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* NEW VECTOR PROFILE CARD (Appears at 9s) - vanishes at 11s */}
        <div style={{
          position: "absolute",
          right: 40,
          top: 140 + vectorProfileY, // Moved up to 140
          width: 580,
          opacity: vectorProfileEntrance * sceneVanishOpacity,
          zIndex: 60,
          backgroundColor: "#ffffff",
          borderRadius: 30,
          padding: "32px 40px", // Reduced top/bottom padding
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span style={{ backgroundColor: "#000", color: "#fff", padding: "8px 16px", borderRadius: 999, fontSize: 13, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1.5 }}>Insights</span>
              <span style={{ fontWeight: 800, fontSize: 20 }}>Node Profile</span>
            </div>
            <div style={{ width: 44, height: 44, borderRadius: 22, border: "2px solid #f1f5f9", display: "grid", placeItems: "center", color: "#64748b", fontWeight: 700 }}>✕</div>
          </div>

          <div style={{ fontSize: 50, fontWeight: 800, marginTop: 30, letterSpacing: -1 }}>Vectors</div>
          <div style={{ color: "#14b8a6", fontSize: 15, fontWeight: 800, textTransform: "uppercase", letterSpacing: 2, marginTop: 5 }}>Prerequisite Concept</div>

          <div style={{ marginTop: 24, backgroundColor: "#000", color: "#fff", padding: "16px", borderRadius: 16, display: "flex", alignItems: "center", gap: 12, fontWeight: 700 }}>
            <span style={{ fontSize: 22, marginLeft: 10 }}>⏵</span> View Animation
          </div>

          <div style={{ display: "flex", gap: 16, marginTop: 30 }}>
            <div style={{ flex: 1, border: "2px solid #f1f5f9", borderRadius: 20, padding: 20 }}>
              <div style={{ color: "#64748b", fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1.5 }}>Competency</div>
              <div style={{ color: "#10b981", fontSize: 48, fontWeight: 800, lineHeight: 1, marginTop: 10 }}>0</div>
            </div>
            <div style={{ flex: 1, border: "2px solid #f1f5f9", borderRadius: 20, padding: 20 }}>
              <div style={{ color: "#64748b", fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1.5 }}>Partial Understanding</div>
              <div style={{ color: "#f59e0b", fontSize: 48, fontWeight: 800, lineHeight: 1, marginTop: 10 }}>0</div>
            </div>
          </div>
          <div style={{ width: "48%", border: "2px solid #f1f5f9", borderRadius: 20, padding: 20, marginTop: 16 }}>
            <div style={{ color: "#64748b", fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1.5 }}>Misconception</div>
            <div style={{ color: "#ef4444", fontSize: 48, fontWeight: 800, lineHeight: 1, marginTop: 10 }}>1</div>
          </div>

          {/* Invisible spacer: maintains layout for Concept Lineage below it, while the actual misconception block is rendered standalone to avoid fading */}
          <div style={{ marginTop: 24, border: "2px solid #f1f5f9", borderRadius: 20, padding: "24px 20px", position: "relative", overflow: "hidden", opacity: 0 }}>
            {/* Left Red Border Highlight */}
            <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, backgroundColor: "#000" }}>
              <div style={{ position: "absolute", left: 0, top: 20, bottom: 20, width: 4, backgroundColor: "#ef4444" }}></div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, color: "#ef4444", fontWeight: 800, letterSpacing: 1.5, textTransform: "uppercase", fontSize: 12 }}>
                <span>ⓘ</span> Misconception
              </div>
              <div style={{ color: "#64748b", fontWeight: 800, letterSpacing: 1.5, textTransform: "uppercase", fontSize: 11 }}>Conceptual</div>
            </div>

            <div style={{ color: "#09090b", fontSize: 16, lineHeight: 1.6, fontWeight: 500, marginTop: 16 }}>
              The student incorrectly applies the cross product instead of the dot product to compute work, failing to recognize that work is a scalar quantity resulting from force and displacement.
            </div>

            <div style={{ color: "#64748b", fontSize: 13, fontWeight: 500, marginTop: 14 }}>
              Subsection: Generalization to Three Dimensions
            </div>

            <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
              <div style={{ backgroundColor: "#2dd4bf", color: "#000", padding: "8px 16px", borderRadius: 8, fontWeight: 800, fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
                <span>⚡</span> Explain
              </div>
              <div style={{ backgroundColor: "#3b82f6", color: "#fff", padding: "8px 16px", borderRadius: 8, fontWeight: 800, fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
                <span>?</span> Test
              </div>
            </div>
          </div>

          <div style={{ marginTop: 24, border: "2px solid #f1f5f9", borderRadius: 20, padding: 20, backgroundColor: "#f8fafc" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#64748b", fontWeight: 800, letterSpacing: 1.5, textTransform: "uppercase", fontSize: 13 }}>
              Concept Lineage
            </div>
            <div style={{ color: "#64748b", marginTop: 8, fontSize: 14, fontWeight: 500 }}>Grades: 2 • Subjects: 2 • Chapters: 8</div>
            <div style={{ marginTop: 16, backgroundColor: "#0f172a", color: "#fff", padding: "12px", borderRadius: 12, textAlign: "center", fontWeight: 700 }}>
              View Lineage Graph
            </div>
          </div>
        </div>

        {/* STANDALONE MISCONCEPTION/COMPETENCY BLOCK — animates to left-center and transforms */}
        {
          misconceptionVisible === 1 && (
            <div style={{
              position: "absolute",
              left: misconceptionLeft,
              top: misconceptionTop,
              width: misconceptionWidth,
              height: misconceptionHeight,
              transform: `scale(${misconceptionScale})`,
              transformOrigin: "center left",
              zIndex: 80,
              perspective: 1500,
            }}>
              <div style={{
                width: "100%",
                height: "100%",
                transformStyle: "preserve-3d",
                transform: `rotateX(${misconceptionRotateX}deg)`,
                position: "relative",
              }}>
                {/* FRONT FACE (Competency Card) */}
                <div style={{
                  position: "absolute",
                  inset: 0,
                  backfaceVisibility: "hidden",
                  border: `2px solid ${frame >= transformStart ? cardBorderColor : "#f1f5f9"}`,
                  borderRadius: 20,
                  padding: "24px 20px",
                  overflow: "hidden",
                  backgroundColor: "#ffffff",
                  boxShadow: "0 20px 40px -20px rgba(9,9,11,0.3)",
                  width: "100%",
                  height: "100%",
                  boxSizing: "border-box",
                }}>
                  {/* Left Border Highlight */}
                  <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 4, backgroundColor: "#000" }}>
                    <div style={{ position: "absolute", left: 0, top: 20, bottom: 20, width: 4, backgroundColor: cardBorderColor }}></div>
                  </div>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, color: cardBorderColor, fontWeight: 800, letterSpacing: 1.5, textTransform: "uppercase", fontSize: 12 }}>
                      <span>{frame >= transformStart + fps * 0.25 ? "✓" : "ⓘ"}</span>
                      {frame >= transformStart + fps * 0.25 ? "Competency" : "Misconception"}
                    </div>
                    <div style={{ color: frame >= transformStart + fps * 0.25 ? cardBorderColor : "#64748b", backgroundColor: cardBadgeBg, padding: "4px 10px", borderRadius: 8, fontWeight: 800, letterSpacing: 1.5, textTransform: "uppercase", fontSize: 11 }}>
                      Conceptual
                    </div>
                  </div>

                  <div style={{ color: "#09090b", fontSize: 16, lineHeight: 1.6, fontWeight: 500, marginTop: 16, display: "-webkit-box", WebkitLineClamp: 4, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                    {frame >= transformStart + fps * 0.25
                      ? "The student accurately applies the dot product to compute work, demonstrating a strong understanding that work is a scalar quantity resulting from force and displacement."
                      : "The student incorrectly applies the cross product instead of the dot product to compute work, failing to recognize that work is a scalar quantity resulting from force and displacement."}
                  </div>

                  <div style={{ color: "#64748b", fontSize: 13, fontWeight: 500, marginTop: 14 }}>
                    Subsection: Generalization to Three Dimensions
                  </div>

                  <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
                    <div style={{ backgroundColor: "#2dd4bf", color: "#000", padding: "8px 16px", borderRadius: 8, fontWeight: 800, fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
                      <span>⚡</span> Explain
                    </div>
                    <div style={{
                      backgroundColor: "#3b82f6",
                      color: "#fff",
                      padding: "8px 16px",
                      borderRadius: 8,
                      fontWeight: 800,
                      fontSize: 13,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      transform: `scale(${testButtonScale})`,
                      boxShadow: frame >= testButtonClickStart && frame < testButtonClickStart + fps * 0.2 ? "0 0 0 4px rgba(59, 130, 246, 0.4)" : "none"
                    }}>
                      <span>✦</span> Test
                    </div>
                  </div>
                </div>

                {/* BACK FACE (Input Bar) */}
                <div style={{
                  position: "absolute",
                  inset: 0,
                  backfaceVisibility: "hidden",
                  transform: "rotateX(180deg)",
                  backgroundColor: "#ffffff",
                  border: "2px solid #e2e8f0",
                  borderRadius: 40,
                  boxShadow: "0 10px 25px -5px rgba(0,0,0,0.1)",
                  display: "flex",
                  alignItems: "center",
                  padding: "0 32px",
                  fontSize: 22,
                  color: currentText.length > 0 ? "#0f172a" : "#64748b",
                  fontWeight: 500,
                  opacity: inputFadeOut,
                }}>
                  <span style={{ fontSize: 24, marginRight: 16, opacity: currentText.length > 0 ? 0 : 1 }}>✨</span>
                  {currentText.length > 0 ? currentText : "What else would you like to explore about work and energy?"}
                  {/* Blinking Cursor */}
                  {frame >= flipStart + flipDuration && frame < enterBtnClickStart && (
                    <span style={{
                      display: "inline-block",
                      width: 2,
                      height: 24,
                      backgroundColor: "#3b82f6",
                      marginLeft: 4,
                      opacity: Math.floor(frame / 15) % 2 === 0 ? 1 : 0
                    }} />
                  )}
                </div>
              </div>
            </div>
          )
        }

        {/* MULTIPLE CHOICE QUESTION BLOCK — slides in from right after test button is pressed */}
        {frame >= mcqAppearStart && (
          <div style={{
            position: "absolute",
            left: mcqLeft,
            top: mcqTop,
            width: mcqWidth,
            height: mcqHeight,
            opacity: mcqOpacity,
            zIndex: 70,
            perspective: 1500,
          }}>
            <div style={{
              width: "100%",
              height: "100%",
              transformStyle: "preserve-3d",
              transform: `rotateY(${mcqRotateY}deg)`,
              position: "relative",
            }}>
              {/* FRONT FACE (MCQ Card) */}
              <div style={{
                position: "absolute",
                inset: 0,
                backfaceVisibility: "hidden",
                backgroundColor: "#ffffff",
                borderRadius: 24,
                padding: "32px",
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                border: "1px solid #e2e8f0",
                width: "100%",
                height: "100%",
                boxSizing: "border-box",
                overflow: "hidden",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    <span style={{ backgroundColor: "#eff6ff", color: "#2563eb", padding: "6px 14px", borderRadius: 999, fontSize: 13, fontWeight: 800, textTransform: "uppercase", letterSpacing: 1.5 }}>Question 1</span>
                    <span style={{ color: "#64748b", fontWeight: 700, fontSize: 14 }}>Work & Vectors</span>
                  </div>
                  <div style={{ color: "#94a3b8", fontWeight: 700, fontSize: 14 }}>1/5</div>
                </div>

                <div style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", lineHeight: 1.5 }}>
                  {"A force F = (2i + 3j) N acts on an object as it moves through a displacement d = (4i + j) m. What is the total work done?"}
                </div>

                <div style={{ marginTop: 32, display: "flex", flexDirection: "column", gap: 16 }}>
                  {/* Wrong Option A */}
                  <div style={{ position: "relative", border: "2px solid #e2e8f0", borderRadius: 16, padding: "16px 20px", display: "flex", alignItems: "center", gap: 16, backgroundColor: "#f8fafc" }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%", border: "2px solid #cbd5e1", display: "grid", placeItems: "center", color: "#64748b", fontWeight: 800 }}>A</div>
                    <div style={{ fontSize: 18, fontWeight: 600, color: "#0f172a" }}>Work = (8i + 3j) J</div>
                  </div>

                  {/* Correct Option B (Animates when selected) */}
                  <div style={{ position: "relative", border: `2px solid ${correctAnswerBorder}`, borderRadius: 16, padding: "16px 20px", display: "flex", alignItems: "center", gap: 16, backgroundColor: correctAnswerBg, transform: `scale(${frame >= answerSelectStart && frame < answerSelectStart + fps * 0.2 ? 0.98 : 1})`, transition: "transform 0.1s" }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%", border: `2px solid ${frame >= answerSelectStart ? "rgba(255,255,255,0.5)" : "#cbd5e1"}`, display: "grid", placeItems: "center", color: frame >= answerSelectStart ? "#fff" : "#64748b", fontWeight: 800 }}>B</div>
                    <div style={{ fontSize: 18, fontWeight: 600, color: correctAnswerText }}>Work = 11 J</div>
                    {/* Checkmark icon for correct answer */}
                    <div style={{ position: "absolute", right: 20, opacity: frame >= answerSelectStart + fps * 0.1 ? 1 : 0, color: "#ffffff", fontSize: 24 }}>✓</div>
                  </div>

                  {/* Wrong Option C */}
                  <div style={{ position: "relative", border: "2px solid #e2e8f0", borderRadius: 16, padding: "16px 20px", display: "flex", alignItems: "center", gap: 16, backgroundColor: "#f8fafc" }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%", border: "2px solid #cbd5e1", display: "grid", placeItems: "center", color: "#64748b", fontWeight: 800 }}>C</div>
                    <div style={{ fontSize: 18, fontWeight: 600, color: "#0f172a" }}>Work = -10 J</div>
                  </div>
                </div>
              </div>

              {/* BACK FACE (Enter Button) */}
              <div style={{
                position: "absolute",
                inset: 0,
                backfaceVisibility: "hidden",
                transform: `rotateY(180deg) scale(${enterBtnScale})`,
                backgroundColor: currentText.length > 0 ? "#2563eb" : "#94a3b8", // Turns blue when text is typed
                borderRadius: "50%", // circle
                boxShadow: currentText.length > 0 ? "0 10px 25px -5px rgba(37,99,235,0.4)" : "none",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                color: "#ffffff",
                fontSize: 28,
                opacity: inputFadeOut,
              }}>
                ➔
              </div>
            </div>
          </div>
        )}

        {/* --- CHAT SEQUENCE --- */}

        {/* USER MESSAGE CARD */}
        {frame >= userMsgStart && (
          <div style={{
            position: "absolute",
            left: inputBarTargetLeft + inputBarTargetWidth - 600, // Aligned to the right side of the input bar area
            top: userMsgTop,
            width: 600,
            opacity: userMsgOpacity,
            zIndex: 85,
            backgroundColor: "#1e293b",
            color: "#f8fafc",
            borderRadius: "24px 24px 0 24px", // Chat bubble style pointing right
            padding: "20px 24px",
            boxShadow: "0 15px 35px -10px rgba(0,0,0,0.2)",
            fontSize: 20,
            lineHeight: 1.5,
            fontWeight: 500,
          }}>
            {questionText}
          </div>
        )}

        {/* AI RESPONSE CARD */}
        {frame >= aiMsgStart && (
          <div style={{
            position: "absolute",
            left: inputBarTargetLeft, // Aligned to the left side of the input bar area
            top: aiMsgTop,
            width: 680,
            opacity: aiMsgOpacity,
            zIndex: 84,
            backgroundColor: "#ffffff",
            border: "1px solid #e2e8f0",
            borderRadius: "24px 24px 24px 0", // Chat bubble style pointing left
            padding: "24px 32px",
            boxShadow: "0 25px 50px -12px rgba(0,0,0,0.15)",
          }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16 }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "linear-gradient(135deg, #3b82f6, #8b5cf6)", display: "grid", placeItems: "center", color: "#fff", fontSize: 16 }}>✨</div>
              <div style={{ fontWeight: 800, color: "#0f172a", letterSpacing: 1, textTransform: "uppercase", fontSize: 13 }}>AI Tutor</div>
            </div>
            <div style={{ fontSize: 18, lineHeight: 1.6, color: "#334155" }}>
              <span style={{ fontWeight: 700, color: "#0f172a" }}>Conservative forces</span> (like gravity or springs) store work as potential energy, meaning the total work done on a closed path is zero.
              <br /><br />
              <span style={{ fontWeight: 700, color: "#0f172a" }}>Non-conservative forces</span> (like friction) dissipate energy from the system as heat or sound, so the work depends on the actual path taken.
            </div>
          </div>
        )}

        {/* LEFT SIDE PANEL - Insights */}
        {frame >= aiMsgStart && (
          <div style={{
            position: "absolute",
            left: 40,
            top: 180,
            width: 320,
            opacity: sidePanelsOpacity,
            zIndex: 60,
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}>
            <div style={{ fontWeight: 800, fontSize: 13, textTransform: "uppercase", letterSpacing: 1.5, color: "#64748b", marginBottom: 8 }}>
              Related Insights
            </div>
            {/* Competency Card */}
            <div style={{ backgroundColor: "#ffffff", borderRadius: 16, padding: 16, border: "2px solid #10b981", boxShadow: "0 10px 20px -5px rgba(16,185,129,0.15)" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, color: "#10b981", fontWeight: 800, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <span>✓</span> Competency
              </div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a", marginBottom: 4 }}>Work-Energy Theorem</div>
              <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.4 }}>Student successfully links net work done to kinetic energy change.</div>
            </div>
            {/* Misconception Card */}
            <div style={{ backgroundColor: "#ffffff", borderRadius: 16, padding: 16, border: "2px solid #ef4444", boxShadow: "0 10px 20px -5px rgba(239,68,68,0.15)" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, color: "#ef4444", fontWeight: 800, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <span>ⓘ</span> Misconception
              </div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a", marginBottom: 4 }}>Path Independence</div>
              <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.4 }}>Student wrongly assumes work done by friction is path-independent.</div>
            </div>
            {/* Partial Understanding Card */}
            <div style={{ backgroundColor: "#ffffff", borderRadius: 16, padding: 16, border: "2px solid #d97706", boxShadow: "0 10px 20px -5px rgba(217,119,6,0.15)" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8, color: "#d97706", fontWeight: 800, fontSize: 11, textTransform: "uppercase", letterSpacing: 1 }}>
                <span>◆</span> Partial Understanding
              </div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a", marginBottom: 4 }}>Potential Energy</div>
              <div style={{ fontSize: 13, color: "#475569", lineHeight: 1.4 }}>Understands gravity but struggles with elastic potential.</div>
            </div>
          </div>
        )}

        {/* RIGHT SIDE PANEL - Concepts */}
        {frame >= aiMsgStart && (
          <div style={{
            position: "absolute",
            right: 40,
            top: 180,
            width: 320,
            opacity: sidePanelsOpacity,
            zIndex: 60,
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}>
            <div style={{ fontWeight: 800, fontSize: 13, textTransform: "uppercase", letterSpacing: 1.5, color: "#64748b", marginBottom: 8, textAlign: "right" }}>
              Related Concepts
            </div>
            <div style={{ backgroundColor: "#ffffff", borderRadius: 16, padding: 16, border: "1px solid #e2e8f0", boxShadow: "0 10px 20px -5px rgba(0,0,0,0.05)", display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: "#f1f5f9", display: "grid", placeItems: "center", fontSize: 18 }}>📐</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a" }}>Dot Product</div>
                <div style={{ fontSize: 12, color: "#64748b", fontWeight: 500, marginTop: 2 }}>Math Prerequisite</div>
              </div>
            </div>
            <div style={{ backgroundColor: "#ffffff", borderRadius: 16, padding: 16, border: "1px solid #e2e8f0", boxShadow: "0 10px 20px -5px rgba(0,0,0,0.05)", display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: "#f1f5f9", display: "grid", placeItems: "center", fontSize: 18 }}>🏃</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a" }}>Kinetic Energy</div>
                <div style={{ fontSize: 12, color: "#64748b", fontWeight: 500, marginTop: 2 }}>Core Concept Node</div>
              </div>
            </div>
            <div style={{ backgroundColor: "#ffffff", borderRadius: 16, padding: 16, border: "1px solid #e2e8f0", boxShadow: "0 10px 20px -5px rgba(0,0,0,0.05)", display: "flex", alignItems: "center", gap: 16 }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: "#f1f5f9", display: "grid", placeItems: "center", fontSize: 18 }}>🧱</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: "#0f172a" }}>Friction</div>
                <div style={{ fontSize: 12, color: "#64748b", fontWeight: 500, marginTop: 2 }}>Non-conservative force</div>
              </div>
            </div>
          </div>
        )}

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
            opacity: interpolate(endWhiteout, [0, 1], [1, 0]),
          }}
        >
          +
        </div>

      </div>{/* End converge wrapper */}

      <LogoShatter frame={frame} fps={fps} />

    </AbsoluteFill >
  );
};
