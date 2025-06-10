import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';
import { marked } from 'marked';

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

  // Calculate optimal font size based on response length - targeting 100% height usage
  const getOptimalFontSize = (text: string): string => {
    const length = text.length;
    const lineCount = text.split('\n').length;
    const estimatedLines = Math.max(lineCount, Math.ceil(length / 70)); // ~70 chars per line (more generous)

    // Check if we're on mobile
    const isMobile = typeof window !== 'undefined' && window.innerWidth <= 768;

    if (isMobile) {
      // Mobile-specific font sizes (smaller to fit more content)
      if (estimatedLines <= 3) return '1.5rem'; // text-2xl for short responses
      if (estimatedLines <= 6) return '1.25rem'; // text-xl for medium responses
      if (estimatedLines <= 12) return '1.125rem'; // text-lg for longer responses
      if (estimatedLines <= 20) return '1rem'; // text-base for very long responses
      if (estimatedLines <= 30) return '0.875rem'; // text-sm for extremely long responses
      return '0.75rem'; // text-xs for massive responses
    } else {
      // Desktop font sizes (larger for better visibility)
      if (estimatedLines <= 4) return '1.875rem'; // text-3xl for short responses
      if (estimatedLines <= 8) return '1.5rem'; // text-2xl for medium responses
      if (estimatedLines <= 15) return '1.25rem'; // text-xl for longer responses
      if (estimatedLines <= 25) return '1.125rem'; // text-lg for very long responses
      if (estimatedLines <= 35) return '1rem'; // text-base for extremely long responses
      return '0.875rem'; // text-sm for massive responses
    }
  };

  // Calculate line height based on font size
  const getLineHeight = (fontSize: string): string => {
    const sizeMap: { [key: string]: string } = {
      '1.875rem': '2.25rem', // leading-9 for text-3xl
      '1.5rem': '2rem', // leading-8 for text-2xl
      '1.25rem': '1.75rem', // leading-7 for text-xl
      '1.125rem': '1.75rem', // leading-7 for text-lg
      '1rem': '1.5rem', // leading-6 for text-base
      '0.875rem': '1.25rem', // leading-5 for text-sm
      '0.75rem': '1rem', // leading-4 for text-xs
    };
    return sizeMap[fontSize] || '1.5rem';
  };

  // Handle dissolution separately
  useEffect(() => {
    if (shouldDissolve && containerRef.current && response) {
      const ctx = gsap.context(() => {
        // Use new v3.13.0+ onSplit approach for dissolution too
        SplitText.create(textRef.current, {
          type: 'chars,words,lines',
          smartWrap: true,
          tag: 'span',
          ignore: 'a',
          onSplit(self) {
            // Return dissolution animation for SplitText to manage
            return gsap.to(self.chars, {
              opacity: 0,
              scale: 0.3,
              x: () => (Math.random() - 0.5) * 300,
              y: () => (Math.random() - 0.5) * 300,
              rotation: () => (Math.random() - 0.5) * 180,
              duration: 1.0,
              ease: 'power2.in',
              force3D: true,
              stagger: {
                amount: 0.8,
                from: 'random',
              },
              onComplete: () => {
                onDissolveComplete?.();
              },
            });
          }
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

      // Use new v3.13.0+ onSplit approach for better timing
      SplitText.create(textRef.current, {
        type: 'chars,words,lines',
        smartWrap: true,
        tag: 'span',
        ignore: 'a',
        onSplit(self) {
          // Animation runs exactly when split is ready - no timing issues!
          console.log('Split chars:', self.chars.length, 'elements');

          // Initial state - characters scattered but closer with hardware acceleration
          gsap.set(self.chars, {
            opacity: 0,
            scale: 0.3,
            x: () => (Math.random() - 0.5) * 250,
            y: () => (Math.random() - 0.5) * 250,
            rotation: () => (Math.random() - 0.5) * 120,
            force3D: true, // Force hardware acceleration
          });

          // Return the animation timeline for SplitText to manage
          return gsap.timeline({
            onComplete: () => {
              onComplete?.();
            },
          })
            // Smoother emergence with better overlap and hardware acceleration
            .to(self.chars, {
              opacity: 0.7,
              scale: 0.6,
              x: () => (Math.random() - 0.5) * 80,
              y: () => (Math.random() - 0.5) * 80,
              rotation: () => (Math.random() - 0.5) * 60,
              duration: 0.8,
              ease: 'power2.out',
              force3D: true,
              stagger: {
                amount: 1.2,
                from: 'random',
              },
            })
            // Quick converge with hardware acceleration
            .to(
              self.chars,
              {
                opacity: 0.9,
                scale: 0.85,
                x: () => (Math.random() - 0.5) * 25,
                y: () => (Math.random() - 0.5) * 25,
                rotation: () => (Math.random() - 0.5) * 20,
                duration: 0.7,
                ease: 'sine.inOut',
                force3D: true,
                stagger: {
                  amount: 1.0,
                  from: 'random',
                },
              },
              0.6
            )
            // Final settle with bounce and hardware acceleration
            .to(
              self.chars,
              {
                opacity: 1,
                scale: 1,
                x: 0,
                y: 0,
                rotation: 0,
                duration: 0.9,
                ease: 'back.out(1.2)',
                force3D: true,
                stagger: {
                  amount: 1.2,
                  from: 'random',
                },
              },
              1.0
            );
        }
      });

      // Don't revert split to avoid layout shift after animation
      return () => {
        // split.revert(); // Commented out to prevent layout jump
      };
    }, containerRef);

    return () => ctx.revert();
  }, [isActive, response, onComplete]);

  if (!response) return null;

  // Pre-process response to ensure comfortable paragraph spacing
  const processedResponse = response
    // First, normalize all line breaks to single \n
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    
    // Convert obvious paragraph breaks (sentence endings followed by new sentences)
    .replace(/([.!?])\s*\n\s*([A-Z])/g, '$1\n\n$2')
    
    // Convert colons followed by new content to paragraph breaks
    .replace(/([:])\s*\n\s*([A-Z])/g, '$1\n\n$2')
    
    // Ensure list items have proper spacing (but not double spacing between items)
    .replace(/\n+(-|\*|\d+\.)\s/g, '\n\n$1 ')
    
    // Convert any sequence of 3+ line breaks to just 2 (paragraph break)
    .replace(/\n{3,}/g, '\n\n')
    
    // Ensure code blocks have proper spacing
    .replace(/\n+(```)/g, '\n\n$1')
    .replace(/(```)\n+/g, '$1\n\n');

  // Parse markdown to HTML with proper paragraph handling
  const htmlContent = marked(processedResponse, {
    breaks: false, // Turn OFF automatic line break conversion - key fix!
    gfm: true,
  }) as string;

  // Add target="_blank" to external links and process custom formatting
  let processedContent = htmlContent.replace(
    /<a href="(https?:\/\/[^"]+)">/g,
    '<a href="$1" target="_blank" rel="noopener noreferrer">'
  );

  // Convert <div class='centered'> to proper centered spans
  processedContent = processedContent.replace(
    /<div class=['"]centered['"]>(.*?)<\/div>/g,
    '<span class="centered">$1</span>'
  );

  // Calculate dynamic font size based on response length
  const fontSize = getOptimalFontSize(response);
  const lineHeight = getLineHeight(fontSize);

  return (
    <div
      ref={containerRef}
      className={`response-emergence ${className}`}
      style={{ display: 'none', opacity: 0, pointerEvents: 'auto' }}
    >
      <div
        ref={textRef}
        className="response-text prose max-w-none [&_a]:font-semibold [&_a]:no-underline [&_a]:cursor-pointer [&_a]:transition-opacity [&_a]:duration-200 [&_a]:pointer-events-auto [&_a]:relative [&_a]:z-10 [&_a]:inline-block [&_a:hover]:opacity-70"
        style={{
          color: 'var(--color-primary)',
          fontSize: fontSize,
          lineHeight: lineHeight,
        }}
        dangerouslySetInnerHTML={{ __html: processedContent }}
      />
    </div>
  );
};

export default ResponseEmergence;
