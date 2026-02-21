"use client";

import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Cropper from "react-easy-crop";
import type { Area } from "react-easy-crop";
import "katex/dist/katex.min.css";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Exercise {
    id: string;
    number: number;
    problem: string;
    solution: string | null;
    difficulty: string | null;
    exercise_type: string | null;
    exercise_set: string | null;
}

/* ── Helper: crop an image to the selected area ── */
async function getCroppedImg(imageSrc: string, crop: Area): Promise<string> {
    const image = new Image();
    image.src = imageSrc;
    await new Promise((res) => (image.onload = res));
    const canvas = document.createElement("canvas");
    canvas.width = crop.width;
    canvas.height = crop.height;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(
        image,
        crop.x, crop.y, crop.width, crop.height,
        0, 0, crop.width, crop.height
    );
    return canvas.toDataURL("image/jpeg", 0.92);
}

/* ── LaTeX-aware text renderer ── */
function RichText({ text }: { text: string }) {
    const parts = useMemo(() => {
        if (!text) return [];
        const regex = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
        const segments: { type: "text" | "inline-math" | "display-math"; value: string }[] = [];
        let lastIndex = 0;
        let match;

        while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) {
                segments.push({ type: "text", value: text.slice(lastIndex, match.index) });
            }
            const raw = match[0];
            if (raw.startsWith("$$")) {
                segments.push({ type: "display-math", value: raw.slice(2, -2).trim() });
            } else {
                segments.push({ type: "inline-math", value: raw.slice(1, -1).trim() });
            }
            lastIndex = match.index + raw.length;
        }
        if (lastIndex < text.length) {
            segments.push({ type: "text", value: text.slice(lastIndex) });
        }
        return segments;
    }, [text]);

    const [katex, setKatex] = useState<typeof import("katex") | null>(null);
    useEffect(() => {
        import("katex").then(setKatex);
    }, []);

    return (
        <>
            {parts.map((seg, i) => {
                if (seg.type === "text") {
                    return seg.value.split("\n\n").map((para, j) => (
                        <span key={`${i}-${j}`}>
                            {j > 0 && <br />}
                            {para}
                        </span>
                    ));
                }
                if (!katex) return <code key={i}>{seg.value}</code>;
                try {
                    const html = katex.renderToString(seg.value, {
                        throwOnError: false,
                        displayMode: seg.type === "display-math",
                    });
                    if (seg.type === "display-math") {
                        return (
                            <div
                                key={i}
                                style={{ margin: "1.5rem 0", textAlign: "center", overflowX: "auto" }}
                                dangerouslySetInnerHTML={{ __html: html }}
                            />
                        );
                    }
                    return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
                } catch {
                    return <code key={i}>{seg.value}</code>;
                }
            })}
        </>
    );
}

