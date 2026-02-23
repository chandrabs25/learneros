import { PerspectiveCamera } from "@react-three/drei";
import { useCurrentFrame, useVideoConfig } from "remotion";
import * as THREE from "three";

export const CameraController = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Story beats:
    // 0s - 3s: Laptop scene. Camera focuses on the laptop screen.
    // 3s - 5.1s: AtlasScene. Camera pulls back and up.
    // 5.1s - 8.2s: PhysicsChapterScene. Camera pans slightly right.
    // ... and so on.

    // Let's create a smooth camera path.
    const startPos = new THREE.Vector3(0, 1.2, 3);
    const laptopScreenPos = new THREE.Vector3(0, 1, 0);

    const floatPos = new THREE.Vector3(0, 2, 6);
    const floatLookAt = new THREE.Vector3(0, 2, 0);

    // Calculate progress
    // Wait, let's use a simpler approach.
    const progress = Math.min(1, Math.max(0, (frame - 2 * fps) / (2 * fps)));

    // Eased progress (cubic ease in out)
    const easeInOut = (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const easedProgress = easeInOut(progress);

    const currentPos = startPos.clone().lerp(floatPos, easedProgress);
    const currentLookAt = laptopScreenPos.clone().lerp(floatLookAt, easedProgress);

    return (
        <PerspectiveCamera
            makeDefault
            position={[currentPos.x, currentPos.y, currentPos.z]}
            onUpdate={(c) => c.lookAt(currentLookAt.x, currentLookAt.y, currentLookAt.z)}
            fov={45}
        />
    );
};
