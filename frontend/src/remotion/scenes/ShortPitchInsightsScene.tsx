import React from "react";
import { AbsoluteFill, spring, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

const { fontFamily } = loadInter("normal", {
    weights: ["300", "400", "500", "600", "700", "800"],
    subsets: ["latin"],
});

export const ShortPitchInsightsScene: React.FC = () => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    // The scene duration is expected to be ~7 seconds (210 frames)

    // Animate the main card sliding up and fading in
    const cardEntrance = spring({
        frame,
        fps,
        config: { damping: 14, stiffness: 80, mass: 1 },
        durationInFrames: Math.round(0.8 * fps),
    });

    const fadeBg = interpolate(cardEntrance, [0, 0.5], [0, 0.9], {
        extrapolateRight: "clamp",
    });

    const cardOpacity = interpolate(cardEntrance, [0, 1], [0, 1]);
    const cardTranslateY = interpolate(cardEntrance, [0, 1], [60, 0]);

    // Animate the scrolling of the insights
    // We scroll up by 750px after 1.2 seconds over a 4.5-second period
    const scrollAmount = spring({
        frame: frame - Math.round(1.2 * fps),
        fps,
        config: { damping: 200 },
        durationInFrames: Math.round(4.5 * fps),
    });
    const scrollTranslateY = interpolate(scrollAmount, [0, 1], [0, -780]);

    // SVG Icons
    const CloseIcon = () => (
        <svg fill="currentColor" viewBox="0 0 24 24" width="20" height="20">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
        </svg>
    );

    const AwesomeIcon = () => (
        <svg fill="currentColor" viewBox="0 0 24 24" width="18" height="18">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-8 14l-2.5-5.5L3 9l5.5-2.5L11 1l2.5 5.5L19 9l-5.5 2.5L11 17z" />
        </svg>
    );

    const HelpIcon = () => (
        <svg fill="currentColor" viewBox="0 0 24 24" width="14" height="14">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z" />
        </svg>
    );

    const CheckCircleIcon = () => (
        <svg fill="currentColor" viewBox="0 0 24 24" width="14" height="14">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
        </svg>
    );

    return (
        <AbsoluteFill style={{ fontFamily, display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>

            {/* Dark background fade overlay */}
            <div style={{ position: "absolute", inset: 0, backgroundColor: `rgba(2, 6, 17, ${fadeBg})` }} />

            <div
                style={{
                    width: "100%",
                    maxWidth: 520,
                    backgroundColor: "white",
                    border: "1px solid #e2e8f0",
                    borderRadius: 24,
                    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
                    overflow: "hidden",
                    display: "flex",
                    flexDirection: "column",
                    height: 700,
                    opacity: cardOpacity,
                    transform: `scale(${interpolate(cardEntrance, [0, 1], [0.95, 1])}) translateY(${cardTranslateY}px)`,
                }}
            >
                {/* Header Section (Sticky) */}
                <div style={{ padding: "32px 32px 16px 32px", zIndex: 20, backgroundColor: "white", boxShadow: "0 10px 15px -10px rgba(0,0,0,0.05)" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                            <span style={{ padding: "2px 8px", backgroundColor: "black", color: "white", fontSize: 9, fontWeight: 700, borderRadius: 4, letterSpacing: 1.5 }}>INSIGHTS</span>
                            <h2 style={{ fontWeight: 700, color: "#1e293b", fontSize: 16 }}>Node Profile</h2>
                        </div>
                        <div style={{ width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", backgroundColor: "#f1f5f9", color: "#94a3b8" }}>
                            <CloseIcon />
                        </div>
                    </div>

                    <div style={{ marginBottom: 32 }}>
                        <h1 style={{ fontSize: 36, fontWeight: 800, color: "#0f172a", marginBottom: 4, letterSpacing: "-0.02em" }}>Force</h1>
                        <p style={{ fontSize: 10, fontWeight: 700, color: "#14B8A6", letterSpacing: 2, textTransform: "uppercase" }}>Cross-Chapter Analysis</p>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 16 }}>
                        <div style={{ backgroundColor: "rgba(236, 253, 245, 0.5)", border: "1px solid #d1fae5", padding: 16, borderRadius: 12 }}>
                            <p style={{ fontSize: 8, fontWeight: 700, color: "#059669", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" }}>Competency</p>
                            <span style={{ fontSize: 30, fontWeight: 700, color: "#059669" }}>3</span>
                        </div>
                        <div style={{ backgroundColor: "rgba(255, 237, 213, 0.5)", border: "1px solid #ffedd5", padding: 16, borderRadius: 12 }}>
                            <p style={{ fontSize: 8, fontWeight: 700, color: "#ea580c", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" }}>Partial</p>
                            <span style={{ fontSize: 30, fontWeight: 700, color: "#ea580c" }}>3</span>
                        </div>
                        <div style={{ backgroundColor: "rgba(254, 242, 242, 0.5)", border: "1px solid #fee2e2", padding: 16, borderRadius: 12 }}>
                            <p style={{ fontSize: 8, fontWeight: 700, color: "#dc2626", letterSpacing: 1.5, marginBottom: 8, textTransform: "uppercase" }}>Misconception</p>
                            <span style={{ fontSize: 30, fontWeight: 700, color: "#dc2626" }}>4</span>
                        </div>
                    </div>
                </div>

                {/* Scrollable Content Section */}
                <div style={{ flex: 1, padding: "0 32px 32px 32px", overflow: "hidden", position: "relative" }}>

                    {/* The scrolling wrapper */}
                    <div style={{ transform: `translateY(${scrollTranslateY}px)` }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, paddingTop: 16, marginTop: 16, borderTop: "1px solid #f1f5f9", marginBottom: 24 }}>
                            <div style={{ color: "#14B8A6" }}>
                                <AwesomeIcon />
                            </div>
                            <h3 style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, color: "#1e293b", textTransform: "uppercase" }}>Learning Insights</h3>
                        </div>

                        {/* Chapter 4 block */}
                        <div style={{ marginBottom: 40 }}>
                            <div style={{ marginBottom: 24 }}>
                                <h4 style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Chapter 4: Laws of Motion</h4>
                            </div>
                            <div style={{ paddingLeft: 16, borderLeft: "2px solid #fb923c", backgroundColor: "#f8fafc", padding: 24, borderRadius: "0 12px 12px 0", position: "relative" }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        <div style={{ color: "#fb923c" }}>
                                            <HelpIcon />
                                        </div>
                                        <span style={{ fontSize: 9, fontWeight: 700, color: "#fb923c", letterSpacing: 1.5, textTransform: "uppercase" }}>Partial Understanding</span>
                                    </div>
                                    <span style={{ fontSize: 8, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Newtonian Dynamics</span>
                                </div>
                                <p style={{ fontSize: 13, lineHeight: 1.6, color: "#475569" }}>
                                    Student correctly identifies the net force in static equilibrium scenarios but fails to apply Newton's Second Law when acceleration is non-zero. They tend to equate 'Force' with 'Velocity', assuming that a constant force is required to maintain constant motion rather than to change it. This indicates a strong grasp of vector addition but a fundamental gap in the relationship between force and inertia.
                                </p>
                            </div>
                        </div>

                        {/* Divider */}
                        <div style={{ width: "100%", height: 1, backgroundColor: "#f1f5f9", margin: "32px 0" }} />

                        {/* Chapter 5 block */}
                        <div style={{ marginBottom: 24 }}>
                            <div style={{ marginBottom: 24 }}>
                                <h4 style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Chapter 5: Work, Energy and Power</h4>
                            </div>
                            <div style={{ paddingLeft: 16, borderLeft: "2px solid #34d399", backgroundColor: "#f8fafc", padding: 24, borderRadius: "0 12px 12px 0", position: "relative" }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        <div style={{ color: "#10b981" }}>
                                            <CheckCircleIcon />
                                        </div>
                                        <span style={{ fontSize: 9, fontWeight: 700, color: "#10b981", letterSpacing: 1.5, textTransform: "uppercase" }}>Competency</span>
                                    </div>
                                    <span style={{ fontSize: 8, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Work-Energy Theorem</span>
                                </div>
                                <p style={{ fontSize: 13, lineHeight: 1.6, color: "#475569" }}>
                                    Excellent proficiency in calculating work done by variable forces using integral calculus. The student demonstrates a deep understanding of how conservative forces relate to potential energy gradients. They accurately distinguish between work done by external forces and work done by the system, showing advanced conceptual intuition in energetic interactions.
                                </p>
                            </div>
                        </div>

                        {/* Ghost Chapter Block (Faded) replaced with Chapter 6 and 7 */}
                        {/* Divider */}
                        <div style={{ width: "100%", height: 1, backgroundColor: "#f1f5f9", margin: "32px 0" }} />

                        {/* Chapter 6 block */}
                        <div style={{ marginBottom: 24 }}>
                            <div style={{ marginBottom: 24 }}>
                                <h4 style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Chapter 6: System of Particles</h4>
                            </div>
                            <div style={{ paddingLeft: 16, borderLeft: "2px solid #ef4444", backgroundColor: "#f8fafc", padding: 24, borderRadius: "0 12px 12px 0", position: "relative" }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        <div style={{ color: "#ef4444" }}>
                                            <CloseIcon />
                                        </div>
                                        <span style={{ fontSize: 9, fontWeight: 700, color: "#ef4444", letterSpacing: 1.5, textTransform: "uppercase" }}>Misconception</span>
                                    </div>
                                    <span style={{ fontSize: 8, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Center of Mass</span>
                                </div>
                                <p style={{ fontSize: 13, lineHeight: 1.6, color: "#475569" }}>
                                    The student struggles to locate the center of mass for continuous bodies. They frequently confuse the geometric center with the center of mass, especially when mass density is non-uniform.
                                </p>
                            </div>
                        </div>

                        {/* Divider */}
                        <div style={{ width: "100%", height: 1, backgroundColor: "#f1f5f9", margin: "32px 0" }} />

                        {/* Chapter 7 block */}
                        <div style={{ marginBottom: 24 }}>
                            <div style={{ marginBottom: 24 }}>
                                <h4 style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Chapter 7: Gravitation</h4>
                            </div>
                            <div style={{ paddingLeft: 16, borderLeft: "2px solid #34d399", backgroundColor: "#f8fafc", padding: 24, borderRadius: "0 12px 12px 0", position: "relative" }}>
                                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                        <div style={{ color: "#10b981" }}>
                                            <CheckCircleIcon />
                                        </div>
                                        <span style={{ fontSize: 9, fontWeight: 700, color: "#10b981", letterSpacing: 1.5, textTransform: "uppercase" }}>Competency</span>
                                    </div>
                                    <span style={{ fontSize: 8, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase" }}>Kepler's Laws</span>
                                </div>
                                <p style={{ fontSize: 13, lineHeight: 1.6, color: "#475569" }}>
                                    Excellent application of Kepler's laws to planetary motion. Consistently correct in calculating orbital periods and velocities.
                                </p>
                            </div>
                        </div>

                        {/* Ghost Chapter Block (Faded) */}
                        <div style={{ opacity: 0.3 }}>
                            <div style={{ width: "100%", height: 1, backgroundColor: "#f1f5f9", margin: "32px 0" }} />
                            <div style={{ marginBottom: 16 }}>
                                <h4 style={{ fontSize: 10, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.5, textTransform: "uppercase", marginBottom: 16 }}>Chapter 8: Mechanical Properties</h4>
                                <div style={{ height: 96, backgroundColor: "#f8fafc", borderRadius: 12, borderLeft: "2px solid #e2e8f0" }} />
                            </div>
                        </div>

                    </div>

                    {/* Bottom fade gradient so text disappears smoothly */}
                    <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 80, background: "linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1))", pointerEvents: "none" }} />
                </div>
            </div>
        </AbsoluteFill>
    );
};
