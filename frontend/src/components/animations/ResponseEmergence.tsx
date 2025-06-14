import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { SplitText } from 'gsap/SplitText';
import { marked } from 'marked';
import { 
  EMERGENCE_DURATION, 
  EMERGENCE_STAGGER, 
  DISSOLUTION_DURATION, 
  DISSOLUTION_STAGGER,
  SCATTER_RANGE_X,
  SCATTER_RANGE_Y,
  SCATTER_ROTATION,
  DISSOLUTION_SCATTER_X,
  DISSOLUTION_SCATTER_Y,
  DISSOLUTION_SCATTER_ROTATION,
  SCATTERED_SCALE,
  FINAL_SCALE,
  EMERGENCE_EASE,
  DISSOLUTION_EASE,
  FORCE_3D,
  TRANSFORM_ORIGIN,
  STAGGER_FROM
} from '../../constants/animations';

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
  const textRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLDivElement>(null); // For measuring
  const isAnimatingRef = useRef(false); // Track if animation is running
  const shouldAnimateRef = useRef(false); // Track if we should animate when content is ready
  const splitTextInstanceRef = useRef<any>(null); // Store SplitText instance for proper cleanup
  const isTextSplitRef = useRef(false); // Reliable flag to track if content is currently split
  const dissolutionStartTimeRef = useRef<number | null>(null); // Track when dissolution started for timing
  const isDissolvingRef = useRef(false); // Flag to prevent new content during dissolution

  // Prepared content state - this stays stable once set
  const [preparedContent, setPreparedContent] = useState<{
    html: string;
    fontSize: string;
    lineHeight: string;
    marginTop: string;
    dimensions: { width: number; height: number };
  } | null>(null);

  const [isContentReady, setIsContentReady] = useState(false);

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
      if (estimatedLines <= 30) return '1.125rem'; // text-lg for very long responses
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

  // Calculate top margin based on content length for vertical positioning
  const getTopMargin = (text: string): string => {
    const length = text.length;
    const lineCount = text.split('\n').length;
    const estimatedLines = Math.max(lineCount, Math.ceil(length / 70));

    // Short content: More margin (centered-ish)
    if (estimatedLines <= 3) return '25vh';

    // Medium content: Moderate margin (slightly above center)
    if (estimatedLines <= 20) return '12vh';

    // Long content: Minimal margin (start near top)
    return '0';
  };

  // PHASE 1: Prepare content completely before any animation
  useEffect(() => {
    if (!response || typeof window === 'undefined') {
      setPreparedContent(null);
      setIsContentReady(false);
      isTextSplitRef.current = false; // Reset split status for new/no content
      if (textRef.current) textRef.current.innerHTML = ''; // Clear textRef content
      if (splitTextInstanceRef.current) {
        splitTextInstanceRef.current.revert(); // Revert old SplitText instance
        splitTextInstanceRef.current = null;
      }
      return;
    }

    console.log('🔧 Preparing content for:', response.substring(0, 50) + '...');

    // If dissolution is happening, wait for it to complete
    if (isDissolvingRef.current) {
      console.log('⏸️ Dissolution in progress, waiting for completion before preparing new content');
      const checkDissolution = () => {
        if (!isDissolvingRef.current) {
          console.log('✅ Dissolution complete, now preparing new content');
          prepareContent();
        } else {
          setTimeout(checkDissolution, 100); // Check every 100ms
        }
      };
      setTimeout(checkDissolution, 100);
      return;
    }

    const prepareContent = () => {

    // Process markdown - more conservative approach
    const processedResponse = response
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
      // Only convert sentence endings followed by new sentences to paragraph breaks
      .replace(/([.!?])\s*\n\s*([A-Z])/g, '$1\n\n$2')
      // Don't aggressively convert list items - let them stay as single breaks
      // .replace(/\n+(-|\*|\d+\.)\s/g, '\n\n$1 ') // REMOVED - was causing extra spacing
      .replace(/\n{3,}/g, '\n\n'); // Normalize excessive breaks only

    const htmlContent = marked(processedResponse, {
      breaks: false,
      gfm: true,
    }) as string;
    
    console.log('🔍 Markdown processing:', {
      input: processedResponse.substring(0, 200),
      output: htmlContent.substring(0, 200)
    });
    
    // Post-process to handle markdown inside HTML elements (like centered divs)
    let finalContent = htmlContent;
    
    // Handle markdown inside <div class='centered'> tags
    finalContent = finalContent.replace(
      /<div class=['"]centered['"]>\s*\n([\s\S]*?)\n\s*<\/div>/g,
      (match, content) => {
        console.log('🔧 Processing markdown inside centered div:', content);
        // Process the content inside the div as markdown
        const processedInner = marked(content.trim(), {
          breaks: false,
          gfm: true,
        }) as string;
        // Remove the wrapping <p> tags that marked adds
        const cleanInner = processedInner.replace(/^<p>(.*)<\/p>$/s, '$1');
        return `<div class='centered'>\n${cleanInner}\n</div>`;
      }
    );

    let processedContent = finalContent.replace(
      /<a href="(https?:\/\/[^"]+)">/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer">'
    );

    processedContent = processedContent.replace(
      /<div class=['"]centered['"]>(.*?)<\/div>/g,
      '<span class="centered">$1</span>'
    );

    // Remove the actual-paragraph class system - we don't need it since we keep split structure
    // processedContent = processedContent.replace(
    //   /<p>/g,
    //   '<p class="actual-paragraph">'
    // );

    // Calculate font sizing and positioning
    const fontSize = getOptimalFontSize(response);
    const lineHeight = getLineHeight(fontSize);
    const marginTop = getTopMargin(response);

    // Measure dimensions using hidden element
    if (measureRef.current) {
      // Apply the same styles that will be used in final render
      measureRef.current.style.fontSize = fontSize;
      measureRef.current.style.lineHeight = lineHeight;
      measureRef.current.style.visibility = 'hidden';
      measureRef.current.style.position = 'absolute';
      measureRef.current.style.top = '-9999px';
      measureRef.current.style.left = '0';

      // Use a reasonable max width instead of container width
      const parentWidth =
        containerRef.current?.parentElement?.offsetWidth || 800;
      measureRef.current.style.width = Math.min(parentWidth - 64, 800) + 'px'; // Account for padding
      measureRef.current.style.maxWidth = '100%';

      measureRef.current.innerHTML = processedContent;

      // Force layout calculation
      const rect = measureRef.current.getBoundingClientRect();

      // Store everything we need
      setPreparedContent({
        html: processedContent,
        fontSize,
        lineHeight,
        marginTop,
        dimensions: {
          width: rect.width,
          height: rect.height,
        },
      });

      // Clean up measurement element
      measureRef.current.innerHTML = '';
      measureRef.current.style.cssText = ''; // Reset all styles

      setIsContentReady(true);
      console.log(
        '✅ Content prepared, dimensions:',
        rect.width,
        'x',
        rect.height
      );
    }
    };

    // Prepare content immediately (dissolution blocking handles race conditions)
    prepareContent();
  }, [response]);

  // PHASE 2: Handle dissolution (before new content)
  useEffect(() => {
    if (
      shouldDissolve &&
      containerRef.current &&
      preparedContent &&
      isContentReady
    ) {
      console.log('💥 Starting dissolution');
      dissolutionStartTimeRef.current = Date.now(); // Track when dissolution starts
      isDissolvingRef.current = true; // Block new content preparation

      const ctx = gsap.context(() => {
        // Use reliable flag to determine if content is already split
        if (isTextSplitRef.current && splitTextInstanceRef.current) {
          console.log('💥 Content already split - animating existing characters via SplitText instance');

          // Animate existing characters directly from the stored SplitText instance
          return gsap.to(splitTextInstanceRef.current.chars, {
            opacity: 0,
            scale: SCATTERED_SCALE,
            x: () => (Math.random() - 0.5) * DISSOLUTION_SCATTER_X,
            y: () => (Math.random() - 0.5) * DISSOLUTION_SCATTER_Y,
            rotation: () => (Math.random() - 0.5) * DISSOLUTION_SCATTER_ROTATION,
            duration: DISSOLUTION_DURATION,
            ease: DISSOLUTION_EASE,
            force3D: FORCE_3D,
            stagger: {
              amount: DISSOLUTION_STAGGER,
              from: STAGGER_FROM,
            },
            onComplete: () => {
              console.log('💥 Dissolution complete (already split)');
              // Clear prepared content and reset split flag after dissolution
              setPreparedContent(null);
              setIsContentReady(false);
              isTextSplitRef.current = false; // Reset for next content
              isDissolvingRef.current = false; // Allow new content preparation
              if (textRef.current) textRef.current.innerHTML = ''; // Clear the DOM
              onDissolveComplete?.();
            },
          });
        } else {
          console.warn('💥 Dissolution - content NOT split, creating SplitText as fallback');
          // Ensure textRef has content before splitting
          if (textRef.current && preparedContent?.html) {
            textRef.current.innerHTML = preparedContent.html;
          }
          splitTextInstanceRef.current = SplitText.create(textRef.current, {
            type: 'chars,words', // Just chars and words - no artificial line containers
            smartWrap: true, // Wraps words in nowrap spans to prevent breaking
            tag: 'span', // Use spans for characters - naturally inline
            // Remove linesClass - let natural paragraph structure handle line breaks
            onSplit(self) {
              // Add animating class for dissolution too
              textRef.current?.classList.add('animating');

              return gsap.to(self.chars, {
                opacity: 0,
                scale: SCATTERED_SCALE,
                x: () => (Math.random() - 0.5) * DISSOLUTION_SCATTER_X,
                y: () => (Math.random() - 0.5) * DISSOLUTION_SCATTER_Y,
                rotation: () => (Math.random() - 0.5) * DISSOLUTION_SCATTER_ROTATION,
                duration: DISSOLUTION_DURATION,
                ease: DISSOLUTION_EASE,
                force3D: FORCE_3D,
                stagger: {
                  amount: DISSOLUTION_STAGGER,
                  from: STAGGER_FROM,
                },
                onComplete: () => {
                  console.log('💥 Dissolution complete');
                  // Remove animating class
                  textRef.current?.classList.remove('animating');

                  // DON'T revert SplitText - keep structure consistent with emergence
                  console.log(
                    '💥 Dissolution complete - keeping split structure'
                  );

                  // Clear prepared content only after dissolution
                  setPreparedContent(null);
                  setIsContentReady(false);
                  isDissolvingRef.current = false; // Allow new content preparation

                  // Clean up GSAP context after dissolution animation
                  // ctx.revert();

                  onDissolveComplete?.();
                },
              });
            },
          });
        }
      }, containerRef);

      return () => {
        // DON'T revert SplitText - keep structure consistent
        console.log('💥 Dissolution cleanup - keeping split structure');
        // if (splitTextInstanceRef.current) {
        //   splitTextInstanceRef.current.revert();
        //   splitTextInstanceRef.current = null; // Clear the reference
        // }
        ctx.revert();
      };
    }
  }, [shouldDissolve, preparedContent, isContentReady, onDissolveComplete]);

  // PHASE 3: Handle emergence animation (only when content is ready)
  useEffect(() => {
    console.log('🔍 Animation effect running:', {
      isActive,
      hasContent: !!preparedContent,
      isReady: isContentReady,
      shouldDissolve,
    });

    // Set animation intent when isActive is true
    if (isActive) {
      shouldAnimateRef.current = true;
    }

    // Wait for content to be prepared
    if (!preparedContent || !isContentReady || shouldDissolve) {
      if (containerRef.current) {
        gsap.set(containerRef.current, {
          opacity: 0,
          visibility: 'hidden',
        });
      }
      return;
    }

    if (!shouldAnimateRef.current) {
      // Show content without animation when not active
      if (containerRef.current) {
        gsap.set(containerRef.current, {
          opacity: 1,
          visibility: 'visible',
        });
      }
      return;
    }

    // Prevent multiple animations from running
    if (isAnimatingRef.current) {
      console.log('⚠️ Animation already running, skipping');
      return;
    }

    console.log('✨ Starting emergence animation');

    isAnimatingRef.current = true;

    const ctx = gsap.context(() => {
      // Pre-lock dimensions based on our measurements
      gsap.set(containerRef.current, {
        opacity: 1,
        visibility: 'visible',
        minHeight: preparedContent.dimensions.height,
        // Don't lock width - let it be flexible
      });

      // Lock text element dimensions more flexibly
      gsap.set(textRef.current, {
        width: '100%',
        minHeight: preparedContent.dimensions.height,
        fontSize: preparedContent.fontSize,
        lineHeight: preparedContent.lineHeight,
        // Ensure no transform shifts
        x: 0,
        y: 0,
        transformOrigin: 'left top', // Anchor to prevent shifts
      });

      // Ensure textRef has content before splitting (manual innerHTML management)
      if (!isTextSplitRef.current && textRef.current && preparedContent?.html) {
        textRef.current.innerHTML = preparedContent.html;
        console.log('✨ Setting innerHTML for new content before splitting');
      }

      splitTextInstanceRef.current = SplitText.create(textRef.current, {
        type: 'chars,words', // Just chars and words - no artificial line containers
        smartWrap: true, // Wraps words in nowrap spans to prevent breaking
        tag: 'span', // Use spans for characters - naturally inline
        // Remove linesClass - let natural paragraph structure handle line breaks
        onSplit(self) {
          isTextSplitRef.current = true; // Mark as split
          console.log(
            '✨ Split complete, animating',
            self.chars.length,
            'characters'
          );

          // Set scattered state FIRST before making anything visible
          gsap.set(self.chars, {
            opacity: 0,
            scale: SCATTERED_SCALE,
            x: () => (Math.random() - 0.5) * SCATTER_RANGE_X,
            y: () => (Math.random() - 0.5) * SCATTER_RANGE_Y,
            rotation: () => (Math.random() - 0.5) * SCATTER_ROTATION,
            force3D: FORCE_3D,
            transformOrigin: TRANSFORM_ORIGIN,
          });

          // NOW make text visible after scattered state is set
          gsap.set(textRef.current, {
            opacity: 1,
            visibility: 'visible',
          });

          // Add animating class to reduce paragraph spacing
          textRef.current?.classList.add('animating');

          return gsap.timeline().to(self.chars, {
            opacity: 1,
            scale: FINAL_SCALE,
            x: 0,
            y: 0,
            rotation: 0,
            transformOrigin: TRANSFORM_ORIGIN,
            duration: EMERGENCE_DURATION,
            ease: EMERGENCE_EASE,
            force3D: FORCE_3D,
            stagger: {
              amount: EMERGENCE_STAGGER,
              from: STAGGER_FROM,
            },
            onComplete: () => {
              console.log('🎯 BOUNCE ANIMATION COMPLETE!');

              isAnimatingRef.current = false; // Clear animation flag
              shouldAnimateRef.current = false; // Clear animation intent

              // Store current layout before clearing transforms to prevent reflow shifts
              let currentLayout: { width: number; height: number } | null =
                null;
              if (textRef.current) {
                const rect = textRef.current.getBoundingClientRect();
                currentLayout = { width: rect.width, height: rect.height };
                console.log('📐 Layout before cleanup:', currentLayout);
              }

              // Clear all GSAP transforms to prevent tiny shifts
              if (textRef.current) {
                gsap.set(textRef.current.querySelectorAll('span'), {
                  clearProps: 'all', // Remove all GSAP properties
                });
                // Also clear any transforms on the text container
                gsap.set(textRef.current, {
                  clearProps: 'transform,x,y,scale,rotation',
                });
              }

              // Remove animating class and revert SplitText
              setTimeout(() => {
                console.log(
                  '🎯 Removing animating class and reverting SplitText'
                );
                if (textRef.current) {
                  // Temporarily lock dimensions during revert to prevent layout shifts
                  if (currentLayout) {
                    textRef.current.style.width = currentLayout.width + 'px';
                    textRef.current.style.minHeight =
                      currentLayout.height + 'px';
                    console.log(
                      '🔒 Temporarily locked dimensions to prevent reflow'
                    );
                  }

                  textRef.current.classList.remove('animating');

                  // DON'T revert SplitText - keep the split structure to prevent layout shifts
                  console.log(
                    '🚀 Keeping split structure to prevent horizontal shifts'
                  );

                  // Log the current split structure we're keeping
                  console.log('🎨 KEEPING SPLIT STRUCTURE - Final state:');
                  const splitChars = textRef.current.querySelectorAll('span');
                  const splitLines =
                    textRef.current.querySelectorAll('.split-line');
                  console.log(
                    `📊 Keeping ${splitChars.length} character spans and ${splitLines.length} split lines`
                  );
                }
              }, 100); // Shorter timeout
            },
          });
        },
      });
    }, containerRef);

    return () => {
      isAnimatingRef.current = false; // Clear flag on cleanup
      shouldAnimateRef.current = false; // Clear animation intent
      // DON'T revert SplitText - keep structure consistent with dissolution
      // if (splitTextInstanceRef.current) {
      //   splitTextInstanceRef.current.revert();
      //   splitTextInstanceRef.current = null; // Clear the reference
      // }
      // ctx.revert(); // Clean up GSAP animations
    };
  }, [isActive, preparedContent, isContentReady]); // Need to respond when content becomes ready

  if (!response) return null;

  return (
    <div
      ref={containerRef}
      className={`response-emergence ${className}`}
      style={{
        opacity: 0,
        visibility: 'hidden',
        pointerEvents: 'auto',
        marginTop: preparedContent?.marginTop || '4rem',
        // Lock container to prevent any layout shifts
        contain: 'layout style',
        transform: 'translateZ(0)',
        willChange: 'transform, opacity',
      }}
    >
      {/* Hidden measurement element */}
      <div
        ref={measureRef}
        className="response-text prose max-w-none"
        style={{
          position: 'absolute',
          visibility: 'hidden',
          top: '-9999px',
          pointerEvents: 'none',
        }}
        aria-hidden="true"
      />

      {/* Actual content - only rendered when prepared */}
      {preparedContent && (
        <div
          ref={textRef}
          className="response-text prose max-w-none [&_a]:font-semibold [&_a]:no-underline [&_a]:cursor-pointer [&_a]:transition-opacity [&_a]:duration-200 [&_a]:pointer-events-auto [&_a]:relative [&_a]:z-10 [&_a]:inline-block [&_a:hover]:opacity-70"
          style={{
            color: 'var(--color-primary)',
            fontSize: preparedContent.fontSize,
            lineHeight: preparedContent.lineHeight,
            width: '100%',
            // Prevent any layout recalculation during animation
            contain: 'layout style',
            transform: 'translateZ(0)',
            willChange: 'transform, opacity',
            // Hide text initially until SplitText processes it
            opacity: 0,
            visibility: 'hidden',
          }}
          // innerHTML is manually managed to preserve SplitText character spans
        />
      )}
    </div>
  );
};

export default ResponseEmergence;