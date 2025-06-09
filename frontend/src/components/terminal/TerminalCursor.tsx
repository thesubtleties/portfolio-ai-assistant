import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';

interface TerminalCursorProps {
  isVisible?: boolean;
  isBlinking?: boolean;
  className?: string;
}

const TerminalCursor: React.FC<TerminalCursorProps> = ({
  isVisible = true,
  isBlinking = true,
  className = '',
}) => {
  const cursorRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!cursorRef.current || typeof window === 'undefined') return;

    const ctx = gsap.context(() => {
      if (isBlinking && isVisible) {
        // Terminal-style blinking cursor with hardware acceleration
        gsap.to(cursorRef.current, {
          opacity: 0,
          duration: 0.5,
          ease: 'power2.inOut',
          repeat: -1,
          yoyo: true,
          force3D: true, // Force hardware acceleration
        });
      } else if (isVisible) {
        // Solid cursor when typing with hardware acceleration
        gsap.set(cursorRef.current, { opacity: 1, force3D: true });
      } else {
        // Hidden cursor with hardware acceleration
        gsap.set(cursorRef.current, { opacity: 0, force3D: true });
      }
    }, cursorRef);

    return () => ctx.revert();
  }, [isVisible, isBlinking]);

  if (!isVisible) return null;

  return (
    <span ref={cursorRef} className={`terminal-cursor ${className}`}>
      █
    </span>
  );
};

export default TerminalCursor;