/* ── Camera Capture Modal ── */
function CameraModal({ onCapture, onClose }: { onCapture: (img: string) => void; onClose: () => void }) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [stream, setStream] = useState<MediaStream | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;
        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } } })
            .then((s) => {
                if (!active) { s.getTracks().forEach((t) => t.stop()); return; }
                setStream(s);
                if (videoRef.current) videoRef.current.srcObject = s;
            })
            .catch(() => setError("Camera access denied. Please allow camera permissions and try again."));
        return () => {
            active = false;
            stream?.getTracks().forEach((t) => t.stop());
        };
    }, []);

    const capture = () => {
        if (!videoRef.current) return;
        const v = videoRef.current;
        const canvas = document.createElement("canvas");
        canvas.width = v.videoWidth;
        canvas.height = v.videoHeight;
        canvas.getContext("2d")!.drawImage(v, 0, 0);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
        stream?.getTracks().forEach((t) => t.stop());
        onCapture(dataUrl);
    };

    return (
        <div style={{
            position: "fixed", inset: 0, zIndex: 9999,
            background: "rgba(0,0,0,0.85)", backdropFilter: "blur(8px)",
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
            {/* Close */}
            <button
                onClick={() => { stream?.getTracks().forEach((t) => t.stop()); onClose(); }}
                style={{
                    position: "absolute", top: 20, right: 20,
                    width: 44, height: 44, borderRadius: "50%",
                    background: "rgba(255,255,255,0.15)", color: "white",
                    border: "none", cursor: "pointer", zIndex: 10,
                    display: "flex", alignItems: "center", justifyContent: "center",
                }}
            >
                <span className="material-symbols-outlined" style={{ fontSize: "1.5rem" }}>close</span>
            </button>

            {error ? (
                <div style={{ textAlign: "center", color: "white", padding: "2rem" }}>
                    <span className="material-symbols-outlined" style={{ fontSize: "3rem", color: "#ef4444", marginBottom: 16, display: "block" }}>videocam_off</span>
                    <p style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: 8 }}>{error}</p>
                    <button
                        onClick={onClose}
                        style={{
                            marginTop: 16, padding: "0.75rem 2rem", background: "white",
                            color: "#111", border: "none", borderRadius: 12, fontWeight: 700,
                            cursor: "pointer", fontFamily: "var(--font-display)",
                        }}
                    >Go Back</button>
                </div>
            ) : (
                <>
                    {/* Video feed */}
                    <div style={{
                        position: "relative", width: "90%", maxWidth: 640,
                        aspectRatio: "4/3", borderRadius: 16, overflow: "hidden",
                        border: "2px solid rgba(255,255,255,0.15)",
                        boxShadow: "0 24px 48px rgba(0,0,0,0.3)",
                    }}>
                        <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            muted
                            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                        />
                        {/* Corner guides */}
                        <div style={{ position: "absolute", top: 16, left: 16, width: 24, height: 24, borderTop: "3px solid white", borderLeft: "3px solid white", borderRadius: "4px 0 0 0" }} />
                        <div style={{ position: "absolute", top: 16, right: 16, width: 24, height: 24, borderTop: "3px solid white", borderRight: "3px solid white", borderRadius: "0 4px 0 0" }} />
                        <div style={{ position: "absolute", bottom: 16, left: 16, width: 24, height: 24, borderBottom: "3px solid white", borderLeft: "3px solid white", borderRadius: "0 0 0 4px" }} />
                        <div style={{ position: "absolute", bottom: 16, right: 16, width: 24, height: 24, borderBottom: "3px solid white", borderRight: "3px solid white", borderRadius: "0 0 4px 0" }} />
                    </div>

                    <p style={{ color: "rgba(255,255,255,0.6)", marginTop: "1.25rem", fontSize: "0.875rem", fontWeight: 500 }}>
                        Position your paper within the frame
                    </p>

                    {/* Shutter button */}
                    <button
                        onClick={capture}
                        style={{
                            marginTop: "1.5rem",
                            width: 72, height: 72, borderRadius: "50%",
                            background: "white", border: "4px solid rgba(255,255,255,0.3)",
                            cursor: "pointer", position: "relative",
                            boxShadow: "0 8px 24px rgba(0,0,0,0.3)",
                            transition: "transform 0.1s ease",
                        }}
                    >
                        <div style={{
                            position: "absolute", inset: 6,
                            borderRadius: "50%", background: "white",
                            border: "2px solid #e2e8f0",
                        }} />
                    </button>
                </>
            )}
        </div>
    );
}

