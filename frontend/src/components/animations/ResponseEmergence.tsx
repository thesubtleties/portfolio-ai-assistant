import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(SplitText);

interface ResponseEmergenceProps {
  response: string;
  isActive: boolean;
  shouldDissolve?: boolean;
  onComplete?: () => void;
  onDissolveComplete?: () => void;
  className?: string;
}

const ResponseEmergence: React.FC<ResponseEmergenceProps> = ({
  response,
  isActive,
  shouldDissolve = false,
  onComplete,
  onDissolveComplete,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLParagraphElement>(null);

  // Handle dissolution separately
  useEffect(() => {
    if (shouldDissolve && containerRef.current && response) {
      const ctx = gsap.context(() => {
        // Dissolve current response back to swirling letters
        const split = new SplitText(textRef.current, {
          type: 'chars',
          smartWrap: true,
        });

        gsap.to(split.chars, {
          opacity: 0,
          scale: 0.3,
          x: () => (Math.random() - 0.5) * 200,
          y: () => (Math.random() - 0.5) * 200,
          rotation: () => (Math.random() - 0.5) * 90,
          duration: 0.6, // Reduced from 0.8s to 0.6s
          ease: 'power2.in',
          force3D: true, // Force hardware acceleration
          stagger: {
            amount: 0.3, // Reduced from 0.4s to 0.3s
            from: 'random',
          },
          onComplete: () => {
            // Don't revert split until after callback to prevent flash
            onDissolveComplete?.();
            // Small delay to ensure callback completes before reverting
            setTimeout(() => {
              split.revert();
            }, 10);
          },
        });
      }, containerRef);

      return () => ctx.revert();
    }
  }, [shouldDissolve, response, onDissolveComplete]);

  useEffect(() => {
    if (!response || !containerRef.current || typeof window === 'undefined') {
      return;
    }

    if (!isActive && response && !shouldDissolve) {
      // Keep response visible but not actively animating
      gsap.set(containerRef.current, { display: 'block', opacity: 1 });
      return;
    }

    if (!isActive) {
      // Hide when no response
      gsap.set(containerRef.current, { display: 'none', opacity: 0 });
      return;
    }

    const ctx = gsap.context(() => {
      // Show container
      gsap.set(containerRef.current, { display: 'block', opacity: 1 });

      // Split the response text into characters
      const split = new SplitText(textRef.current, {
        type: 'chars',
        smartWrap: true,
      });

      const chars = split.chars;

      // Initial state - characters scattered but closer with hardware acceleration
      gsap.set(chars, {
        opacity: 0,
        scale: 0.3,
        x: () => (Math.random() - 0.5) * 250,
        y: () => (Math.random() - 0.5) * 250,
        rotation: () => (Math.random() - 0.5) * 120,
        force3D: true, // Force hardware acceleration
      });

      // Animate characters coming together to form the response
      const tl = gsap.timeline({
        onComplete: () => {
          split.revert();
          onComplete?.();
        },
      });

      // Smoother emergence with better overlap and hardware acceleration
      tl.to(chars, {
        opacity: 0.7,
        scale: 0.6,
        x: () => (Math.random() - 0.5) * 80,
        y: () => (Math.random() - 0.5) * 80,
        rotation: () => (Math.random() - 0.5) * 60,
        duration: 0.3,
        ease: 'power2.out',
        force3D: true, // Force hardware acceleration
        stagger: {
          amount: 0.2,
          from: 'random',
        },
      })

        // Quick converge with hardware acceleration
        .to(
          chars,
          {
            opacity: 0.9,
            scale: 0.85,
            x: () => (Math.random() - 0.5) * 25,
            y: () => (Math.random() - 0.5) * 25,
            rotation: () => (Math.random() - 0.5) * 20,
            duration: 0.3,
            ease: 'sine.inOut',
            force3D: true, // Force hardware acceleration
            stagger: {
              amount: 0.2,
              from: 'random',
            },
          },
          0.15
        ) // Earlier overlap

        // Final settle with bounce and hardware acceleration
        .to(
          chars,
          {
            opacity: 1,
            scale: 1,
            x: 0,
            y: 0,
            rotation: 0,
            duration: 0.4,
            ease: 'back.out(1.2)', // Gentler bounce
            force3D: true, // Force hardware acceleration
            stagger: {
              amount: 0.3,
              from: 'random',
            },
          },
          0.35
        ); // Much earlier overlap

      return () => {
        split.revert();
      };
    }, containerRef);

    return () => ctx.revert();
  }, [isActive, response, onComplete]);

  if (!response) return null;

  return (
    <div
      ref={containerRef}
      className={`response-emergence ${className}`}
      style={{ display: 'none', opacity: 0 }}
    >
      <p ref={textRef} className="response-text">
        {response}
      </p>
    </div>
  );
};

export default ResponseEmergence;
