"use client";

import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Types ───────────────────────────────────────────────────────── */

interface ConceptPosition {
  id: string;
  name: string;
  x: number;
  y: number;
  z: number;
  chapter_ids: string[];
  subject: string | null;
}

interface InsightOverlay {
  [conceptId: string]: "COMPETENCY" | "PARTIAL_UNDERSTANDING" | "MISCONCEPTION";
}

interface InsightsGraphProps {
  token: string | null;
  onConceptClick?: (conceptId: string) => void;
}

/* ─── Colors ──────────────────────────────────────────────────────── */

const INSIGHT_COLORS: Record<string, string> = {
  COMPETENCY: "#10b981",
  PARTIAL_UNDERSTANDING: "#f59e0b",
  MISCONCEPTION: "#ef4444",
};

const DEFAULT_COLOR = "#94a3b8"; // grey for unassessed
const SPHERE_RADIUS = 4.2;

/* ─── Concept Points (instanced for perf) ─────────────────────────── */

function ConceptNodes({
  concepts,
  insightOverlay,
  onHover,
  onClick,
}: {
  concepts: ConceptPosition[];
  insightOverlay: InsightOverlay;
  onHover: (index: number | null) => void;
  onClick: (index: number) => void;
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const tempObject = useMemo(() => new THREE.Object3D(), []);
  const tempColor = useMemo(() => new THREE.Color(), []);

  // Set positions + colors
  useEffect(() => {
    if (!meshRef.current) return;

    const colorArray = new Float32Array(concepts.length * 3);

    concepts.forEach((c, i) => {
      tempObject.position.set(
        c.x * SPHERE_RADIUS,
        c.y * SPHERE_RADIUS,
        c.z * SPHERE_RADIUS
      );
      tempObject.scale.setScalar(1);
      tempObject.updateMatrix();
      meshRef.current!.setMatrixAt(i, tempObject.matrix);

      const insightType = insightOverlay[c.id];
      const hex = insightType ? INSIGHT_COLORS[insightType] || DEFAULT_COLOR : DEFAULT_COLOR;
      tempColor.set(hex);
      colorArray[i * 3] = tempColor.r;
      colorArray[i * 3 + 1] = tempColor.g;
      colorArray[i * 3 + 2] = tempColor.b;
    });

    meshRef.current.instanceMatrix.needsUpdate = true;
    meshRef.current.geometry.setAttribute(
      "color",
      new THREE.InstancedBufferAttribute(colorArray, 3)
    );
  }, [concepts, insightOverlay, tempObject, tempColor]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, concepts.length]}
      onPointerMove={(e) => {
        e.stopPropagation();
        if (e.instanceId !== undefined) onHover(e.instanceId);
      }}
      onPointerLeave={() => onHover(null)}
      onClick={(e) => {
        e.stopPropagation();
        if (e.instanceId !== undefined) onClick(e.instanceId);
      }}
    >
      <sphereGeometry args={[0.06, 12, 12]} />
      <meshStandardMaterial vertexColors toneMapped={false} />
    </instancedMesh>
  );
}

/* ─── Wireframe Sphere Shell ──────────────────────────────────────── */

function SphereShell() {
  return (
    <mesh>
      <sphereGeometry args={[SPHERE_RADIUS + 0.02, 32, 32]} />
      <meshBasicMaterial
        color="#e2e8f0"
        wireframe
        transparent
        opacity={0.08}
      />
    </mesh>
  );
}

/* ─── Gentle auto-rotate ──────────────────────────────────────────── */

function AutoRotate({ enabled }: { enabled: boolean }) {
  const { scene } = useThree();
  useFrame((_, delta) => {
    if (enabled) {
      scene.rotation.y += delta * 0.08;
    }
  });
  return null;
}

/* ─── Tooltip ─────────────────────────────────────────────────────── */

function Tooltip({
  concept,
  insightType,
}: {
  concept: ConceptPosition;
  insightType?: string;
}) {
  const prettyName = concept.name.replace(/_/g, " ");
  const dotColor = insightType ? INSIGHT_COLORS[insightType] || DEFAULT_COLOR : DEFAULT_COLOR;
  const typeLabel = insightType
    ? insightType.replace(/_/g, " ")
    : "Not assessed";

  return (
    <Html
      position={[
        concept.x * SPHERE_RADIUS,
        concept.y * SPHERE_RADIUS + 0.25,
        concept.z * SPHERE_RADIUS,
      ]}
      center
      style={{ pointerEvents: "none" }}
    >
      <div
        style={{
          background: "#fff",
          border: "1px solid #e2e8f0",
          borderRadius: 10,
          padding: "6px 10px",
          boxShadow: "0 4px 16px rgba(0,0,0,0.10)",
          whiteSpace: "nowrap",
          minWidth: 100,
        }}
      >
        <div
          style={{
            fontSize: "0.78rem",
            fontWeight: 700,
            color: "#0f172a",
            marginBottom: 2,
          }}
        >
          {prettyName}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: dotColor,
              display: "inline-block",
            }}
          />
          <span
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              color: "#64748b",
              textTransform: "capitalize",
            }}
          >
            {typeLabel}
          </span>
        </div>
        {concept.subject && (
          <div
            style={{
              fontSize: "0.6rem",
              color: "#94a3b8",
              marginTop: 2,
            }}
          >
            {concept.subject}
          </div>
        )}
      </div>
    </Html>
  );
}

/* ─── Main Component ──────────────────────────────────────────────── */

