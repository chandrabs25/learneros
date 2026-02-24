"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Grade {
  textbook_id: string;
  grade: number;
  label: string;
  chapter_count: number;
}

const ALL_GRADES = [6, 7, 8, 9, 10, 11, 12];

const GRADE_LABELS: Record<number, string> = {
  6: "Class VI",
  7: "Class VII",
  8: "Class VIII",
  9: "Freshman",
  10: "Sophomore",
  11: "Junior",
  12: "Senior",
};
const DEFAULT_START_GRADE = 11;

export default function HubPage() {
  const { user, getIdToken, role, loading: authLoading } = useAuth();
  const [apiGrades, setApiGrades] = useState<Grade[]>([]);
  const [scrollIndex, setScrollIndex] = useState(
    Math.max(0, ALL_GRADES.findIndex((g) => g === DEFAULT_START_GRADE))
  );
  const [loading, setLoading] = useState(true);
  const [roleChecked, setRoleChecked] = useState(false);
  const carouselRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (authLoading) return;
      if (!user) {
        if (!cancelled) setRoleChecked(true);
        return;
      }
      try {
        if (cancelled) return;
        if (role === "teacher") {
          router.replace("/teacher/dashboard");
          return;
        }
        if (role === "admin" || role === "superadmin") {
          router.replace("/admin/dashboard");
          return;
        }
      } catch {
        // Fall through to student hub.
      } finally {
        if (!cancelled) setRoleChecked(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, role, authLoading, router]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (user) {
          const token = await getIdToken();
          if (token) {
            const res = await fetch(`${API_URL}/api/students/me/dashboard/bootstrap`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            if (!cancelled) {
              const grades = Array.isArray(data?.grades) ? data.grades : [];
              setApiGrades(grades);
              setLoading(false);
            }
            return;
          }
        }
        const r = await fetch(`${API_URL}/api/grades`);
        const data = await r.json();
        if (!cancelled) {
          setApiGrades(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, getIdToken]);

  const availableGrades = new Set(apiGrades.map((g) => g.grade));

  const scrollToIndex = useCallback((idx: number) => {
    const el = carouselRef.current;
    if (!el) return;
    const cards = el.querySelectorAll<HTMLElement>(".grade-card");
    if (cards[idx]) {
      cards[idx].scrollIntoView({
        behavior: "smooth",
        inline: "center",
        block: "nearest",
      });
    }
    setScrollIndex(idx);
  }, []);

  const handlePrev = () => scrollToIndex(Math.max(0, scrollIndex - 1));
  const handleNext = () => scrollToIndex(Math.min(ALL_GRADES.length - 1, scrollIndex + 1));

  useEffect(() => {
    let rafId = 0;
    let cleanup: (() => void) | null = null;

    const bindWhenReady = () => {
      const el = carouselRef.current;
      if (!el) {
        rafId = window.requestAnimationFrame(bindWhenReady);
        return;
      }
      const onScroll = () => {
        const cards = el.querySelectorAll<HTMLElement>(".grade-card");
        const containerCenter = el.scrollLeft + el.clientWidth / 2;
        let closest = 0;
        let minDist = Infinity;
        cards.forEach((card, i) => {
          const cardCenter = card.offsetLeft + card.offsetWidth / 2;
          const dist = Math.abs(containerCenter - cardCenter);
          if (dist < minDist) {
            minDist = dist;
            closest = i;
          }
        });
        setScrollIndex(closest);
      };
      el.addEventListener("scroll", onScroll, { passive: true });
      cleanup = () => el.removeEventListener("scroll", onScroll);
    };

    bindWhenReady();
    return () => {
      if (rafId) window.cancelAnimationFrame(rafId);
      if (cleanup) cleanup();
    };
  }, []);

  // Set initial scroll BEFORE first paint — no animation avoids the visible jump
  useLayoutEffect(() => {
    if (loading || !roleChecked) return;
    const cards = carouselRef.current?.querySelectorAll<HTMLElement>(".grade-card");
    if (!cards || cards.length === 0) return;
    const preferredIdx = ALL_GRADES.findIndex((g) => g === DEFAULT_START_GRADE);
    const firstAvailableIdx = ALL_GRADES.findIndex((g) => availableGrades.has(g));
    const startIdx = preferredIdx >= 0 ? preferredIdx : (firstAvailableIdx >= 0 ? firstAvailableIdx : 0);
    const targetCard = cards[startIdx];
    if (!targetCard) return;
    targetCard.scrollIntoView({
      behavior: "auto",
      inline: "center",
      block: "nearest",
    });
    setScrollIndex(startIdx);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, roleChecked, apiGrades]);

  if (!roleChecked || loading) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p>Preparing your curriculum...</p>
      </div>
    );
  }

  return (
    <div className="hub-page">
      <div className="hub-main">
        {/* Hero Title */}
        <div className="hub-hero">
          <h1>
            Where are we <br />
            <span>starting today?</span>
          </h1>
          <p className="subtitle">
            Select your grade level to dive back into your academic journey.
          </p>
        </div>

        {/* Right column: Carousel + Nav */}
        <div className="carousel-window">
          <div className="carousel-column">
            {/* Grade Carousel */}
            <div className="grade-carousel" ref={carouselRef}>
              {/* Leading spacer — matches scroll-padding-left so first card starts at center */}
              <div className="carousel-spacer-lead" style={{ flexShrink: 0 }} />
              {ALL_GRADES.map((grade, i) => {
                const exists = availableGrades.has(grade);
                const isActive = i === scrollIndex;

                return (
                  <div
                    key={grade}
                    className={`grade-card ${isActive ? "card-active" : "card-inactive"}`}
                    onClick={() => {
                      if (isActive && exists) {
                        router.push(`/${grade}`);
                      } else {
                        scrollToIndex(i);
                      }
                    }}
                  >
                    <div className="card-pattern">
                      {/* Visual patterns from reference would go here */}
                      {isActive && (
                        <img
                          src="https://lh3.googleusercontent.com/aida-public/AB6AXuD1wZjlwkpES-AlykUkmG6WPTAdz3REaqmxa_ez6zAEKgoDId6VtXw77Bk301oRTJ0Gp6LYZeDSmFHhtIBobd83uP6rAb1Zt3qdBMk71LQcVAUUxFytHSvqt-ETMqE78dvsiAkedXROpuqbib7RSP0vJvbT0nLafCvqKPVdG84m3UzuxCSh9KVaoxFX_MGFJYXahLtBWGC9I7j3em7wqAUYWbEMwtbTs0WF7pCtWCB1RZ5hfzy3xIF5TSLjplfhIXpHt9guUgrUM04B"
                          alt=""
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                      )}
                    </div>

                    <div className="card-content">
                      <div className="card-top">
                        <div className="level-badge">Level {String(grade).padStart(2, "00")}</div>
                      </div>

                      <div className="grade-number">{String(grade).padStart(2, "0")}</div>

                      <div className="card-footer">
                        <div className="footer-main">
                          <p className="footer-label">{GRADE_LABELS[grade] || `Class ${grade}`}</p>
                          {exists ? (
                            <p className="footer-info">Curriculum Available</p>
                          ) : (
                            <p className="footer-info coming-soon">Coming Soon</p>
                          )}
                        </div>

                        {isActive && exists ? (
                          <button
                            className="arrow-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              router.push(`/${grade}`);
                            }}
                          >
                            <span className="material-symbols-outlined">arrow_forward</span>
                          </button>
                        ) : (
                          <span className="material-symbols-outlined footer-icon">
                            {exists ? "north_east" : "chevron_right"}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              {/* Spacer for end of carousel */}
              <div style={{ width: "20vw", flexShrink: 0 }} />
            </div>

            {/* Navigation Controls */}
            <div className="hub-nav-controls">
              <div className="hub-nav-inner">
                <button
                  className="hub-nav-arrow"
                  onClick={handlePrev}
                  disabled={scrollIndex === 0}
                >
                  <span className="material-symbols-outlined">west</span>
                </button>

                <div className="hub-nav-dots">
                  {ALL_GRADES.map((_, i) => (
                    <div
                      key={i}
                      className={`hub-dot ${i === scrollIndex ? "active" : ""}`}
                      onClick={() => scrollToIndex(i)}
                    />
                  ))}
                </div>

                <button
                  className="hub-nav-arrow"
                  onClick={handleNext}
                  disabled={scrollIndex === ALL_GRADES.length - 1}
                >
                  <span className="material-symbols-outlined">east</span>
                </button>
              </div>
              <div className="hub-nav-hint">Swipe or Use Arrows to Navigate</div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Footer ─── */}
      <footer className="hub-footer">
        <div className="hub-footer-inner">
          {/* Brand Column */}
          <div className="hub-footer-col hub-footer-brand">
            <div className="hub-footer-logo-row">
              <img src="/learneros-logo.jpg" alt="LearnerOS" className="hub-footer-logo" />
              <span className="hub-footer-brand-name">LearnerOS</span>
            </div>
            <p className="hub-footer-tagline">
              Your personalised academic companion — learn at your pace, master every concept.
            </p>
          </div>

          {/* Quick Links */}
          <div className="hub-footer-col">
            <h4 className="hub-footer-heading">Quick Links</h4>
            <ul className="hub-footer-list">
              <li><Link href="/" className="hub-footer-link">Home</Link></li>
              <li><Link href="/insights" className="hub-footer-link">Insights</Link></li>
              <li><Link href="/tutor" className="hub-footer-link">LearnerOS Tutor</Link></li>
            </ul>
          </div>

          {/* Get Involved */}
          <div className="hub-footer-col">
            <h4 className="hub-footer-heading">Get Involved</h4>
            <ul className="hub-footer-list">
              <li>
                <Link href="/teacher/apply" className="hub-footer-link hub-footer-cta">
                  Apply as a Teacher
                </Link>
              </li>
              <li>
                <a className="hub-footer-link" href="mailto:srichandra@learneros.me">
                  srichandra@learneros.me
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="hub-footer-bottom">
          <p>© {new Date().getFullYear()} LearnerOS. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
