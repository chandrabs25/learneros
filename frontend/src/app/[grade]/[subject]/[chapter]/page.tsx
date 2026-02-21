"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Section {
    id: string;
    number: string;
    title: string;
}

export default function ChapterDetailPage() {
    const params = useParams();
    const router = useRouter();
    const grade = params.grade as string;
    const subject = params.subject as string;
    const chapter = params.chapter as string;
    const [error, setError] = useState(false);

    const chapterId = `ncert:${subject}:${grade}:${chapter}`;

    useEffect(() => {
        fetch(`${API_URL}/api/chapters/${chapterId}/sections`)
            .then((r) => r.json())
            .then((data) => {
                const sections = Array.isArray(data)
                    ? data.filter((s: Section) => s.title?.toLowerCase() !== "exercises")
                    : [];
                if (sections.length > 0) {
                    router.replace(`/${grade}/${subject}/${chapter}/${sections[0].number}`);
                } else {
                    setError(true);
                }
            })
            .catch(() => setError(true));
    }, [chapterId, grade, subject, chapter, router]);

    if (error) {
        return (
            <div className="loading-container">
                <p>No sections found for this chapter.</p>
            </div>
        );
    }

    return (
        <div className="loading-container">
            <div className="spinner" />
            Loading chapter...
        </div>
    );
}