export default function InsightsGraph({ token, onConceptClick }: InsightsGraphProps) {
  const [concepts, setConcepts] = useState<ConceptPosition[]>([]);
  const [insightOverlay, setInsightOverlay] = useState<InsightOverlay>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [autoRotate, setAutoRotate] = useState(true);

  const stats = useMemo(() => {
    const total = concepts.length;
    const withInsights = Object.keys(insightOverlay).length;
    return { total, withInsights };
  }, [concepts, insightOverlay]);

  // 1. Load static positions
  useEffect(() => {
    setLoading(true);
    fetch("/concept-positions.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setConcepts(data.concepts || []);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load positions.");
        setLoading(false);
      });
  }, []);

  // 2. Load dynamic insight overlay
  useEffect(() => {
    if (!token) return;

    fetch(`${API_URL}/api/students/me/insights`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (!Array.isArray(data)) return;
        const overlay: InsightOverlay = {};
        for (const ins of data) {
          const cid = ins.concept_id;
          if (!cid) continue;
          // Priority: MISCONCEPTION > PARTIAL > COMPETENCY
          const existing = overlay[cid];
          if (!existing) {
            overlay[cid] = ins.type;
          } else if (ins.type === "MISCONCEPTION") {
            overlay[cid] = "MISCONCEPTION";
          } else if (ins.type === "PARTIAL_UNDERSTANDING" && existing !== "MISCONCEPTION") {
            overlay[cid] = "PARTIAL_UNDERSTANDING";
          }
        }
        setInsightOverlay(overlay);
      })
      .catch(() => {});
  }, [token]);

  const handleHover = useCallback(
    (index: number | null) => {
      setHoveredIndex(index);
      setAutoRotate(index === null);
    },
    []
  );

  const handleClick = useCallback(
    (index: number) => {
      const c = concepts[index];
      if (c && onConceptClick) onConceptClick(c.id);
    },
    [concepts, onConceptClick]
  );

  const hoveredConcept = hoveredIndex !== null ? concepts[hoveredIndex] : null;

  return (
    <div
      style={{
        background: "#f8fafb",
        borderRadius: 20,
        overflow: "hidden",
        marginBottom: "2rem",
        border: "1px solid #e2e8f0",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1rem 1.25rem 0.5rem",
          flexWrap: "wrap",
          gap: "0.5rem",
        }}
      >
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: "1.25rem",
              fontWeight: 800,
              color: "#0f172a",
              letterSpacing: "-0.02em",
            }}
          >
            <span
              className="material-symbols-outlined"
              style={{ fontSize: 20, verticalAlign: "middle", marginRight: 6, color: "#13ecda" }}
            >
              hub
            </span>
            Knowledge Graph
          </h2>
          <p style={{ margin: "0.2rem 0 0", fontSize: "0.78rem", color: "#64748b" }}>
            465 concepts in 3D semantic space • Hover to inspect, click to scroll
          </p>
        </div>

        {!loading && !error && (
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <LegendDot color={DEFAULT_COLOR} label={`${stats.total - stats.withInsights} Not assessed`} />
            <LegendDot color="#10b981" label="Competency" />
            <LegendDot color="#f59e0b" label="Partial" />
            <LegendDot color="#ef4444" label="Misconception" />
          </div>
        )}
      </div>

      {/* 3D Canvas */}
      <div style={{ width: "100%", height: 500, position: "relative", cursor: "grab" }}>
        {loading ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#64748b", fontSize: "0.9rem", fontWeight: 600 }}>
            Loading concept sphere…
          </div>
        ) : error ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#ef4444", fontSize: "0.9rem", fontWeight: 600 }}>
            {error}
          </div>
        ) : (
          <Canvas camera={{ position: [0, 0, 10], fov: 50 }} style={{ background: "#f8fafb" }}>
            <ambientLight intensity={0.8} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <pointLight position={[-10, -5, -10]} intensity={0.4} />

            <SphereShell />
            <ConceptNodes
              concepts={concepts}
              insightOverlay={insightOverlay}
              onHover={handleHover}
              onClick={handleClick}
            />

            {hoveredConcept && (
              <Tooltip
                concept={hoveredConcept}
                insightType={insightOverlay[hoveredConcept.id]}
              />
            )}

            <AutoRotate enabled={autoRotate} />
            <OrbitControls
              enablePan={false}
              minDistance={6}
              maxDistance={18}
              enableDamping
              dampingFactor={0.05}
            />
          </Canvas>
        )}
      </div>

      {/* Stats bar */}
      {!loading && !error && (
        <div
          style={{
            display: "flex",
            justifyContent: "center",
            gap: "2rem",
            padding: "0.6rem 1.25rem 0.8rem",
            borderTop: "1px solid #e2e8f0",
          }}
        >
          <Stat label="Concepts" value={stats.total} />
          <Stat label="With Insights" value={stats.withInsights} />
        </div>
      )}
    </div>
  );
}

/* ─── Small Components ────────────────────────────────────────────── */

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div style={{ textAlign: "center" }}>
      <p style={{ margin: 0, fontSize: "1.5rem", fontWeight: 900, color: "#0f172a" }}>{value}</p>
      <p style={{ margin: 0, fontSize: "0.68rem", color: "#64748b", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
        {label}
      </p>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      <span style={{ fontSize: "0.68rem", color: "#94a3b8", fontWeight: 600 }}>
        {label}
      </span>
    </div>
  );
}
