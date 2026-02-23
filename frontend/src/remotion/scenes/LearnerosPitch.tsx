import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ThreeDCenteredScenes } from "./ThreeDEnvironment";
import { AITutorScene } from "./AITutorScene";
import { AtlasScene } from "./AtlasScene";
import { InsightsDashboardScene } from "./InsightsDashboardScene";
import { KnowledgeGraphScene, KnowledgeGraphWorkScene } from "./KnowledgeGraphScene";
import { OpeningHubScene } from "./OpeningHubScene";
import { PhysicsChapterScene } from "./PhysicsChapterScene";
import { SubsectionViewerScene } from "./SubsectionViewerScene";

const StoryCaption = ({ title, subtitle }: { title: string; subtitle: string }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const captionIn = spring({
    frame,
    fps,
    config: { damping: 200 },
    durationInFrames: Math.round(0.55 * fps),
  });

  const captionOut = interpolate(frame, [2.2 * fps, 2.9 * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 82,
        bottom: 64,
        zIndex: 100,
        opacity: interpolate(captionIn, [0, 1], [0, 1]) * captionOut,
        transform: `translateY(${interpolate(captionIn, [0, 1], [16, 0])}px)`,
      }}
    >
      <div
        style={{
          minWidth: 620,
          maxWidth: 960,
          borderRadius: 16,
          border: "1px solid rgba(160,228,255,0.35)",
          background: "linear-gradient(145deg, rgba(8,21,34,0.76), rgba(11,24,38,0.56))",
          boxShadow: "0 18px 40px rgba(0,0,0,0.34)",
          backdropFilter: "blur(10px)",
          color: "#eaf7ff",
          fontFamily: "Outfit, sans-serif",
          padding: "13px 17px",
        }}
      >
        <div
          style={{
            fontSize: 11,
            color: "#89dbff",
            textTransform: "uppercase",
            letterSpacing: 1.4,
            fontWeight: 700,
          }}
        >
          Story Beat
        </div>
        <div style={{ fontSize: 33, lineHeight: 1.1, marginTop: 4, fontWeight: 700 }}>{title}</div>
        <div style={{ marginTop: 5, color: "#b8d2e3", fontSize: 17 }}>{subtitle}</div>
      </div>
    </div>
  );
};

