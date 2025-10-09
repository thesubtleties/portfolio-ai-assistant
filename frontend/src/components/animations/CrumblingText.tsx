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

  // Initialize the definition animation on mount - Simple fade-in instead of typing
  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) return;

    // Wait for all fonts to load before starting animation
    const startAnimation = async () => {
      try {
        // Wait for both Crimson Text (definition text) and Inter (pronunciation) to load
        await Promise.all([
          document.fonts.load('1rem "Crimson Text"'),
          document.fonts.load('1rem "Inter"')
        ]);
      } catch (error) {
        console.warn('Font loading timeout, proceeding with animation:', error);
      }

      const ctx = gsap.context(() => {
        // Set initial states with perspective for depth
        gsap.set(containerRef.current, {
          opacity: 1,
          perspective: 1000, // Add perspective for z-axis movement
          transformStyle: 'preserve-3d'
        });
      
      // Hide text elements with different initial states
      // Number "1." and both parts of definition 1 animate together from depth
      gsap.set(containerRef.current.querySelectorAll('.definition-item:first-child .number, .animate-text-1, .animate-text-2'), {
        opacity: 0,
        z: -100, // Start further back in z-space
        scale: 0.95, // Slightly smaller to enhance depth effect
        filter: 'blur(2px)', // Subtle blur for depth
        force3D: true,
      });

      gsap.set(containerRef.current.querySelectorAll('.delayed-fade'), {
        opacity: 0,
        scale: 0.98,
        y: 20,
        transformOrigin: 'center center',
        force3D: true,
      });

      const tl = gsap.timeline({ delay: 0.3 }); // Small initial pause for that premium feel

      // Number "1." and both definition parts fade from depth together - like lifting the first layer
      tl.to(containerRef.current.querySelectorAll('.definition-item:first-child .number, .animate-text-1, .animate-text-2'), {
        opacity: 1,
        z: 0,
        scale: 1,
        filter: 'blur(0px)',
        duration: 1.4, // Slower, more deliberate
        ease: 'power2.out',
        force3D: true,
      })
      .to(
        containerRef.current.querySelectorAll('.delayed-fade'),
        {
          opacity: 1,
          scale: 1,
          y: 0,
          duration: 0.6,
          ease: 'power2.out',
          stagger: 0.08,
          force3D: true,
        },
        "-=0.4" // Overlap with text fade-in
      );
      }, containerRef);

      return () => ctx.revert();
    };

    startAnimation();

    // No cleanup needed for async function
    return undefined;
  }, []);

  // Word animation effect (sbtl) - REMOVED typing animation, just show immediately
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const wordElement = document.querySelector('.word');
    if (wordElement) {
      // Just set the text immediately
      wordElement.textContent = 'sbtl';
    }
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

      // Clean tumble and fall - no shake, just natural crumbling
      allChars.forEach((char) => {
        const fallDelay = 0.3 + Math.random() * 0.1; // Small delay before fall (0.1-0.2s)
        const randomRotation = (Math.random() - 0.5) * 120;
        const randomX = (Math.random() - 0.5) * 120;
        const randomY = 150 + Math.random() * 300;

        // Stage 1: Fall with initial rotation
        tl.to(
          char,
          {
            opacity: 0,
            y: randomY,
            x: randomX,
            rotation: randomRotation,
            scale: 0.3,
            duration: 1.0 + Math.random() * 0.6,
            ease: 'power1.in',
            force3D: true,
          },
          fallDelay
        );

        // Stage 2: Additional tumbling during fall for natural physics
        tl.to(
          char,
          {
            rotation: `+=${(Math.random() - 0.5) * 180}`,
            duration: 0.4,
            ease: 'none',
            force3D: true,
          },
          fallDelay + 0.1
        );
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
