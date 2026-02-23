import { Composition } from "remotion";
import { LearnerosPitch } from "./scenes/LearnerosPitch";
import { ShortPitch } from "./ShortPitch";

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="LearnerosPitch"
        component={LearnerosPitch}
        durationInFrames={31 * 30}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="ShortPitch"
        component={ShortPitch}
        durationInFrames={20 * 30}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
