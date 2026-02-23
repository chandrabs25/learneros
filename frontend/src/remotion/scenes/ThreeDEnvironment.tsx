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

const LaptopMesh = () => {
    return (
        <group position={[0, -0.2, 0]}>
            {/* Base */}
            <mesh position={[0, -0.05, 0.6]}>
                <boxGeometry args={[3.2, 0.1, 2.2]} />
                <meshStandardMaterial color="#3b4a5a" metalness={0.6} roughness={0.3} />
            </mesh>
            {/* Keyboard area illusion */}
            <mesh position={[0, 0.005, 0.5]}>
                <boxGeometry args={[2.9, 0.01, 1.2]} />
                <meshStandardMaterial color="#1a202c" />
            </mesh>

            {/* Screen Hinge */}
            <mesh position={[0, 1, -0.45]} rotation={[-0.1, 0, 0]}>
                <boxGeometry args={[3.2, 2.1, 0.1]} />
                <meshStandardMaterial color="#2d3748" metalness={0.5} roughness={0.4} />
            </mesh>

            {/* Screen Glow (to fake screen light inside 3D) */}
            <mesh position={[0, 1, -0.39]} rotation={[-0.1, 0, 0]}>
                <boxGeometry args={[3.0, 1.9, 0.05]} />
                <meshBasicMaterial color="#d4f1f9" />
            </mesh>
        </group>
    );
};

const RoomEnvironment = () => {
    return (
        <group>
            <ambientLight intensity={1.8} />
            <directionalLight position={[5, 10, 5]} intensity={2.5} castShadow color="#cce6ff" />
            <pointLight position={[-5, 5, -5]} intensity={2.0} color="#4fa4ff" />
            <pointLight position={[0, 2, 2]} intensity={1.5} color="#ffffff" />

            {/* Floor with Grid to sell the 3D space */}
            <group position={[0, -0.8, 0]}>
                <mesh rotation={[-Math.PI / 2, 0, 0]}>
                    <planeGeometry args={[100, 100]} />
                    <meshStandardMaterial color="#112233" roughness={0.6} metalness={0.2} />
                </mesh>
                <gridHelper args={[100, 100, "#2c4f6b", "#162f45"]} position={[0, 0.01, 0]} />
            </group>

            {/* Background walls */}
            <mesh position={[0, 10, -10]}>
                <planeGeometry args={[100, 40]} />
                <meshStandardMaterial color="#0c1724" roughness={0.9} />
            </mesh>
        </group>
    );
};

export const ThreeDCenteredScenes = () => {
    return (
        <group>
            <RoomEnvironment />
            <CameraController />
            <LaptopMesh />
        </group>
    );
};
