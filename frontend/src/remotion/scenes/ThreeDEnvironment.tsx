import { PerspectiveCamera } from "@react-three/drei";
import { useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";

export const CameraController = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const laptopCamPos = new THREE.Vector3(0, 1.4, 2.8);
    const laptopLookAt = new THREE.Vector3(0, 0.9, 0);

    const roomCamPos = new THREE.Vector3(0, 2, 7);
    const roomLookAt = new THREE.Vector3(0, 2, 0);

    const transitionStart = 2.8 * fps;
    const transitionEnd = 4 * fps;

    // Remotion interpolate isn't ideal for Vector3 without manual math, 
    // so we'll use a simple ease function
    const rawProgress = (frame - transitionStart) / (transitionEnd - transitionStart);
    const progress = Math.max(0, Math.min(1, rawProgress));

    const eased = progress < 0.5 ? 4 * progress * progress * progress : 1 - Math.pow(-2 * progress + 2, 3) / 2;

    const currentPos = laptopCamPos.clone().lerp(roomCamPos, eased);
    const currentLookAt = laptopLookAt.clone().lerp(roomLookAt, eased);

    // Syncing a floating pan with the HTML VRStage
    // The HTML VRStage uses: `const floatY = interpolate(progress, [0, 1], [12, -16]);`
    // We want the camera to look at the center of the room and slightly drift to feel alive
    if (frame > transitionEnd) {
        const floatProgress = (frame - transitionEnd) / (30 * fps - transitionEnd);
        currentPos.x += Math.sin(floatProgress * 2) * 1.5;
        currentLookAt.x += Math.sin(floatProgress * 2) * 0.5;
        currentPos.y += Math.cos(floatProgress * 3) * 0.2;
    }

    return (
        <PerspectiveCamera
            makeDefault
            position={[currentPos.x, currentPos.y, currentPos.z]}
            onUpdate={(c) => c.lookAt(currentLookAt.x, currentLookAt.y, currentLookAt.z)}
            fov={45}
        />
    );
};



const RoomEnvironment = () => {
    return (
        <group>
            {/* Sets the entire 3D WebGL Canvas background to a darker off-white (slate-200) */}
            <color attach="background" args={["#e2e8f0"]} />

            {/* Bright, even lighting so any floating elements stay bright */}
            <ambientLight intensity={3.0} />
            <directionalLight position={[0, 10, 5]} intensity={1.5} color="#ffffff" />
        </group>
    );
};

export const ThreeDCenteredScenes = () => {
    return (
        <group>
            <RoomEnvironment />
            <CameraController />
        </group>
    );
};