const LaptopStage = ({ children, opacity }: { children: React.ReactNode, opacity: number }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const inAnim = spring({
    frame,
    fps,
    config: { damping: 200 },
    durationInFrames: Math.round(0.65 * fps),
  });

  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const screenTilt = interpolate(progress, [0, 1], [-8, 0]);
  const moveX = interpolate(progress, [0, 1], [0, 0]);
  const moveY = interpolate(progress, [0, 1], [24, -10]);

  return (
    <div
      style={{
        position: "absolute",
        left: 200,
        right: 200,
        top: 150,
        bottom: 120,
        transform: `translate(${moveX}px, ${moveY}px) scale(${interpolate(inAnim, [0, 1], [0.95, 0.88])})`,
        opacity: interpolate(inAnim, [0, 1], [0, opacity]),
        transformStyle: "preserve-3d",
        perspective: 2400,
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: 22,
          transform: `perspective(2400px) rotateX(${screenTilt}deg) translateZ(-40px)`,
          transformOrigin: "50% 100%",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 22,
            borderRadius: 18,
            overflow: "hidden",
            backgroundColor: "#000",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <div style={{ width: 1920, height: 1080, transform: "scale(0.8)", transformOrigin: "center" }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
};

const VRStage = ({ children, opacity }: { children: React.ReactNode, opacity: number }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const inAnim = spring({
    frame,
    fps,
    config: { damping: 190 },
    durationInFrames: Math.round(0.6 * fps),
  });

  const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const floatY = interpolate(progress, [0, 1], [12, -16]);
  const rotateY = interpolate(progress, [0, 1], [-10, 8]);
  const rotateX = interpolate(progress, [0, 1], [7, 3]);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transformStyle: "preserve-3d",
        perspective: 2200,
        opacity: interpolate(inAnim, [0, 1], [0, opacity]),
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          position: "absolute",
          left: 170,
          right: 170,
          top: 116,
          bottom: 120,
          borderRadius: 28,
          overflow: "hidden",
          transform: `translateY(${floatY}px) rotateY(${rotateY}deg) rotateX(${rotateX}deg)`,
          border: "1px solid rgba(172,234,255,0.4)",
          background: "linear-gradient(145deg, rgba(225,248,255,0.2), rgba(150,208,233,0.08))",
          boxShadow: "0 36px 80px rgba(0,0,0,0.45)",
          backdropFilter: "blur(10px)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div style={{ width: 1920, height: 1080, transform: "scale(0.8)", transformOrigin: "center" }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export const LearnerosPitch = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const totalDuration = 31 * fps;
  const barsIn = interpolate(frame, [0, 0.6 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const firstSceneStart = 0;
  const secondSceneStart = Math.round(3.0 * fps);
  const thirdSceneStart = Math.round(5.1 * fps);
  const fourthSceneStart = Math.round(8.2 * fps);
  const fifthSceneStart = Math.round(11.3 * fps);
  const sixthSceneStart = Math.round(14.6 * fps);
  const seventhSceneStart = Math.round(18.1 * fps);
  const eighthSceneStart = Math.round(25.2 * fps);

  const firstSceneDuration = secondSceneStart - firstSceneStart;
  const secondSceneDuration = thirdSceneStart - secondSceneStart;
  const thirdSceneDuration = fourthSceneStart - thirdSceneStart;
  const fourthSceneDuration = fifthSceneStart - fourthSceneStart;
  const fifthSceneDuration = sixthSceneStart - fifthSceneStart;
  const sixthSceneDuration = seventhSceneStart - sixthSceneStart;
  const seventhSceneDuration = eighthSceneStart - seventhSceneStart;
  const eighthSceneDuration = totalDuration - eighthSceneStart;

  const createFadeOut = (startSec: number, endSec: number) =>
    interpolate(frame, [startSec * fps, endSec * fps], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  const openingFadeOut = createFadeOut(2.7, 3.0);
  const atlasFadeOut = createFadeOut(4.8, 5.1);
  const chapterFadeOut = createFadeOut(7.9, 8.2);
  const subsectionFadeOut = createFadeOut(11.0, 11.3);
  const graphFadeOut = createFadeOut(14.3, 14.6);
  const workGraphFadeOut = createFadeOut(17.8, 18.1);
  const insightsFadeOut = createFadeOut(24.9, 25.2);

  return (
    <AbsoluteFill style={{ backgroundColor: "#020611" }}>
      {/* BACKGROUND: True WebGL 3D Room and Laptop mesh */}
      <ThreeCanvas width={width} height={height}>
        <ThreeDCenteredScenes />
      </ThreeCanvas>

      {/* FOREGROUND: HTML DOM nodes projected using CSS 3D */}

      <Sequence from={0} durationInFrames={firstSceneDuration}>
        <LaptopStage opacity={openingFadeOut}>
          <OpeningHubScene />
        </LaptopStage>
        <StoryCaption
          title="Start with intent"
          subtitle="Grade 10 transitions to Grade 11, then the card is clicked to begin."
        />
      </Sequence>

      <Sequence from={secondSceneStart} durationInFrames={secondSceneDuration}>
        <VRStage opacity={atlasFadeOut}>
          <AtlasScene />
        </VRStage>
        <StoryCaption
          title="Choose the learning domain"
          subtitle="The camera pans out: Atlas now appears floating in 3D space."
        />
      </Sequence>

      <Sequence from={thirdSceneStart} durationInFrames={thirdSceneDuration}>
        <VRStage opacity={chapterFadeOut}>
          <PhysicsChapterScene />
        </VRStage>
        <StoryCaption
          title="Focus on a chapter"
          subtitle="Work, Energy and Power is selected, then Explore is pressed to dive deeper."
        />
      </Sequence>

      <Sequence from={fourthSceneStart} durationInFrames={fourthSceneDuration}>
        <VRStage opacity={subsectionFadeOut}>
          <SubsectionViewerScene />
        </VRStage>
        <StoryCaption
          title="Pinpoint understanding"
          subtitle="The subsection opens with misconception, partial understanding, and competency insights."
        />
      </Sequence>

      <Sequence from={fifthSceneStart} durationInFrames={fifthSceneDuration}>
        <VRStage opacity={graphFadeOut}>
          <KnowledgeGraphScene />
        </VRStage>
        <StoryCaption
          title="Visualize concept structure"
          subtitle="A circular concept graph around the chapter node exposes prerequisite relationships."
        />
      </Sequence>

      <Sequence from={sixthSceneStart} durationInFrames={sixthSceneDuration}>
        <VRStage opacity={workGraphFadeOut}>
          <KnowledgeGraphWorkScene />
        </VRStage>
        <StoryCaption
          title="Interrogate a concept node"
          subtitle="Work is clicked, blinks as selected, and diagnostics update with coherent counts."
        />
      </Sequence>

      <Sequence from={seventhSceneStart} durationInFrames={seventhSceneDuration}>
        <VRStage opacity={insightsFadeOut}>
          <InsightsDashboardScene />
        </VRStage>
        <StoryCaption
          title="Turn insight into intervention"
          subtitle="Dashboard scrolls rapidly; vector explain opens an explanation card before tutor handoff."
        />
      </Sequence>

      <Sequence from={eighthSceneStart} durationInFrames={eighthSceneDuration}>
        <VRStage opacity={1}>
          <AITutorScene />
        </VRStage>
        <StoryCaption
          title="Close the loop with AI tutoring"
          subtitle="LearnerOS Tutor responds with personalized guidance grounded in matched insights and concepts."
        />
      </Sequence>

      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: interpolate(barsIn, [0, 1], [0, 42]),
          backgroundColor: "#02040a",
          zIndex: 200,
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: interpolate(barsIn, [0, 1], [0, 42]),
          backgroundColor: "#02040a",
          zIndex: 200,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
