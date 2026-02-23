import React from "react";
import { AbsoluteFill, spring, interpolate, useCurrentFrame, useVideoConfig, Easing, interpolateColors } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadInter("normal", {
    weights: ["300", "400", "500", "600", "700", "800"],
    subsets: ["latin"],
});

const PrimaryTeal = "#0D9488";
const GridColor = "#e5e7eb";

export const ShortPitchMapScene: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // Entrance animations
    const centerIn = spring({
        frame,
        fps,
        config: { damping: 14, stiffness: 80, mass: 1 },
        durationInFrames: Math.round(1 * fps),
    });

    const linesIn = spring({
        frame: frame - 10,
        fps,
        config: { damping: 200 },
        durationInFrames: Math.round(1.0 * fps),
    });

    // Selection Transition Timeline (Transition happens from 1.6s to 2.2s)
    const transitionStart = Math.round(1.6 * fps);
    const transitionEnd = Math.round(2.2 * fps);

    // 1 during start, fades to 0
    const centerSelected = interpolate(frame, [transitionStart, transitionEnd], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.ease),
    });

    // 0 during start, fades to 1
    const forceSelected = interpolate(frame, [transitionStart, transitionEnd], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.inOut(Easing.ease),
    });

    const centerPulse = interpolate(frame % Math.round(2 * fps), [0, 1 * fps, 2 * fps], [1, 1.1, 1], {
        easing: Easing.inOut(Easing.ease),
    });

    const outerPulse = interpolate(frame % Math.round(2 * fps), [0, 1 * fps, 2 * fps], [0.1, 0.4, 0.1], {
        easing: Easing.inOut(Easing.ease),
    });

    const rawNodes = [
        { name: "Work" },
        { name: "Power" },
        { name: "Vectors" },
        { name: "Newton's Laws Of Motion" },
        { name: "Calculus" },
        { name: "Kinetic Energy" },
        { name: "Force" },
        { name: "Work Energy Theorem" },
        { name: "Conservative Force" },
        { name: "Momentum" },
        { name: "Energy" },
    ];

    const radius = 330;
    const nodes = rawNodes.map((n, i) => {
        const a = -Math.PI / 2 + (i / rawNodes.length) * Math.PI * 2;
        return {
            ...n,
            dx: Math.cos(a) * radius,
            dy: Math.sin(a) * radius,
            delay: 10 + i * 2.5,
        };
    });

    return (
        <AbsoluteFill
            style={{
                backgroundColor: "#f8fafc",
                fontFamily,
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
        >
            {/* Premium Background Grid */}
            <div
                style={{
                    position: "absolute",
                    inset: 0,
                    backgroundImage: `radial-gradient(circle, ${GridColor} 2px, transparent 2.5px)`,
                    backgroundSize: "36px 36px",
                    opacity: 0.6,
                }}
            />
            <div
                style={{
                    position: "absolute",
                    inset: 0,
                    background: "radial-gradient(circle at center, transparent 30%, #f8fafc 80%)",
                    pointerEvents: "none"
                }}
            />

            <div style={{ position: "relative", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>

                {/* SVG Lines */}
                <svg
                    style={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        pointerEvents: "none",
                        filter: "drop-shadow(0 0 4px rgba(13,148,136,0.3))"
                    }}
                    xmlns="http://www.w3.org/2000/svg"
                >
                    <g stroke={PrimaryTeal} strokeWidth="2.5" strokeLinecap="round">
                        {nodes.map((node, i) => {
                            const isForce = node.name === "Force";
                            const dashOffset = interpolate(linesIn, [0, 1], [1200, 0]);
                            const movingOffset = frame * 1.5;

                            // Highlight the line connecting to "Force" when it's selected
                            const baseOpacity = interpolate(linesIn, [0, 1], [0, 0.45]);
                            const lineOpacity = isForce
                                ? interpolate(forceSelected, [0, 1], [baseOpacity, 0.9])
                                : baseOpacity;

                            const lineThickness = isForce
                                ? interpolate(forceSelected, [0, 1], [2.5, 4.0])
                                : 2.5;

                            return (
                                <line
                                    key={i}
                                    x1="50%"
                                    y1="50%"
                                    x2={`calc(50% + ${node.dx}px)`}
                                    y2={`calc(50% + ${node.dy}px)`}
                                    strokeWidth={lineThickness}
                                    strokeDasharray="16 12"
                                    strokeDashoffset={dashOffset - movingOffset}
                                    opacity={lineOpacity}
                                />
                            )
                        })}
                    </g>
                </svg>

                {/* Ambient Floating Dust */}
                {[
                    { x: 120, y: -90, s: 6 }, { x: 200, y: -160, s: 10 }, { x: 280, y: -70, s: 5 },
                    { x: 180, y: 120, s: 8 }, { x: -90, y: 140, s: 12 }, { x: -140, y: -80, s: 7 },
                    { x: 0, y: -220, s: 9 }, { x: -20, y: 220, s: 6 }, { x: 100, y: 300, s: 11 }
                ].map((pos, i) => {
                    const moveY = Math.sin(frame / 40 + pos.x) * 15;
                    return (
                        <div
                            key={i}
                            style={{
                                position: "absolute",
                                width: pos.s,
                                height: pos.s,
                                backgroundColor: PrimaryTeal,
                                borderRadius: "50%",
                                opacity: interpolate(linesIn, [0, 1], [0, 0.3]),
                                transform: `translate(${pos.x}px, ${pos.y + moveY}px)`,
                                boxShadow: "0 0 10px rgba(13,148,136,0.5)"
                            }}
                        />
                    );
                })}

                {/* Surrounding Nodes */}
                {nodes.map((node) => {
                    const nodeIn = spring({
                        frame: frame - node.delay,
                        fps,
                        config: { damping: 15, mass: 1.2, stiffness: 90 },
                        durationInFrames: Math.round(0.6 * fps),
                    });

                    const isForce = node.name === "Force";
                    const sel = isForce ? forceSelected : 0;

                    const bubbleSize = interpolate(sel, [0, 1], [62, 74]);
                    const bubbleBorder = interpolate(sel, [0, 1], [1.5, 3]);
                    const bubbleBorderColor = interpolateColors(sel, [0, 1], ["#cbd5e1", PrimaryTeal]);

                    const iconColor = interpolateColors(sel, [0, 1], ["#64748b", PrimaryTeal]);
                    const iconSize = interpolate(sel, [0, 1], [26, 34]);

                    const labelTop = interpolate(sel, [0, 1], [40, 46]);
                    const labelBg = interpolateColors(sel, [0, 1], ["rgba(255,255,255,0.95)", "#0f172a"]);
                    const labelColor = interpolateColors(sel, [0, 1], ["#1e293b", "#ffffff"]);
                    const labelBorder = interpolateColors(sel, [0, 1], ["rgba(226,232,240,1)", "rgba(255,255,255,0.1)"]);
                    const labelSize = interpolate(sel, [0, 1], [10, 11]);
                    const labelSpacing = interpolate(sel, [0, 1], [0.5, 1.5]);

                    return (
                        <div
                            key={node.name}
                            style={{
                                position: "absolute",
                                left: `calc(50% + ${node.dx}px)`,
                                top: `calc(50% + ${node.dy}px)`,
                                transform: `scale(${interpolate(nodeIn, [0, 1], [0.01, 1])})`,
                                opacity: interpolate(nodeIn, [0, 0.2], [0, 1]),
                                zIndex: isForce ? Math.round(interpolate(sel, [0, 1], [10, 50])) : 10,
                            }}
                        >
                            <div
                                style={{
                                    position: "absolute",
                                    left: 0,
                                    top: 0,
                                    transform: "translate(-50%, -50%)",
                                    width: bubbleSize,
                                    height: bubbleSize,
                                    backgroundColor: "rgba(255,255,255,0.9)",
                                    backdropFilter: "blur(8px)",
                                    borderRadius: "50%",
                                    border: `${bubbleBorder}px solid ${bubbleBorderColor}`,
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    boxShadow: isForce
                                        ? `0 15px 35px -5px rgba(13,148,136,${interpolate(sel, [0, 1], [0.12, 0.4])}), inset 0 2px 5px rgba(255,255,255,0.5)`
                                        : "0 8px 20px -5px rgba(15,23,42,0.12), inset 0 2px 4px rgba(255,255,255,0.5)",
                                }}
                            >
                                <span style={{
                                    color: iconColor,
                                    fontSize: iconSize,
                                    textShadow: isForce ? `0 2px 6px rgba(13,148,136,${interpolate(sel, [0, 1], [0, 0.3])})` : "none"
                                }}>
                                    ⚗
                                </span>

                                {/* Ping ring for selected node */}
                                {isForce && (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            inset: -4,
                                            borderRadius: '50%',
                                            border: `2px solid ${PrimaryTeal}`,
                                            opacity: outerPulse * sel,
                                            transform: `scale(${1 + (outerPulse * sel)})`,
                                        }}
                                    />
                                )}
                            </div>

                            <div
                                style={{
                                    position: "absolute",
                                    left: 0,
                                    top: labelTop,
                                    transform: "translateX(-50%)",
                                    padding: "5px 14px",
                                    backgroundColor: labelBg,
                                    backdropFilter: "blur(4px)",
                                    color: labelColor,
                                    border: `1.5px solid ${labelBorder}`,
                                    fontSize: labelSize,
                                    fontWeight: 700,
                                    borderRadius: 8,
                                    boxShadow: isForce ? `0 10px 20px rgba(15,23,42,${interpolate(sel, [0, 1], [0.06, 0.3])})` : "0 4px 10px rgba(15,23,42,0.06)",
                                    whiteSpace: "nowrap",
                                    textTransform: isForce && sel > 0.5 ? "uppercase" : "none", // Swap text transform halfway
                                    letterSpacing: labelSpacing,
                                }}
                            >
                                {node.name}
                            </div>
                        </div>
                    );
                })}

                {/* Center Node Selected Glow Ring */}
                <div
                    style={{
                        position: "absolute",
                        width: 172,
                        height: 172,
                        borderRadius: "50%",
                        backgroundColor: PrimaryTeal,
                        // Scale opacity by centerSelected
                        opacity: interpolate(centerIn, [0, 1], [0, 0.15]) * (centerPulse * 0.8) * centerSelected,
                        transform: `scale(${interpolate(centerIn, [0, 1], [0.5, 1]) * centerPulse})`,
                        filter: "blur(12px)",
                        zIndex: 5,
                    }}
                />

                <div
                    style={{
                        position: "absolute",
                        width: 190,
                        height: 190,
                        borderRadius: "50%",
                        border: `2px solid ${PrimaryTeal}`,
                        // Scale opacity by centerSelected
                        opacity: interpolate(centerIn, [0, 1], [0, outerPulse]) * centerSelected,
                        transform: `scale(${interpolate(centerIn, [0, 1], [0.5, 1]) * (1 + outerPulse)})`,
                        zIndex: 5,
                    }}
                />

                {/* Center Node */}
                <div
                    style={{
                        position: "relative",
                        zIndex: 10,
                        transform: `scale(${interpolate(centerIn, [0, 1], [0.01, 1])})`,
                        opacity: centerIn,
                    }}
                >
                    <div
                        style={{
                            width: 156,
                            height: 156,
                            backgroundColor: "rgba(255,255,255,0.95)",
                            backdropFilter: "blur(12px)",
                            borderRadius: "50%",
                            border: `${interpolate(centerSelected, [0, 1], [1.5, 3])}px solid ${interpolateColors(centerSelected, [0, 1], ["#cbd5e1", PrimaryTeal])}`,
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            justifyContent: "center",
                            boxShadow: `0 30px 60px -15px rgba(13,148,136, ${interpolate(centerSelected, [0, 1], [0.1, 0.25])}), 0 0 0 8px rgba(13,148,136, ${interpolate(centerSelected, [0, 1], [0, 0.1])})`,
                            padding: 24,
                            textAlign: "center",
                        }}
                    >
                        <span style={{
                            fontSize: 44,
                            marginBottom: 10,
                            filter: `drop-shadow(0 4px 8px rgba(13,148,136,${interpolate(centerSelected, [0, 1], [0.1, 0.3])}))`
                        }}>
                            💡
                        </span>
                        <div style={{ fontSize: 13, fontWeight: 800, lineHeight: 1.15, textTransform: "uppercase", letterSpacing: 0.5, color: "#0f172a" }}>
                            Work, Energy <br />and Power
                        </div>
                        <div style={{
                            fontSize: 10,
                            color: interpolateColors(centerSelected, [0, 1], ["#64748b", PrimaryTeal]),
                            fontWeight: 800,
                            marginTop: 6,
                            letterSpacing: 2,
                            padding: "3px 8px",
                            backgroundColor: interpolateColors(centerSelected, [0, 1], ["rgba(203,213,225,0.3)", "rgba(13,148,136,0.1)"]),
                            borderRadius: 6
                        }}>
                            CHAPTER 5
                        </div>
                    </div>
                </div>

            </div>
        </AbsoluteFill>
    );
};
