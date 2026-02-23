import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { ShortPitchMapScene } from "./scenes/ShortPitchMapScene";
import { ShortPitchInsightsScene } from "./scenes/ShortPitchInsightsScene";

export const ShortPitch = () => {
    const { fps } = useVideoConfig();

    // Scene 1: The Global Map (0:00 - 0:03)
    // Scene 2: Actionable Insights (0:03 - 0:09)
    // ...

    const firstSceneDuration = 3 * fps;
    const secondSceneDuration = 6 * fps;

    return (
        <AbsoluteFill style={{ backgroundColor: "#020611" }}>
            <Sequence from={0} durationInFrames={firstSceneDuration + secondSceneDuration}>
                <ShortPitchMapScene />
            </Sequence>
            <Sequence from={firstSceneDuration} durationInFrames={secondSceneDuration}>
                <ShortPitchInsightsScene />
            </Sequence>
        </AbsoluteFill>
    );
};
