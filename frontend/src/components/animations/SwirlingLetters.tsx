import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';

interface SwirlingLettersProps {
  isActive: boolean;
  shouldDissolve?: boolean;
  className?: string;
}

const SwirlingLetters: React.FC<SwirlingLettersProps> = ({
  isActive,
  shouldDissolve = false,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const lettersRef = useRef<HTMLSpanElement[]>([]);
  const [letters, setLetters] = useState<string[]>([]);

  // Generate random letters for the swirl effect
  const generateLetters = (count: number = 80) => {
    const alphabet =
      'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,;:!?-';
    const newLetters = [];

    for (let i = 0; i < count; i++) {
      newLetters.push(alphabet[Math.floor(Math.random() * alphabet.length)]);
    }

    return newLetters;
  };

  // Initialize letters
  useEffect(() => {
    setLetters(generateLetters());
  }, []);

  useEffect(() => {
    if (
      !containerRef.current ||
      typeof window === 'undefined' ||
      letters.length === 0
    )
      return;

    const ctx = gsap.context(() => {
      // Always show the container - make it continuous
      gsap.set(containerRef.current, { display: 'block' });

      // Animate to the appropriate intensity - quick fade out when inactive
      const targetOpacity = isActive ? 1 : 0;
      gsap.to(containerRef.current, {
        opacity: targetOpacity,
        duration: isActive ? 0.8 : 0.3, // Faster fade out
        ease: isActive ? 'power2.out' : 'power2.in',
      });

      lettersRef.current.forEach((letter) => {
        if (!letter) return;

        // Create a continuous bee-swarm behavior
        const createBeeSwarmAnimation = () => {
          // Get container dimensions for relative positioning
          const container = containerRef.current;
          if (!container) return;

          // Use the actual container's offsetWidth/Height for positioning
          const containerWidth = container.offsetWidth || 800;
          const containerHeight = container.offsetHeight || 600;

          // Random starting position on edge of container
          const edge = Math.floor(Math.random() * 4); // 0: top, 1: right, 2: bottom, 3: left
          let startX, startY, centerX, centerY;

          const margin = 50;
          switch (edge) {
            case 0: // top
              startX = Math.random() * containerWidth;
              startY = -margin;
              break;
            case 1: // right
              startX = containerWidth + margin;
              startY = Math.random() * containerHeight;
              break;
            case 2: // bottom
              startX = Math.random() * containerWidth;
              startY = containerHeight + margin;
              break;
            default: // left
              startX = -margin;
              startY = Math.random() * containerHeight;
          }

          // Center area for swarming - focus on main content area
          centerX = containerWidth / 2;
          centerY = containerHeight * 0.3; // Focus on upper area

          // Set initial position
          gsap.set(letter, {
            x: startX,
            y: startY,
            opacity: 0,
            scale: 0.3 + Math.random() * 0.4,
            rotation: Math.random() * 360,
          });

          const swarmTl = gsap.timeline({
            onComplete: () => {
              // Restart the animation for continuous flow
              setTimeout(() => createBeeSwarmAnimation(), Math.random() * 2000);
            },
          });

          // Bee enters swarm area
          swarmTl.to(letter, {
            x: centerX + (Math.random() - 0.5) * 200,
            y: centerY + (Math.random() - 0.5) * 150,
            opacity: isActive
              ? 0.4 + Math.random() * 0.4
              : 0.1 + Math.random() * 0.2,
            duration: 1.5 + Math.random() * 2,
            ease: 'power2.inOut',
          });

          // Bee swarms around center with organic movement (shorter)
          for (let i = 0; i < 2 + Math.random() * 2; i++) {
            swarmTl.to(letter, {
              x: centerX + (Math.random() - 0.5) * 250,
              y: centerY + (Math.random() - 0.5) * 180,
              rotation: `+=${Math.random() * 720 - 360}`,
              scale: 0.3 + Math.random() * 0.5,
              duration: 0.8 + Math.random() * 1,
              ease: 'sine.inOut',
            });
          }

          // Bee exits swarm area
          const exitEdge = Math.floor(Math.random() * 4);
          let exitX, exitY;

          switch (exitEdge) {
            case 0: // top
              exitX = Math.random() * containerWidth;
              exitY = -margin;
              break;
            case 1: // right
              exitX = containerWidth + margin;
              exitY = Math.random() * containerHeight;
              break;
            case 2: // bottom
              exitX = Math.random() * containerWidth;
              exitY = containerHeight + margin;
              break;
            default: // left
              exitX = -margin;
              exitY = Math.random() * containerHeight;
          }

          swarmTl.to(letter, {
            x: exitX,
            y: exitY,
            opacity: 0,
            scale: 0.2,
            duration: 1.5 + Math.random() * 1.5,
            ease: 'power2.inOut',
          });
        };

        // Start each letter with a random delay for natural swarming
        gsap.delayedCall(Math.random() * 5, createBeeSwarmAnimation);
      });
    }, containerRef);

    return () => ctx.revert();
  }, [isActive, letters]);

  return (
    <div
      ref={containerRef}
      className={`swirling-letters ${className}`}
      style={{
        display: 'none',
        opacity: 0,
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 1,
      }}
    >
      {letters.map((letter, index) => (
        <span
          key={index}
          ref={(el) => {
            if (el) lettersRef.current[index] = el;
          }}
          className="swirl-letter"
        >
          {letter}
        </span>
      ))}
    </div>
  );
};

export default SwirlingLetters;
