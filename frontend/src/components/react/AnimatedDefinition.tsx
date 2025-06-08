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
      // Show the container first
      gsap.set(containerRef.current, { visibility: 'visible' });

      // Split with smartWrap to prevent mid-word breaks
      const split1 = new SplitText(
        containerRef.current.querySelector('.animate-text-1'),
        {
          type: 'chars',
          smartWrap: true, // This keeps words together!
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
      const totalTypingDuration = allChars.length * 0.04;

      // Set up initial states
      gsap.set(allChars, {
        opacity: 0,
      });

      gsap.set(containerRef.current.querySelectorAll('.delayed-fade'), {
        opacity: 0,
        scale: 0.97,
        y: 35,
        transformOrigin: 'center center',
      });

      const tl = gsap.timeline();

      // Type the entire first definition
      tl.to(allChars, {
        opacity: 1,
        duration: 0.05,
        ease: 'none',
        stagger: 0.04,
      })

        // Rest of animation
        .to(
          containerRef.current.querySelectorAll('.delayed-fade'),
          {
            opacity: 1,
            scale: 1,
            duration: 0.8,
            ease: 'sine.out',
            stagger: 0.12,
          },
          totalTypingDuration * 0.7
        )

        .to(
          containerRef.current.querySelectorAll('.delayed-fade'),
          {
            y: 0,
            duration: 0.4,
            ease: 'power2.out',
            stagger: 0.08,
          },
          totalTypingDuration - 0.4
        );

      return () => {
        split1.revert();
        split2.revert();
      };
    }, containerRef);

    return () => ctx.revert();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const ctx = gsap.context(() => {
      const wordElement = document.querySelector('.word');
      let currentText = '';

      // Start empty
      wordElement.textContent = '';

      const tl = gsap.timeline({ delay: 1 });

      // Type out "subtl"
      ['s', 'u', 'b', 't', 'l'].forEach((letter) => {
        tl.call(() => {
          currentText += letter;
          wordElement.textContent = currentText;
        }).to({}, { duration: 0.15 });
      });

      // Brief pause after typing "subtl"
      tl.to({}, { duration: 0.8 });

      // Backspace all the way back to just "s"
      // Remove 'l'
      tl.call(() => {
        currentText = currentText.slice(0, -1);
        wordElement.textContent = currentText; // "subt"
      })
        .to({}, { duration: 0.12 })
        // Remove 't'
        .call(() => {
          currentText = currentText.slice(0, -1);
          wordElement.textContent = currentText; // "sub"
        })
        .to({}, { duration: 0.12 })
        // Remove 'b'
        .call(() => {
          currentText = currentText.slice(0, -1);
          wordElement.textContent = currentText; // "su"
        })
        .to({}, { duration: 0.12 })
        // Remove 'u'
        .call(() => {
          currentText = currentText.slice(0, -1);
          wordElement.textContent = currentText; // "s"
        })
        .to({}, { duration: 0.12 })

        // Brief pause - "now let me be more precise"
        .to({}, { duration: 0.4 })

        // Retype "btl"
        .call(() => {
          currentText += 'b';
          wordElement.textContent = currentText; // "sb"
        })
        .to({}, { duration: 0.15 })
        .call(() => {
          currentText += 't';
          wordElement.textContent = currentText; // "sbt"
        })
        .to({}, { duration: 0.15 })
        .call(() => {
          currentText += 'l';
          wordElement.textContent = currentText; // "sbtl"
        });
    });

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
