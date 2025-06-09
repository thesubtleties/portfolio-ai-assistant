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
      // Show the container first
      gsap.set(containerRef.current, { visibility: 'visible' });

      // Split with smartWrap to prevent mid-word breaks
      const split1 = new SplitText(
        containerRef.current.querySelector('.animate-text-1'),
        {
          type: 'chars',
          smartWrap: true,
        }
      );
      const split2 = new SplitText(
        containerRef.current.querySelector('.animate-text-2'),
        {
          type: 'chars',
          smartWrap: true,
        }
      );

      const allChars = [...split1.chars, ...split2.chars];
      const totalTypingDuration = allChars.length * 0.03; // Slightly faster typing

      // Set up initial states with hardware acceleration
      gsap.set(allChars, {
        opacity: 0,
        force3D: true, // Force hardware acceleration
      });

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
      let currentText = '';

      // Start empty
      wordElement.textContent = '';

      const tl = gsap.timeline({ delay: 0.8 }); // Reduced delay

      // Type out "subtl"
      ['s', 'u', 'b', 't', 'l'].forEach((letter) => {
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
            type: 'chars',
            smartWrap: true,
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

      // Smoother crumbling animation with better timing
      allChars.forEach((char) => {
        const trembleDelay = Math.random() * 0.3; // Shorter delay spread
        const fallDelay = 0.5 + Math.random() * 0.4; // Start falling sooner

        // Stage 1: Quick trembles with hardware acceleration
        tl.to(
          char,
          {
            x: () => (Math.random() - 0.5) * 3,
            y: () => (Math.random() - 0.5) * 3,
            rotation: () => (Math.random() - 0.5) * 4,
            duration: 0.08,
            ease: 'none',
            repeat: 2 + Math.floor(Math.random() * 3), // Fewer repeats
            yoyo: true,
            force3D: true, // Force hardware acceleration
          },
          trembleDelay
        );

        // Stage 2: Fall with smoother physics and hardware acceleration
        const randomRotation = (Math.random() - 0.5) * 120; // Less extreme rotation
        const randomX = (Math.random() - 0.5) * 120;
        const randomY = 150 + Math.random() * 300;

        tl.to(
          char,
          {
            opacity: 0,
            y: randomY,
            x: randomX,
            rotation: randomRotation,
            scale: 0.3,
            duration: 0.8 + Math.random() * 0.5, // Shorter, more consistent duration
            ease: 'power1.in', // Gentler easing
            force3D: true, // Force hardware acceleration
          },
          fallDelay
        );

        // Stage 3: Subtle tumbling (overlapping with fall) with hardware acceleration
        tl.to(
          char,
          {
            rotation: `+=${(Math.random() - 0.5) * 180}`,
            duration: 0.4,
            ease: 'none',
            force3D: true, // Force hardware acceleration
          },
          fallDelay + 0.1
        ); // Start tumbling almost immediately
      });
    }, containerRef);

    return () => ctx.revert();
  }, [shouldCrumble, hasCrumbled, onComplete]);

  if (hasCrumbled) return null;

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

export default CrumblingText;
