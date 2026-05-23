"use client";

import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";

type StudentMapPoint = {
  student_id: string;
  name: string;
  x: number;
  y: number;
  z: number;
  risk_band: "LOW" | "MEDIUM" | "HIGH";
};

function riskColor(risk: string) {
  if (risk === "HIGH") return "#ef4444";
  if (risk === "MEDIUM") return "#facc15";
  return "#22c55e";
}

export default function StudentEmbeddingMap3D({ students }: { students: StudentMapPoint[] }) {
  return (
    <Canvas camera={{ position: [4.8, 4.2, 6], fov: 48 }} style={{ height: 420, width: "100%" }}>
      <color attach="background" args={["#f8fafc"]} />
      <ambientLight intensity={0.75} />
      <directionalLight position={[4, 6, 4]} intensity={1.1} />
      <gridHelper args={[8, 8, "#cbd5e1", "#e2e8f0"]} />
      <axesHelper args={[4.2]} />
      {students.map((student) => {
        const pos: [number, number, number] = [student.x * 3.2, student.y * 3.2, student.z * 3.2];
        const color = riskColor(student.risk_band);
        return (
          <group key={student.student_id} position={pos}>
            <mesh>
              <sphereGeometry args={[0.13, 24, 24]} />
              <meshStandardMaterial color={color} roughness={0.45} metalness={0.05} />
            </mesh>
            <Html position={[0, 0.24, 0]} center distanceFactor={8}>
              <div
                style={{
                  background: "rgba(255,255,255,0.92)",
                  border: "1px solid #e2e8f0",
                  borderRadius: 999,
                  color: "#0f172a",
                  fontSize: 10,
                  fontWeight: 800,
                  padding: "2px 7px",
                  whiteSpace: "nowrap",
                  boxShadow: "0 6px 16px rgba(15,23,42,0.08)",
                }}
              >
                {student.name}
              </div>
            </Html>
          </group>
        );
      })}
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
    </Canvas>
  );
}
