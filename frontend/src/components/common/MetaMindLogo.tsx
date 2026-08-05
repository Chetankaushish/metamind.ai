import React from 'react';

interface MetaMindLogoProps {
  className?: string;
  size?: number;
  variant?: 'icon' | 'horizontal' | 'vertical' | 'showcase';
  theme?: 'dark' | 'light' | 'auto';
  showSubtext?: boolean;
  showGlow?: boolean;
}

export const MetaMindLogo: React.FC<MetaMindLogoProps> = ({
  className = "",
  size = 42,
  variant = 'icon',
  theme = 'auto',
  showSubtext = true,
  showGlow = true
}) => {
  const idPrefix = React.useId().replace(/:/g, '_');
  const isDark = theme === 'dark' || (theme === 'auto');

  // Pure Vector 3D Flowing Ribbon "M" Mark
  const IconMark = (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      {showGlow && (
        <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-[#1877F2] via-[#2563EB] to-[#06B6D4] opacity-30 blur-lg pointer-events-none transform scale-110" />
      )}
      <svg
        width={size}
        height={size}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="relative z-10 w-full h-full drop-shadow-lg transition-transform duration-300 hover:scale-105"
      >
        <defs>
          {/* Continuous Ribbon Gradients for 3D Depth */}
          <linearGradient id={`${idPrefix}_ribbonMain`} x1="10" y1="90" x2="90" y2="10" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1877F2" />
            <stop offset="35%" stopColor="#2563EB" />
            <stop offset="70%" stopColor="#4F46E5" />
            <stop offset="100%" stopColor="#06B6D4" />
          </linearGradient>

          <linearGradient id={`${idPrefix}_ribbonBack`} x1="15" y1="20" x2="85" y2="80" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1D4ED8" />
            <stop offset="50%" stopColor="#3730A3" />
            <stop offset="100%" stopColor="#0284C7" />
          </linearGradient>

          <linearGradient id={`${idPrefix}_ribbonHighlight`} x1="30" y1="15" x2="80" y2="25" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#60A5FA" />
            <stop offset="50%" stopColor="#818CF8" />
            <stop offset="100%" stopColor="#22D3EE" />
          </linearGradient>

          <linearGradient id={`${idPrefix}_bgGrad`} x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor={isDark ? "#0F172A" : "#FFFFFF"} />
            <stop offset="100%" stopColor={isDark ? "#1E1B4B" : "#F8FAFC"} />
          </linearGradient>

          {/* Depth Drop Shadow Filter */}
          <filter id={`${idPrefix}_shadow`} x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="3" floodColor="#000000" floodOpacity={isDark ? "0.5" : "0.15"} />
          </filter>
        </defs>

        {/* Outer Squircle Container Frame */}
        <rect
          x="3"
          y="3"
          width="94"
          height="94"
          rx="26"
          fill={`url(#${idPrefix}_bgGrad)`}
          stroke={isDark ? "rgba(255, 255, 255, 0.12)" : "rgba(37, 99, 235, 0.15)"}
          strokeWidth="2"
        />

        {/* Subtle Infinity Geometric Guide Mesh */}
        <path
          d="M25 50 C25 35, 40 35, 50 50 C60 65, 75 65, 75 50 C75 35, 60 35, 50 50 C40 65, 25 65, 25 50 Z"
          fill="none"
          stroke={`url(#${idPrefix}_ribbonMain)`}
          strokeWidth="0.5"
          strokeDasharray="2 4"
          opacity="0.2"
        />

        {/* CONTINUOUS 3D FLOWING RIBBON "M" */}
        {/* Layer 1: Rear Overlap Shadow / Depth Ribbon Loop */}
        <path
          d="M 22 72 C 22 55, 30 24, 42 24 C 52 24, 46 52, 50 52 C 54 52, 48 24, 58 24 C 70 24, 78 55, 78 72"
          fill="none"
          stroke={`url(#${idPrefix}_ribbonBack)`}
          strokeWidth="11"
          strokeLinecap="round"
          opacity="0.85"
        />

        {/* Layer 2: Main Continuous Flowing Ribbon "M" */}
        <path
          d="M 20 72 C 20 48, 28 22, 42 22 C 53 22, 47 50, 50 50 C 53 50, 47 22, 58 22 C 72 22, 80 48, 80 72"
          fill="none"
          stroke={`url(#${idPrefix}_ribbonMain)`}
          strokeWidth="10"
          strokeLinecap="round"
          filter={`url(#${idPrefix}_shadow)`}
        />

        {/* Layer 3: Top Curved Highlights (Glossy 3D Effect) */}
        <path
          d="M 26 40 C 31 27, 37 24, 42 24 C 47 24, 48 38, 50 48"
          fill="none"
          stroke={`url(#${idPrefix}_ribbonHighlight)`}
          strokeWidth="4"
          strokeLinecap="round"
          opacity="0.9"
        />
        <path
          d="M 50 48 C 52 38, 53 24, 58 24 C 63 24, 69 27, 74 40"
          fill="none"
          stroke={`url(#${idPrefix}_ribbonHighlight)`}
          strokeWidth="4"
          strokeLinecap="round"
          opacity="0.9"
        />

        {/* Layer 4: Upward AI Trajectory Cyan Accent Ribbon (Data Flow & Growth) */}
        <path
          d="M 50 50 C 58 50, 72 38, 82 20"
          fill="none"
          stroke="#06B6D4"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray="1 0"
        />

        {/* Arrowhead / Data Growth Beacon at Apex */}
        <path
          d="M 72 18 L 84 18 L 84 30"
          fill="none"
          stroke="#06B6D4"
          strokeWidth="4.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Interconnected Neural Data Nodes */}
        <circle cx="20" cy="72" r="5" fill="#1877F2" stroke="#FFFFFF" strokeWidth="2" />
        <circle cx="50" cy="50" r="4.5" fill="#4F46E5" stroke="#FFFFFF" strokeWidth="2" />
        <circle cx="80" cy="72" r="5" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2" />
        <circle cx="84" cy="18" r="5.5" fill="#06B6D4" stroke="#FFFFFF" strokeWidth="2.5" />

        {/* AI Pulse Sparkle */}
        <path d="M 84 10 L 85.5 15.5 L 91 17 L 85.5 18.5 L 84 24 L 82.5 18.5 L 77 17 L 82.5 15.5 Z" fill="#FFFFFF" />
      </svg>
    </div>
  );

  if (variant === 'icon') {
    return <div className={className}>{IconMark}</div>;
  }

  if (variant === 'showcase') {
    return (
      <div className={`p-8 rounded-2xl border transition-all ${isDark ? 'bg-slate-900/90 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'} ${className}`}>
        <div className="flex flex-col items-center text-center gap-4">
          {IconMark}
          <div>
            <h3 className="text-2xl font-black tracking-tight font-sans">
              Meta<span className="bg-gradient-to-r from-[#1877F2] via-[#2563EB] to-[#06B6D4] bg-clip-text text-transparent">Mind</span> AI
            </h3>
            <p className="text-xs font-bold tracking-[0.25em] uppercase text-slate-400 mt-1">
              BY VOLZAD
            </p>
          </div>
          <p className="text-xs text-slate-400 max-w-xs mt-2">
            Enterprise Meta Ads Intelligence, Predictive Analytics & Autonomous Copilot Engine.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${variant === 'vertical' ? 'flex-col items-center text-center gap-3' : 'items-center gap-3.5'} ${className}`}>
      {IconMark}
      <div className="flex flex-col justify-center">
        <div className="flex items-center gap-1.5 leading-none">
          <span className={`font-black tracking-tight text-xl font-sans ${isDark ? 'text-white' : 'text-slate-900'}`}>
            Meta<span className="bg-gradient-to-r from-[#1877F2] via-[#2563EB] to-[#06B6D4] bg-clip-text text-transparent">Mind</span>
          </span>
          <span className="px-1.5 py-0.5 text-[10px] font-extrabold tracking-wider text-cyan-400 bg-cyan-950/80 border border-cyan-500/30 rounded-md uppercase">
            AI
          </span>
        </div>
        {showSubtext && (
          <span className={`text-[10px] font-semibold tracking-[0.25em] uppercase mt-1 ${isDark ? 'text-slate-400' : 'text-slate-500'}`}>
            BY VOLZAD
          </span>
        )}
      </div>
    </div>
  );
};

export default MetaMindLogo;
