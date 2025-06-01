import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';

// Register the plugin
gsap.registerPlugin(SplitText);

interface AnimatedDefinitionProps {
  // Add any props you might want to pass in later
  className?: string;
}

const AnimatedDefinition: React.FC<AnimatedDefinitionProps> = ({
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;

    const ctx = gsap.context(() => {
      // Split both lines into characters for typing
      const split1 = new SplitText('.animate-text-1', { type: 'chars' });
      const split2 = new SplitText('.animate-text-2', { type: 'chars' });

      // Set up typing effect for both lines
      gsap.set([...split1.chars, ...split2.chars], {
        opacity: 0,
      });

      // Set delayed content - breathe in below final position
      gsap.set('.delayed-fade', {
        opacity: 0,
        scale: 0.97,
        y: 35, // Start below where it should end up
        transformOrigin: 'center center',
      });

      const tl = gsap.timeline();

      // First line: typing
      tl.to(split1.chars, {
        opacity: 1,
        duration: 0.05,
        ease: 'none',
        stagger: 0.04,
      })

        // Brief pause
        .to({}, { duration: 0.4 })

        // Second line: typing
        .to(split2.chars, {
          opacity: 1,
          duration: 0.05,
          ease: 'none',
          stagger: 0.04,
        })

        // Phase 1: Breathe in (no vertical movement)
        .to('.delayed-fade', {
          opacity: 1,
          scale: 1,
          // y stays at 35 - no movement yet
          duration: 0.8,
          ease: 'sine.out',
          stagger: 0.15,
        })

        // Brief pause - let it sit as static text
        .to({}, { duration: 0.3 })

        // Phase 2: Nudge up to final position
        .to('.delayed-fade', {
          y: 0, // Move to final spot
          duration: 0.4,
          ease: 'power2.out',
          stagger: 0.08,
        });

      return () => {
        split1.revert();
        split2.revert();
      };
    }, containerRef);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={containerRef} className={`dictionary-entry ${className}`}>
      <div className="word-section">
        <h1 className="word">sbtl</h1>
        <span className="pronunciation">/sʌtl/</span>
      </div>

      <div className="part-of-speech">adj.</div>

      <div className="definitions">
        <div className="definition-item">
          <span className="number">1.</span>
          <div className="definition">
            <span className="animate-text-1">
              The art of refined minimalism in digital craftsmanship;{' '}
            </span>
            <span className="animate-text-2">
              attention to microscopic details that collectively create
              exceptional user experiences.
            </span>
          </div>
        </div>

        <div
          className="definition-item delayed-fade"
          style={{ opacity: 0, transform: 'translateY(20px)' }}
        >
          <span className="number">2.</span>
          <p className="definition">
            <span className="italic">tech.</span> The practice of implementing
            thoughtful, delicate interactions that enhance user engagement
            without demanding attention.
          </p>
        </div>

        <div
          className="examples delayed-fade"
          style={{ opacity: 0, transform: 'translateY(20px)' }}
        >
          <p>
            <span className="italic">
              "The sbtl touches in the application's interface created a
              seamless experience that users felt rather than noticed."
            </span>
          </p>
        </div>
      </div>
    </div>
  );
};

export default AnimatedDefinition;
