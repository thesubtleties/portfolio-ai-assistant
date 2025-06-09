import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';

// Register GSAP plugin
gsap.registerPlugin(SplitText);

interface TextToSwarmProps {
  targetRef: React.RefObject<HTMLElement | null>;
  trigger: boolean;
  onComplete?: () => void;
  className?: string;
}

const TextToSwarm: React.FC<TextToSwarmProps> = ({
  targetRef,
  trigger,
  onComplete,
  className = '',
}) => {
  const animationRef = useRef<GSAPTimeline | null>(null);

  useEffect(() => {
    if (!trigger || !targetRef.current || typeof window === 'undefined') return;

    const ctx = gsap.context(() => {
      const targetElement = targetRef.current;
      if (!targetElement) return;

      // Find all text elements within the target
      const textElements = targetElement.querySelectorAll('span, p, h1, div');
      const allSplits: SplitText[] = [];

      // Split all text elements into characters
      textElements.forEach((element) => {
        if (element.textContent && element.textContent.trim()) {
          const split = new SplitText(element, {
            type: 'chars',
            smartWrap: true,
          });
          allSplits.push(split);
        }
      });

      // Collect all characters
      const allChars = allSplits.reduce((acc: Element[], split) => {
        return acc.concat(split.chars);
      }, []);

      if (allChars.length === 0) {
        onComplete?.();
        return;
      }

      // Create the bee-swarm dissolve animation
      const tl = gsap.timeline({
        onComplete: () => {
          // Clean up splits
          allSplits.forEach((split) => split.revert());

          // Hide the original element
          gsap.set(targetElement, {
            display: 'none',
            visibility: 'hidden',
          });

          onComplete?.();
        },
      });

      animationRef.current = tl;

      // Animate characters to elegantly fly away
      allChars.forEach((char, index) => {
        const randomDelay = Math.random() * 0.3;

        // Each letter flies off in a different direction with natural physics
        const flyDirection =
          (index / allChars.length) * Math.PI * 2 + (Math.random() - 0.5) * 0.5;
        const flyDistance = 300 + Math.random() * 200;
        const finalX = Math.cos(flyDirection) * flyDistance;
        const finalY = Math.sin(flyDirection) * flyDistance;

        // Create elegant flight path with slight curve
        const midX = finalX * 0.6 + (Math.random() - 0.5) * 100;
        const midY = finalY * 0.6 + (Math.random() - 0.5) * 100;

        // Initial subtle lift and rotation
        tl.to(
          char,
          {
            y: -20 + (Math.random() - 0.5) * 20,
            rotation: Math.random() * 30 - 15,
            scale: 0.9,
            duration: 0.2,
            ease: 'power2.out',
          },
          randomDelay
        );

        // Flight to mid-point with rotation
        tl.to(
          char,
          {
            x: midX,
            y: midY,
            rotation:
              flyDirection * (180 / Math.PI) + (Math.random() - 0.5) * 60,
            scale: 0.6 + Math.random() * 0.3,
            opacity: 0.8,
            duration: 0.4,
            ease: 'power2.inOut',
          },
          randomDelay + 0.1
        );

        // Final dispersal with fade
        tl.to(
          char,
          {
            x: finalX,
            y: finalY,
            rotation: `+=${(Math.random() - 0.5) * 180}`,
            scale: 0.2,
            opacity: 0,
            duration: 0.6,
            ease: 'power2.in',
          },
          randomDelay + 0.3
        );
      });
    }, targetRef);

    return () => {
      ctx.revert();
      if (animationRef.current) {
        animationRef.current.kill();
      }
    };
  }, [trigger, targetRef, onComplete]);

  return null; // This component doesn't render anything visible
};

export default TextToSwarm;
