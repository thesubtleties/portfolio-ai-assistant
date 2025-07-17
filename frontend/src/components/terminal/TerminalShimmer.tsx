import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin';

// Register the plugin
gsap.registerPlugin(DrawSVGPlugin);

interface TerminalShimmerProps {
  containerRef: React.RefObject<HTMLElement>;
  triggerAnimation?: boolean;
  onComplete?: () => void;
}

const TerminalShimmer: React.FC<TerminalShimmerProps> = ({
  containerRef,
  triggerAnimation = false,
  onComplete,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const pathRef = useRef<SVGPathElement>(null);
  const hasAnimatedRef = useRef(false);

  useEffect(() => {
    console.log(
      '🎨 TerminalShimmer useEffect - triggerAnimation:',
      triggerAnimation,
      'hasAnimated:',
      hasAnimatedRef.current
    );
    if (
      !triggerAnimation ||
      !containerRef.current ||
      !svgRef.current ||
      !pathRef.current ||
      hasAnimatedRef.current // Prevent re-animation
    )
      return;

    hasAnimatedRef.current = true; // Mark as animated
    console.log('✨ Starting shimmer animation');
    const container = containerRef.current;
    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // Update SVG size
    svgRef.current.setAttribute('width', `${width}`);
    svgRef.current.setAttribute('height', `${height}`);

    // Create rectangle path (with small offset to prevent clipping)
    const offset = 1; // Small offset from edges
    const pathData = `
      M ${offset} ${offset}
      L ${width - offset} ${offset}
      L ${width - offset} ${height - offset}
      L ${offset} ${height - offset}
      Z
    `;

    pathRef.current.setAttribute('d', pathData);

    // Create timeline for the animation
    const tl = gsap.timeline({
      onComplete: () => {
        if (onComplete) onComplete();
      },
    });

    // Set initial state - completely hidden
    gsap.set(pathRef.current, {
      drawSVG: '0%',
      opacity: 1,
    });

    // Animate the line drawing and keep it visible
    tl.to(pathRef.current, {
      drawSVG: '100%',
      duration: 2,
      ease: 'power2.inOut',
    });

    // Cleanup
    return () => {
      tl.kill();
    };
  }, [triggerAnimation, containerRef, onComplete]);

  return (
    <svg
      ref={svgRef}
      className="shimmer-svg"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 100,
      }}
    >
      <path
        ref={pathRef}
        fill="none"
        stroke="rgba(44, 62, 80, 0.1)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          filter: 'blur(0.5px)',
        }}
      />
    </svg>
  );
};

export default TerminalShimmer;