/* ── Crop Modal ── */
function CropModal({ imageSrc, onConfirm, onCancel }: {
    imageSrc: string;
    onConfirm: (croppedImg: string) => void;
    onCancel: () => void;
}) {
    const [crop, setCrop] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);

    const onCropComplete = useCallback((_: Area, areaPixels: Area) => {
        setCroppedAreaPixels(areaPixels);
    }, []);

    const handleConfirm = async () => {
        if (!croppedAreaPixels) return;
        const cropped = await getCroppedImg(imageSrc, croppedAreaPixels);
        onConfirm(cropped);
    };

    return (
        <div style={{
            position: "fixed", inset: 0, zIndex: 9999,
            background: "rgba(0,0,0,0.9)", backdropFilter: "blur(8px)",
            display: "flex", flexDirection: "column",
        }}>
            {/* Header */}
            <div style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "1rem 1.5rem", color: "white",
            }}>
                <button
                    onClick={onCancel}
                    style={{
                        background: "rgba(255,255,255,0.12)", border: "none",
                        color: "white", padding: "0.5rem 1.25rem", borderRadius: 10,
                        fontWeight: 600, fontSize: "0.875rem", cursor: "pointer",
                        fontFamily: "var(--font-display)",
                    }}
                >Cancel</button>
                <h3 style={{ fontWeight: 700, fontSize: "1rem", letterSpacing: "0.02em" }}>Crop your solution</h3>
                <button
                    onClick={handleConfirm}
                    style={{
                        background: "#ff7f50", border: "none",
                        color: "white", padding: "0.5rem 1.25rem", borderRadius: 10,
                        fontWeight: 700, fontSize: "0.875rem", cursor: "pointer",
                        fontFamily: "var(--font-display)",
                        boxShadow: "0 4px 12px rgba(255,127,80,0.3)",
                    }}
                >Done</button>
            </div>

            {/* Crop area */}
            <div style={{ position: "relative", flexGrow: 1 }}>
                <Cropper
                    image={imageSrc}
                    crop={crop}
                    zoom={zoom}
                    aspect={undefined}
                    onCropChange={setCrop}
                    onZoomChange={setZoom}
                    onCropComplete={onCropComplete}
                    style={{
                        containerStyle: { background: "#111" },
                    }}
                />
            </div>

            {/* Zoom slider */}
            <div style={{
                padding: "1.25rem 2rem", display: "flex", alignItems: "center",
                gap: "1rem", justifyContent: "center",
            }}>
                <span className="material-symbols-outlined" style={{ color: "rgba(255,255,255,0.5)", fontSize: "1.25rem" }}>
                    zoom_out
                </span>
                <input
                    type="range"
                    min={1}
                    max={3}
                    step={0.05}
                    value={zoom}
                    onChange={(e) => setZoom(Number(e.target.value))}
                    style={{
                        width: 200, accentColor: "#ff7f50",
                        cursor: "pointer",
                    }}
                />
                <span className="material-symbols-outlined" style={{ color: "rgba(255,255,255,0.5)", fontSize: "1.25rem" }}>
                    zoom_in
                </span>
            </div>
        </div>
    );
}


