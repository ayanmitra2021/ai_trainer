"use client";

import { ReactNode } from "react";
import { PortalBackground } from "../Portal3D";

interface PortalLayoutProps {
  children: ReactNode;
  className?: string;
  showBackground?: boolean;
}

export function PortalLayout({ children, className = "", showBackground = true }: PortalLayoutProps) {
  return (
    <div className={`portal-container ${className}`} style={{ minHeight: "100vh", position: "relative" }}>
      {showBackground && <PortalBackground />}
      <div
        className="portal-glow"
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          width: "800px",
          height: "800px",
          margin: "-400px 0 0 -400px",
          background: "radial-gradient(circle, rgba(77, 171, 247, 0.08) 0%, transparent 70%)",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 0,
          animation: "portalPulse 8s ease-in-out infinite",
        }}
      />
      <div
        className="portal-ring portal-ring-1"
        style={{
          position: "fixed",
          border: "1px solid rgba(77, 171, 247, 0.15)",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 0,
          animation: "rotateSlow 60s linear infinite",
          width: "200px",
          height: "200px",
          top: "calc(50% - 100px)",
          left: "calc(50% - 100px)",
        }}
      />
      <div
        className="portal-ring portal-ring-2"
        style={{
          position: "fixed",
          border: "1px solid rgba(77, 171, 247, 0.1)",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 0,
          animation: "rotateSlow 80s linear infinite reverse",
          width: "400px",
          height: "400px",
          top: "calc(50% - 200px)",
          left: "calc(50% - 200px)",
        }}
      />
      <div
        className="portal-ring portal-ring-3"
        style={{
          position: "fixed",
          border: "1px solid rgba(77, 171, 247, 0.05)",
          borderRadius: "50%",
          pointerEvents: "none",
          zIndex: 0,
          animation: "rotateSlow 100s linear infinite",
          width: "600px",
          height: "600px",
          top: "calc(50% - 300px)",
          left: "calc(50% - 300px)",
        }}
      />
      <main style={{ position: "relative", zIndex: 10, minHeight: "100vh", background: "var(--bg)" }}>
        {children}
      </main>
    </div>
  );
}

export function PortalPage({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <PortalLayout showBackground={true}>
      <div className={`page-enter ${className}`} style={{ padding: "2rem 1rem", maxWidth: "1200px", margin: "0 auto" }}>
        {children}
      </div>
    </PortalLayout>
  );
}