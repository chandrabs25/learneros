import { ThreeCanvas } from "@remotion/three";
import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { ThreeDCenteredScenes } from "./ThreeDEnvironment";
import { AtlasScene } from "./AtlasScene";
import { OpeningHubScene } from "./OpeningHubScene";

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

interface VRStageProps {
  children: React.ReactNode;
  opacity: number;
  containerOpacity?: number;
  globalFrame?: number;
  totalDuration?: number;
  disableEnterAnimation?: boolean;
  flatFrameStart?: number;
  flatFrameEnd?: number;
  expandFrameStart?: number;
}

export const VRStage = ({
  children,
  opacity = 1,
  containerOpacity = 1,
  globalFrame,
  totalDuration,
  disableEnterAnimation,
  flatFrameStart,
  flatFrameEnd,
  expandFrameStart,
}: VRStageProps) => {
  const localFrame = useCurrentFrame();
  const { fps, durationInFrames: localDuration } = useVideoConfig();

  const inAnim = spring({
    frame: localFrame, // Keep enter-animation relative to scene start
    fps,
    config: { damping: 190 },
    durationInFrames: Math.round(0.6 * fps),
  });

  const activeFrame = globalFrame !== undefined ? globalFrame : localFrame;
  const t = activeFrame / fps;

  // Continuous floating and rotating using cosine waves mapped to elapsed time in seconds
  // Start identical to progress=0: floatY=12, rotateY=-10, rotateX=7
  const baseFloatY = Math.cos(t * 0.8) * 14 - 2;
  const baseRotateY = -Math.cos(t * 0.9) * 9 - 1;
  const baseRotateX = Math.cos(t * 1.0) * 2 + 5;

  // Flatten the rotation and float if flat frames are provided
  let floatY = baseFloatY;
  let rotateY = baseRotateY;
  let rotateX = baseRotateX;
  if (flatFrameStart !== undefined && flatFrameEnd !== undefined) {
    const flattenProgress = interpolate(activeFrame, [flatFrameStart, flatFrameEnd], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic)
    });
    floatY = interpolate(flattenProgress, [0, 1], [baseFloatY, 0]);
    rotateY = interpolate(flattenProgress, [0, 1], [baseRotateY, 0]);
    rotateX = interpolate(flattenProgress, [0, 1], [baseRotateX, 0]);
  }

  // Expand the stage to full screen
  let scale = 0.8;
  let insets = { left: 192, right: 192, top: 108, bottom: 108 };
  let borderRadiusOuter = 28;
  let borderRadiusInner = 36;

  if (expandFrameStart !== undefined) {
    const expandProgress = interpolate(activeFrame, [expandFrameStart, expandFrameStart + fps * 1.5], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic)
    });

    scale = interpolate(expandProgress, [0, 1], [0.8, 1]);
    insets.left = interpolate(expandProgress, [0, 1], [192, 0]);
    insets.right = interpolate(expandProgress, [0, 1], [192, 0]);
    insets.top = interpolate(expandProgress, [0, 1], [108, 0]);
    insets.bottom = interpolate(expandProgress, [0, 1], [108, 0]);
    borderRadiusOuter = interpolate(expandProgress, [0, 1], [28, 0]);
    borderRadiusInner = interpolate(expandProgress, [0, 1], [36, 0]);
  }

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        transformStyle: "preserve-3d",
        perspective: 2200,
        opacity: disableEnterAnimation ? opacity : interpolate(inAnim, [0, 1], [0, opacity]),
        pointerEvents: "none"
      }}
    >
      <div
        style={{
          position: "absolute",
          left: insets.left,
          right: insets.right,
          top: insets.top,
          bottom: insets.bottom,
          borderRadius: borderRadiusOuter,
          overflow: expandFrameStart !== undefined && activeFrame >= expandFrameStart ? "visible" : "hidden",
          transform: `translateY(${floatY}px) rotateY(${rotateY}deg) rotateX(${rotateX}deg)`,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <div
          style={{
            width: 1920,
            height: 1080,
            transform: `scale(${scale})`,
            transformOrigin: "center",
            flexShrink: 0,
            zIndex: 10,
            backgroundColor: "#ffffff",
            borderRadius: borderRadiusInner,
            boxShadow: "0 40px 100px -20px rgba(15,23,42,0.6), 0 20px 40px -20px rgba(15,23,42,0.3)",
            overflow: expandFrameStart !== undefined && activeFrame >= expandFrameStart ? "visible" : "hidden"
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
};

export const LearnerosPitch = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const totalDuration = Math.round(27.5 * fps);
  const barsIn = interpolate(frame, [0, 0.6 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const firstSceneStart = 0;
  const secondSceneStart = Math.round(2.26 * fps + 25);

  // First scene extends past the second scene start to create an overlap during the card zoom (2.26s to 3.2s)
  const firstSceneDuration = Math.round(3.2 * fps) - firstSceneStart;
  const secondSceneDuration = totalDuration - secondSceneStart;

  const createFadeOut = (startSec: number, endSec: number) =>
    interpolate(frame, [startSec * fps, endSec * fps], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  const openingFadeOut = createFadeOut(3.0, 3.2);
  const openingBrighten = interpolate(frame, [3.0 * fps, 3.2 * fps], [1, 5], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const swipeFade = interpolate(frame, [1.1 * fps, 1.45 * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#ffffff" }}>
      {/* BACKGROUND: True WebGL 3D Room and Laptop mesh */}
      <ThreeCanvas width={width} height={height}>
        <ThreeDCenteredScenes />
      </ThreeCanvas>

      {/* FOREGROUND: HTML DOM nodes projected using CSS 3D */}

      <Sequence from={0} durationInFrames={firstSceneDuration}>
        <AbsoluteFill style={{ filter: `brightness(${openingBrighten})` }}>
          <VRStage opacity={1} containerOpacity={swipeFade} globalFrame={frame} totalDuration={totalDuration}>
            <OpeningHubScene />
          </VRStage>
        </AbsoluteFill>
      </Sequence>

      <Sequence from={secondSceneStart} durationInFrames={secondSceneDuration}>
        {/* Flatten the stage as the card moves to the left (3.2s to 4.7s relative to secondSceneStart) */}
        {/* Expand the stage to fullscreen at 6.0s (3.0s relative to secondSceneStart) */}
        <VRStage
          opacity={1}
          globalFrame={frame}
          totalDuration={totalDuration}
          disableEnterAnimation={true}
          flatFrameStart={secondSceneStart + Math.round(3.0 * fps)}
          flatFrameEnd={secondSceneStart + Math.round(4.5 * fps)}
          expandFrameStart={secondSceneStart + Math.round(3.0 * fps)}
        >
          <AtlasScene />
        </VRStage>
      </Sequence>

      {/* 0.5s fade to black at the very end of the video */}
      <AbsoluteFill
        style={{
          backgroundColor: "#000000",
          opacity: interpolate(
            frame,
            [totalDuration - Math.round(0.5 * fps), totalDuration - 1],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ),
          pointerEvents: "none",
          zIndex: 9999,
        }}
      />
    </AbsoluteFill>
  );
};