export default function ExercisesPage() {
    const params = useParams();
    const router = useRouter();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const section = params.section as string;

    const [exercises, setExercises] = useState<Exercise[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [loading, setLoading] = useState(true);

    // Upload / Camera / Crop state
    const [uploadedImages, setUploadedImages] = useState<string[]>([]);
    const [rawImage, setRawImage] = useState<string | null>(null); // pre-crop
    const [showCamera, setShowCamera] = useState(false);
    const [showCrop, setShowCrop] = useState(false);
    const [selectedPreview, setSelectedPreview] = useState<number | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const sectionId = `ncert:${subject}:${grade}:${chapter}:${section}`;

    useEffect(() => {
        fetch(`${API_URL}/api/sections/${sectionId}/exercises`)
            .then((r) => r.json())
            .then((data) => {
                setExercises(Array.isArray(data) ? data : []);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, [sectionId]);

    useEffect(() => {
        setUploadedImages([]);
        setRawImage(null);
        setSelectedPreview(null);
        window.scrollTo({ top: 0, behavior: "smooth" });
    }, [currentIndex]);

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (ev) => {
                const img = ev.target?.result as string;
                setRawImage(img);
                setShowCrop(true);
            };
            reader.readAsDataURL(file);
        }
        // Reset so same file can be re-selected
        e.target.value = "";
    };

    const handleCameraCapture = (img: string) => {
        setShowCamera(false);
        setRawImage(img);
        setShowCrop(true);
    };

    const handleCropConfirm = (croppedImg: string) => {
        setUploadedImages((prev) => [...prev, croppedImg]);
        setRawImage(null);
        setShowCrop(false);
    };

    const removeImage = (index: number) => {
        setUploadedImages((prev) => prev.filter((_, i) => i !== index));
        if (selectedPreview === index) setSelectedPreview(null);
    };

    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner" />
                Loading exercises...
            </div>
        );
    }

    if (exercises.length === 0) {
        return (
            <div style={{
                minHeight: "100vh", display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center", gap: "1.5rem",
                padding: "2rem", textAlign: "center",
            }}>
                <span className="material-symbols-outlined" style={{
                    fontSize: "4rem", color: "var(--text-muted)", opacity: 0.4,
                }}>quiz</span>
                <h2 className="font-display" style={{
                    fontSize: "1.5rem", fontWeight: 700, color: "var(--text)",
                }}>No exercises for this section</h2>
                <p style={{ color: "var(--text-muted)", maxWidth: 400 }}>
                    No exercises have been mapped to this section yet.
                </p>
                <button
                    onClick={() => router.back()}
                    style={{
                        padding: "0.75rem 2rem", background: "var(--primary)",
                        color: "#0a2e2b", border: "none", borderRadius: "var(--radius)",
                        fontWeight: 700, cursor: "pointer", fontFamily: "var(--font-display)",
                    }}
                >
                    Back to Lesson
                </button>
            </div>
        );
    }

    const current = exercises[currentIndex];

    return (
        <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
            {/* Modals */}
            {showCamera && (
                <CameraModal
                    onCapture={handleCameraCapture}
                    onClose={() => setShowCamera(false)}
                />
            )}
            {showCrop && rawImage && (
                <CropModal
                    imageSrc={rawImage}
                    onConfirm={handleCropConfirm}
                    onCancel={() => { setRawImage(null); setShowCrop(false); }}
                />
            )}

            {/* ── Main Content ── */}
            <main style={{
                flexGrow: 1, display: "flex", gap: "2rem",
                maxWidth: "72rem", margin: "0 auto", width: "100%",
                padding: "2rem 1.5rem", paddingBottom: "8rem",
            }}>
                {/* Left: Exercise Card + Upload */}
                <div style={{ flexGrow: 1, display: "flex", flexDirection: "column", gap: "2rem" }}>
                    {/* Exercise Card */}
                    <div style={{
                        background: "var(--white)", borderRadius: "var(--radius-lg)",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)", border: "1px solid var(--border)",
                        padding: "2.5rem",
                    }}>
                        {/* Exercise Badge */}
                        <div style={{
                            display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1.5rem",
                        }}>
                            <span style={{
                                color: "#2e5bff", fontWeight: 700, fontSize: "0.75rem",
                                letterSpacing: "0.15em", textTransform: "uppercase",
                            }}>
                                Exercise {String(current.number).padStart(2, "0")}
                            </span>
                            <div style={{ height: 1, flexGrow: 1, background: "var(--border)" }} />
                            {current.difficulty && (
                                <span style={{
                                    fontSize: "0.6875rem", fontWeight: 600,
                                    color: current.difficulty === "easy" ? "#22c55e" : current.difficulty === "hard" ? "#ef4444" : "#f59e0b",
                                    background: current.difficulty === "easy" ? "#f0fdf4" : current.difficulty === "hard" ? "#fef2f2" : "#fffbeb",
                                    padding: "0.25rem 0.75rem", borderRadius: "9999px",
                                    textTransform: "capitalize",
                                }}>{current.difficulty}</span>
                            )}
                        </div>

                        {/* Problem */}
                        <div style={{
                            fontSize: "1.25rem", fontWeight: 600, lineHeight: 1.6,
                            color: "var(--text)", marginBottom: "1.5rem",
                        }}>
                            <RichText text={current.problem} />
                        </div>

                        {/* Hint text */}
                        <p style={{
                            color: "var(--text-muted)", fontSize: "0.9375rem", lineHeight: 1.6,
                            fontStyle: "italic",
                        }}>
                            Show all your steps. Handwritten steps are preferred for physical intuition.
                        </p>
                    </div>

                    {/* Upload Solution Area */}
                    <div style={{
                        background: "var(--white)", borderRadius: "var(--radius-lg)",
                        border: uploadedImages.length > 0 ? "1px solid var(--border)" : "2px dashed var(--border)",
                        padding: "2rem",
                        display: "flex", flexDirection: "column", alignItems: "center",
                        justifyContent: "center", minHeight: uploadedImages.length > 0 ? "auto" : 400,
                        transition: "border-color 0.2s ease",
                    }}>
                        {/* Hidden file input */}
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            style={{ display: "none" }}
                            onChange={handleFileUpload}
                        />

                        {uploadedImages.length > 0 ? (
                            /* ── Multi-image thumbnail grid ── */
                            <div style={{ width: "100%" }}>
                                {/* Header */}
                                <div style={{
                                    display: "flex", alignItems: "center", justifyContent: "space-between",
                                    marginBottom: "1.25rem",
                                }}>
                                    <h3 style={{
                                        fontSize: "0.9375rem", fontWeight: 700, color: "var(--text)",
                                        display: "flex", alignItems: "center", gap: "0.5rem",
                                    }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: "1.25rem", color: "#22c55e" }}>check_circle</span>
                                        {uploadedImages.length} page{uploadedImages.length !== 1 ? "s" : ""} uploaded
                                    </h3>
                                    <button
                                        onClick={() => setUploadedImages([])}
                                        style={{
                                            fontSize: "0.8125rem", fontWeight: 600,
                                            color: "#ef4444", background: "none",
                                            border: "none", cursor: "pointer",
                                            fontFamily: "var(--font-display)",
                                        }}
                                    >Clear all</button>
                                </div>

                                {/* Thumbnail grid */}
                                <div style={{
                                    display: "grid",
                                    gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                                    gap: "1rem",
                                }}>
                                    {uploadedImages.map((img, i) => (
                                        <div
                                            key={i}
                                            style={{
                                                position: "relative", borderRadius: 12,
                                                overflow: "hidden", border: "1px solid var(--border)",
                                                aspectRatio: "3/4",
                                                cursor: "pointer",
                                                boxShadow: selectedPreview === i
                                                    ? "0 0 0 2px #2e5bff, 0 4px 12px rgba(46,91,255,0.2)"
                                                    : "0 2px 8px rgba(0,0,0,0.06)",
                                                transition: "box-shadow 0.15s ease",
                                            }}
                                            onClick={() => setSelectedPreview(selectedPreview === i ? null : i)}
                                        >
                                            <img
                                                src={img}
                                                alt={`Page ${i + 1}`}
                                                style={{
                                                    width: "100%", height: "100%",
                                                    objectFit: "cover", display: "block",
                                                }}
                                            />
                                            {/* Page number badge */}
                                            <div style={{
                                                position: "absolute", bottom: 6, left: 6,
                                                background: "rgba(0,0,0,0.6)", color: "white",
                                                fontSize: "0.6875rem", fontWeight: 700,
                                                padding: "0.15rem 0.5rem", borderRadius: 6,
                                            }}>Page {i + 1}</div>
                                            {/* Delete button */}
                                            <button
                                                onClick={(e) => { e.stopPropagation(); removeImage(i); }}
                                                style={{
                                                    position: "absolute", top: 6, right: 6,
                                                    width: 26, height: 26, borderRadius: "50%",
                                                    background: "rgba(0,0,0,0.55)", color: "white",
                                                    border: "none", cursor: "pointer",
                                                    display: "flex", alignItems: "center", justifyContent: "center",
                                                }}
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: "0.875rem" }}>close</span>
                                            </button>
                                        </div>
                                    ))}

                                    {/* Add more card */}
                                    <div style={{
                                        borderRadius: 12, border: "2px dashed var(--border)",
                                        aspectRatio: "3/4",
                                        display: "flex", flexDirection: "column",
                                        alignItems: "center", justifyContent: "center",
                                        gap: "0.75rem", cursor: "pointer",
                                        background: "#fafafa",
                                        transition: "border-color 0.15s ease, background 0.15s ease",
                                    }}>
                                        <span className="material-symbols-outlined" style={{
                                            fontSize: "2rem", color: "#94a3b8",
                                        }}>add_photo_alternate</span>
                                        <span style={{
                                            fontSize: "0.75rem", fontWeight: 600,
                                            color: "#94a3b8", textAlign: "center",
                                            lineHeight: 1.4,
                                        }}>Add another<br />page</span>
                                        <div style={{ display: "flex", gap: "0.375rem" }}>
                                            <button
                                                onClick={() => setShowCamera(true)}
                                                style={{
                                                    width: 32, height: 32, borderRadius: 8,
                                                    background: "#ff7f50", color: "white",
                                                    border: "none", cursor: "pointer",
                                                    display: "flex", alignItems: "center", justifyContent: "center",
                                                }}
                                                title="Take Photo"
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>photo_camera</span>
                                            </button>
                                            <button
                                                onClick={() => fileInputRef.current?.click()}
                                                style={{
                                                    width: 32, height: 32, borderRadius: 8,
                                                    background: "white", color: "var(--text-secondary)",
                                                    border: "1px solid var(--border)", cursor: "pointer",
                                                    display: "flex", alignItems: "center", justifyContent: "center",
                                                }}
                                                title="Upload Photo"
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: "1rem" }}>upload_file</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded preview */}
                                {selectedPreview !== null && uploadedImages[selectedPreview] && (
                                    <div style={{
                                        marginTop: "1.5rem", borderRadius: 12,
                                        overflow: "hidden", border: "1px solid var(--border)",
                                        boxShadow: "0 4px 16px rgba(0,0,0,0.08)",
                                    }}>
                                        <div style={{
                                            display: "flex", alignItems: "center", justifyContent: "space-between",
                                            padding: "0.75rem 1rem", background: "#f8fafc",
                                            borderBottom: "1px solid var(--border)",
                                        }}>
                                            <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                                                Page {selectedPreview + 1} of {uploadedImages.length}
                                            </span>
                                            <button
                                                onClick={() => setSelectedPreview(null)}
                                                style={{
                                                    background: "none", border: "none",
                                                    cursor: "pointer", color: "var(--text-muted)",
                                                    display: "flex", alignItems: "center",
                                                }}
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>close</span>
                                            </button>
                                        </div>
                                        <img
                                            src={uploadedImages[selectedPreview]}
                                            alt={`Page ${selectedPreview + 1}`}
                                            style={{ width: "100%", display: "block" }}
                                        />
                                    </div>
                                )}
                            </div>
                        ) : (
                            /* Empty upload state */
                            <>
                                {/* Preview placeholder */}
                                <div style={{
                                    position: "relative", width: "100%", maxWidth: 420,
                                    aspectRatio: "4/3", background: "#f1f5f9",
                                    borderRadius: "var(--radius)", overflow: "hidden",
                                    border: "1px solid var(--border)", marginBottom: "2rem",
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                }}>
                                    {/* Gradient overlay */}
                                    <div style={{
                                        position: "absolute", inset: 0,
                                        background: "linear-gradient(to top, rgba(0,0,0,0.08), transparent)",
                                        zIndex: 1,
                                    }} />
                                    {/* Corner brackets */}
                                    <div style={{ position: "absolute", top: 16, left: 16, width: 16, height: 16, borderTop: "2px solid rgba(0,0,0,0.15)", borderLeft: "2px solid rgba(0,0,0,0.15)" }} />
                                    <div style={{ position: "absolute", top: 16, right: 16, width: 16, height: 16, borderTop: "2px solid rgba(0,0,0,0.15)", borderRight: "2px solid rgba(0,0,0,0.15)" }} />
                                    <div style={{ position: "absolute", bottom: 16, left: 16, width: 16, height: 16, borderBottom: "2px solid rgba(0,0,0,0.15)", borderLeft: "2px solid rgba(0,0,0,0.15)" }} />
                                    <div style={{ position: "absolute", bottom: 16, right: 16, width: 16, height: 16, borderBottom: "2px solid rgba(0,0,0,0.15)", borderRight: "2px solid rgba(0,0,0,0.15)" }} />
                                    {/* Camera icon */}
                                    <div style={{ textAlign: "center", zIndex: 2 }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: "3.5rem", color: "#cbd5e1", marginBottom: 8, display: "block" }}>videocam_off</span>
                                        <p style={{ color: "#94a3b8", fontSize: "0.8125rem", fontWeight: 500 }}>Camera preview will appear here</p>
                                    </div>
                                </div>

                                {/* Upload CTA */}
                                <div style={{ textAlign: "center" }}>
                                    <div style={{
                                        display: "inline-flex", alignItems: "center", justifyContent: "center",
                                        width: 56, height: 56, borderRadius: "50%",
                                        background: "rgba(255,127,80,0.1)", marginBottom: "1rem",
                                    }}>
                                        <span className="material-symbols-outlined" style={{ fontSize: "1.75rem", color: "#ff7f50" }}>photo_camera</span>
                                    </div>
                                    <h3 style={{
                                        fontSize: "1.125rem", fontWeight: 700, color: "var(--text)",
                                        marginBottom: "0.5rem",
                                    }}>Upload your handwritten work</h3>
                                    <p style={{
                                        color: "var(--text-muted)", maxWidth: 320, margin: "0 auto 0.5rem",
                                        fontSize: "0.875rem", lineHeight: 1.6,
                                    }}>
                                        Position your paper clearly in the frame or select a file from your device.
                                    </p>
                                    <p style={{
                                        color: "var(--text-muted)", fontSize: "0.8125rem",
                                        margin: "0 auto 1.75rem", opacity: 0.7,
                                    }}>
                                        You can add multiple pages for longer solutions.
                                    </p>

                                    {/* Two buttons: Camera + Upload */}
                                    <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center", flexWrap: "wrap" }}>
                                        <button
                                            onClick={() => setShowCamera(true)}
                                            style={{
                                                display: "inline-flex", alignItems: "center", gap: "0.5rem",
                                                padding: "0.875rem 1.75rem",
                                                background: "#ff7f50", color: "white",
                                                border: "none", borderRadius: "var(--radius)",
                                                fontWeight: 700, fontSize: "0.9375rem",
                                                cursor: "pointer", fontFamily: "var(--font-display)",
                                                boxShadow: "0 8px 20px rgba(255,127,80,0.25)",
                                                transition: "transform 0.15s ease, box-shadow 0.15s ease",
                                            }}
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: "1.25rem" }}>photo_camera</span>
                                            Take Photo
                                        </button>
                                        <button
                                            onClick={() => fileInputRef.current?.click()}
                                            style={{
                                                display: "inline-flex", alignItems: "center", gap: "0.5rem",
                                                padding: "0.875rem 1.75rem",
                                                background: "white", color: "var(--text)",
                                                border: "1px solid var(--border)", borderRadius: "var(--radius)",
                                                fontWeight: 700, fontSize: "0.9375rem",
                                                cursor: "pointer", fontFamily: "var(--font-display)",
                                                transition: "background 0.15s ease",
                                            }}
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: "1.25rem" }}>upload_file</span>
                                            Upload Photo
                                        </button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Right: Exercise Navigator */}
                <aside style={{
                    width: 280, flexShrink: 0,
                    display: "none", /* hidden on mobile, shown on lg+ */
                }}>
                    <div className="exercise-sidebar" style={{
                        background: "var(--white)", borderRadius: "var(--radius-lg)",
                        border: "1px solid var(--border)", padding: "1.5rem",
                        position: "sticky", top: "6rem",
                    }}>
                        <h3 style={{
                            fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase",
                            letterSpacing: "0.15em", color: "var(--text-muted)",
                            marginBottom: "1.25rem", padding: "0 0.5rem",
                        }}>Exercises</h3>
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                            {exercises.map((ex, i) => {
                                const isActive = i === currentIndex;
                                return (
                                    <button
                                        key={ex.id}
                                        onClick={() => setCurrentIndex(i)}
                                        style={{
                                            display: "flex", alignItems: "center", gap: "0.75rem",
                                            padding: "0.625rem 0.75rem", borderRadius: "0.75rem",
                                            border: isActive ? "1px solid rgba(46,91,255,0.2)" : "1px solid transparent",
                                            background: isActive ? "rgba(46,91,255,0.05)" : "transparent",
                                            cursor: "pointer", textAlign: "left",
                                            transition: "all 0.15s ease",
                                            fontFamily: "var(--font-display)",
                                        }}
                                    >
                                        <div style={{
                                            width: 32, height: 32, borderRadius: "50%",
                                            display: "flex", alignItems: "center", justifyContent: "center",
                                            fontSize: "0.75rem", fontWeight: 700, flexShrink: 0,
                                            background: isActive ? "#2e5bff" : "#f1f5f9",
                                            color: isActive ? "white" : "var(--text-muted)",
                                            boxShadow: isActive ? "0 2px 8px rgba(46,91,255,0.3)" : "none",
                                        }}>
                                            {String(ex.number).padStart(2, "0")}
                                        </div>
                                        <span style={{
                                            fontSize: "0.8125rem", fontWeight: isActive ? 700 : 500,
                                            color: isActive ? "#2e5bff" : "var(--text-muted)",
                                            overflow: "hidden", textOverflow: "ellipsis",
                                            whiteSpace: "nowrap",
                                        }}>
                                            Exercise {String(ex.number).padStart(2, "0")}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>
                        {/* Progress */}
                        <div style={{
                            marginTop: "1.5rem", paddingTop: "1rem",
                            borderTop: "1px solid var(--border)", padding: "1rem 0.5rem 0",
                        }}>
                            <div style={{
                                display: "flex", justifyContent: "space-between",
                                fontSize: "0.6875rem", fontWeight: 700,
                                color: "var(--text-muted)", marginBottom: "0.5rem",
                                textTransform: "uppercase", letterSpacing: "0.1em",
                            }}>
                                <span>Progress</span>
                                <span style={{ color: "var(--text)" }}>
                                    {currentIndex + 1} / {exercises.length}
                                </span>
                            </div>
                            <div style={{
                                height: 6, width: "100%", borderRadius: 9999,
                                background: "rgba(20,184,166,0.12)",
                            }}>
                                <div style={{
                                    height: "100%", borderRadius: 9999,
                                    background: "var(--primary)",
                                    width: `${((currentIndex + 1) / exercises.length) * 100}%`,
                                    transition: "width 0.3s ease",
                                }} />
                            </div>
                        </div>
                    </div>
                </aside>
            </main>

            {/* ── Floating Action Bar ── */}
            <footer style={{
                position: "fixed", bottom: "2rem", left: "50%", transform: "translateX(-50%)",
                width: "90%", maxWidth: "64rem", zIndex: 50,
            }}>
                <div style={{
                    background: "rgba(255,255,255,0.92)", backdropFilter: "blur(16px)",
                    border: "1px solid rgba(0,0,0,0.08)", borderRadius: "var(--radius-lg)",
                    padding: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between",
                    gap: "1rem", boxShadow: "0 20px 40px rgba(0,0,0,0.1)",
                }}>
                    {/* Left: Action Buttons */}
                    <div style={{ display: "flex", gap: "0.5rem" }}>
                        <button
                            onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}`)}
                            style={{
                                display: "flex", alignItems: "center", gap: "0.5rem",
                                padding: "0.75rem 1.25rem",
                                background: "#2e5bff", color: "white", border: "none",
                                borderRadius: "var(--radius)", fontWeight: 700, fontSize: "0.875rem",
                                cursor: "pointer", fontFamily: "var(--font-display)",
                            }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>lightbulb</span>
                            Concepts
                        </button>
                        <button style={{
                            display: "flex", alignItems: "center", gap: "0.5rem",
                            padding: "0.75rem 1.25rem",
                            background: "#ffcc33", color: "#1a1a1a", border: "none",
                            borderRadius: "var(--radius)", fontWeight: 700, fontSize: "0.875rem",
                            cursor: "pointer", fontFamily: "var(--font-display)",
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>edit_note</span>
                            Exercises
                        </button>
                        <button style={{
                            display: "flex", alignItems: "center", gap: "0.5rem",
                            padding: "0.75rem 1.25rem",
                            background: "#ff7f50", color: "white", border: "none",
                            borderRadius: "var(--radius)", fontWeight: 700, fontSize: "0.875rem",
                            cursor: "pointer", fontFamily: "var(--font-display)",
                        }}>
                            <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>smart_toy</span>
                            AI Assistant
                        </button>
                    </div>

                    {/* Right: Nav */}
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <button
                            onClick={() => router.push(`/${grade}/${subject}/${chapter}/${section}`)}
                            style={{
                                padding: "0.75rem 1.5rem", border: "1px solid var(--border)",
                                borderRadius: "var(--radius)", background: "white", fontWeight: 700,
                                fontSize: "0.875rem", cursor: "pointer", color: "var(--text-secondary)",
                                fontFamily: "var(--font-display)",
                            }}
                        >
                            Back to Lesson
                        </button>
                        <button
                            onClick={() => {
                                if (uploadedImages.length === 0) {
                                    fileInputRef.current?.click();
                                    return;
                                }
                                alert(`Submitting ${uploadedImages.length} page(s) for AI review... (Coming soon!)`);
                            }}
                            style={{
                                display: "flex", alignItems: "center", gap: "0.5rem",
                                padding: "0.75rem 2rem", background: "#111",
                                color: "white", border: "none", borderRadius: "var(--radius)",
                                fontWeight: 700, fontSize: "0.875rem", cursor: "pointer",
                                boxShadow: "0 8px 16px rgba(0,0,0,0.15)",
                                fontFamily: "var(--font-display)",
                            }}
                        >
                            Submit for AI Review
                            <span className="material-symbols-outlined" style={{ fontSize: "1.125rem" }}>send</span>
                        </button>
                    </div>
                </div>
            </footer>

            {/* CSS for sidebar visibility on desktop */}
            <style jsx>{`
                @media (min-width: 1024px) {
                    .exercise-sidebar {
                        display: block !important;
                    }
                    aside {
                        display: block !important;
                    }
                }
            `}</style>
        </div>
    );
}
