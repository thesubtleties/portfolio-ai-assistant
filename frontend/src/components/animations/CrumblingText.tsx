import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';

gsap.registerPlugin(SplitText);

interface CrumblingTextProps {
  shouldCrumble: boolean;
  onComplete?: () => void;
  className?: string;
}

const CrumblingText: React.FC<CrumblingTextProps> = ({
  shouldCrumble,
  onComplete,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hasCrumbled, setHasCrumbled] = useState(false);

  // Initialize the definition animation on mount - EXACTLY like the original
  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;

    const ctx = gsap.context(() => {
      // Keep container invisible but maintain layout space
      gsap.set(containerRef.current, { opacity: 0 });

      // Split with smartWrap to prevent mid-word breaks and use onSplit
      const split1 = new SplitText(
        containerRef.current.querySelector('.animate-text-1'),
        {
          type: 'chars',
          smartWrap: true,
          onSplit(self) {
            // Hide characters first
            gsap.set(self.chars, {
              opacity: 0,
              force3D: true,
            });

            // Now show container - characters are already hidden
            gsap.set(containerRef.current, {
              opacity: 1,
            });
          },
        }
      );
      const split2 = new SplitText(
        containerRef.current.querySelector('.animate-text-2'),
        {
          type: 'chars',
          smartWrap: true,
          onSplit(self) {
            // Hide characters immediately
            gsap.set(self.chars, {
              opacity: 0,
              force3D: true,
            });
          },
        }
      );

      const allChars = [...split1.chars, ...split2.chars];
      const totalTypingDuration = allChars.length * 0.03; // Slightly faster typing

      gsap.set(containerRef.current.querySelectorAll('.delayed-fade'), {
        opacity: 0,
        scale: 0.98,
        y: 20, // Smaller initial offset
        transformOrigin: 'center center',
        force3D: true, // Force hardware acceleration
      });

      const tl = gsap.timeline();

      // Type the entire first definition with hardware acceleration
      tl.to(allChars, {
        opacity: 1,
        duration: 0.04,
        ease: 'none',
        stagger: 0.03, // Faster stagger
        force3D: true, // Force hardware acceleration
      }).to(
        containerRef.current.querySelectorAll('.delayed-fade'),
        {
          opacity: 1,
          scale: 1,
          y: 0, // Combine the animations for smoother transition
          duration: 0.6, // Shorter duration
          ease: 'power2.out', // Smoother easing
          stagger: 0.08,
          force3D: true, // Force hardware acceleration
        },
        totalTypingDuration * 0.8 // Start later for better overlap
      );

      return () => {
        split1.revert();
        split2.revert();
      };
    }, containerRef);

    return () => ctx.revert();
  }, []);

  // Word animation effect (sbtl) - EXACTLY like the original
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const ctx = gsap.context(() => {
      const wordElement = document.querySelector('.word');
      let currentText = 's'; // Start with 's' already visible

      // Start with 's'
      wordElement.textContent = 's';

      const tl = gsap.timeline({ delay: 0.8 }); // Reduced delay

      // Type out "ubtl" (since 's' is already there)
      ['u', 'b', 't', 'l'].forEach((letter) => {
        tl.call(() => {
          currentText += letter;
          wordElement.textContent = currentText;
        }).to({}, { duration: 0.12 }); // Faster typing
      });

      // Brief pause after typing "subtl"
      tl.to({}, { duration: 0.6 }); // Shorter pause

      // Backspace all the way back to just "s"
      ['l', 't', 'b', 'u'].forEach(() => {
        tl.call(() => {
          currentText = currentText.slice(0, -1);
          wordElement.textContent = currentText;
        }).to({}, { duration: 0.1 }); // Faster backspace
      });

      // Brief pause - "now let me be more precise"
      tl.to({}, { duration: 0.3 }); // Shorter pause

      // Retype "btl"
      ['b', 't', 'l'].forEach((letter) => {
        tl.call(() => {
          currentText += letter;
          wordElement.textContent = currentText;
        }).to({}, { duration: 0.12 }); // Consistent timing
      });
    });

    return () => ctx.revert();
  }, []);

  // Crumbling animation when triggered
  useEffect(() => {
    if (!shouldCrumble || hasCrumbled || !containerRef.current) return;

    const ctx = gsap.context(() => {
      // Split ALL text elements in the definition
      const allElements =
        containerRef.current.querySelectorAll('h1, span, div, p');
      const allSplits: SplitText[] = [];
      const allChars: Element[] = [];

      allElements.forEach((element) => {
        if (element.textContent && element.textContent.trim()) {
          const split = new SplitText(element, {
            type: 'chars,words', // Like ResponseEmergence
            smartWrap: true, // Wraps words in nowrap spans to prevent breaking
            tag: 'span', // Use spans for characters - naturally inline
          });
          allSplits.push(split);
          allChars.push(...split.chars);
        }
      });

      console.log(
        'CrumblingText found',
        allChars.length,
        'characters to animate'
      );

      if (allChars.length === 0) return;

      const tl = gsap.timeline({
        onComplete: () => {
          gsap.set(containerRef.current, {
            display: 'none',
            visibility: 'hidden',
          });
          allSplits.forEach((split) => split.revert());
          setHasCrumbled(true);
          onComplete?.();
        },
      });

      // Subtle random rotation then fall
      allChars.forEach((char) => {
        const trembleDelay = Math.random() * 0.5; // Stagger the rotation start
        const finalRotation = (Math.random() - 0.5) * 4; // Each letter gets unique rotation (-2 to +2 degrees)

        // Stage 1: Gentle rotation to final position
        tl.to(
          char,
          {
            rotation: finalRotation,
            duration: 0.8 + Math.random() * 0.4, // Varied rotation timing
            ease: 'sine.inOut',
            force3D: true,
          },
          trembleDelay
        );

        // Stage 2: Fall immediately after rotation ends
        const rotationEndTime = trembleDelay + (0.8 + Math.random() * 0.4);
        const randomFallRotation = finalRotation + (Math.random() - 0.5) * 120; // Continue from current rotation
        const randomX = (Math.random() - 0.5) * 120;
        const randomY = 150 + Math.random() * 300;

        tl.to(
          char,
          {
            opacity: 0,
            y: randomY,
            x: randomX,
            rotation: randomFallRotation,
            scale: 0.3,
            duration: 0.8 + Math.random() * 0.5,
            ease: 'power1.in',
            force3D: true,
          },
          rotationEndTime
        );

        // Stage 3: Additional tumbling during fall
        tl.to(
          char,
          {
            rotation: `+=${(Math.random() - 0.5) * 180}`,
            duration: 0.4,
            ease: 'none',
            force3D: true,
          },
          rotationEndTime + 0.1
        ); // Start tumbling just after fall begins
      });
    }, containerRef);

    return () => ctx.revert();
  }, [shouldCrumble, hasCrumbled]);

  if (hasCrumbled) return null;

  return (
    <div
      ref={containerRef}
      className={`dictionary-entry ${className}`}
      style={{ opacity: 0 }}
    >
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

export default CrumblingText;
