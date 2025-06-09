import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';

// Register GSAP plugin
gsap.registerPlugin(SplitText);

interface TextDissolveProps {
  text: string;
  trigger: boolean;
  onComplete: () => void;
  className?: string;
}

const TextDissolve: React.FC<TextDissolveProps> = ({
  text,
  trigger,
  onComplete,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLParagraphElement>(null);
  const animationRef = useRef<GSAPTimeline | null>(null);

  useEffect(() => {
    if (!trigger || !text || !containerRef.current || !textRef.current) return;

    // Kill any existing animation
    if (animationRef.current) {
      animationRef.current.kill();
    }

    const ctx = gsap.context(() => {
      // Use SplitText to preserve formatting like ResponseEmergence does
      const split = new SplitText(textRef.current, {
        type: 'chars',
        smartWrap: true,
      });

      // Create elegant dispersal animation
      const tl = gsap.timeline({
        onComplete: () => {
          split.revert();
          gsap.set(containerRef.current, { display: 'none' });
          onComplete();
        },
      });

      animationRef.current = tl;

      // Smoother dissolve animation with better overlap and hardware acceleration
      tl.to(split.chars, {
        scale: 0.9,
        x: () => (Math.random() - 0.5) * 60,
        y: () => (Math.random() - 0.5) * 60,
        rotation: () => (Math.random() - 0.5) * 45,
        duration: 0.25,
        ease: 'power2.out',
        force3D: true, // Force hardware acceleration
        stagger: {
          amount: 0.15,
          from: 'random',
        },
      })

        // Swirl and scale down with hardware acceleration
        .to(
          split.chars,
          {
            scale: 0.4,
            x: () => (Math.random() - 0.5) * 150,
            y: () => (Math.random() - 0.5) * 150,
            rotation: () => (Math.random() - 0.5) * 120,
            duration: 0.4,
            ease: 'sine.inOut',
            force3D: true, // Force hardware acceleration
            stagger: {
              amount: 0.2,
              from: 'random',
            },
          },
          0.15
        ) // Earlier overlap

        // Final fade with minimal delay and hardware acceleration
        .to(
          split.chars,
          {
            opacity: 0,
            scale: 0.1,
            rotation: () => `+=${(Math.random() - 0.5) * 90}`,
            duration: 0.3,
            ease: 'power1.in',
            force3D: true, // Force hardware acceleration
            stagger: {
              amount: 0.4, // Shorter fade out
              from: 'random',
            },
          },
          0.4
        ); // Much earlier start
    }, containerRef);

    return () => {
      ctx.revert();
      if (animationRef.current) {
        animationRef.current.kill();
      }
    };
  }, [trigger, text, onComplete]);

  if (!text || !trigger) return null;

  return (
    <div
      ref={containerRef}
      className={`text-dissolve ${className}`}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
      }}
    >
      <p ref={textRef} className="dissolve-text response-text">
        {text}
      </p>
    </div>
  );
};

export default TextDissolve;
