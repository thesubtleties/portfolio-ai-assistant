import { useEffect, useRef, useState } from 'react';
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
  const textRef = useRef<HTMLDivElement>(null);
  const measureRef = useRef<HTMLDivElement>(null); // For measuring
  const isAnimatingRef = useRef(false); // Track if animation is running
  const shouldAnimateRef = useRef(false); // Track if we should animate when content is ready
  const splitTextInstanceRef = useRef<any>(null); // Store SplitText instance for proper cleanup

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

  // Calculate top margin based on content length for vertical positioning
  const getTopMargin = (text: string): string => {
    const length = text.length;
    const lineCount = text.split('\n').length;
    const estimatedLines = Math.max(lineCount, Math.ceil(length / 70));

    // Short content: More margin (centered-ish)
    if (estimatedLines <= 3) return '25vh';

    // Medium content: Moderate margin (slightly above center)
    if (estimatedLines <= 10) return '10vh';

    // Long content: Minimal margin (start near top)
    return '5vh';
  };

  // PHASE 1: Prepare content completely before any animation
  useEffect(() => {
    if (!response || typeof window === 'undefined') {
      setPreparedContent(null);
      setIsContentReady(false);
      return;
    }

    console.log('🔧 Preparing content for:', response.substring(0, 50) + '...');

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

    let processedContent = htmlContent.replace(
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

      const ctx = gsap.context(() => {
        // Check if content is already split to prevent double-splitting
        // Look for character spans that SplitText would create
        const existingChars = textRef.current?.querySelectorAll('span');
        const existingPs = textRef.current?.querySelectorAll('p');

        // If we have many more spans than paragraphs, content is likely already split
        // Also check if spans contain single characters (typical of SplitText)
        const singleCharSpans = Array.from(existingChars || []).filter(
          (span) => span.textContent && span.textContent.length === 1
        ).length;

        const isAlreadySplit = singleCharSpans > 10; // If we have 10+ single-char spans, it's split

        console.log('💥 Dissolution - detailed check:', {
          existingChars: existingChars?.length || 0,
          existingPs: existingPs?.length || 0,
          singleCharSpans,
          isAlreadySplit,
          currentHTML: textRef.current?.innerHTML.substring(0, 100) + '...',
        });

        // Only create new SplitText if not already split
        if (!isAlreadySplit) {
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
                  onDissolveComplete?.();
                },
              });
            },
          });
        } else {
          // Content is already split, animate existing characters directly
          console.log(
            '💥 Content already split - animating existing characters'
          );

          // DON'T add animating class - test if that's causing the flicker
          console.log('💥 Skipping animating class to test flicker fix');

          const existingChars = textRef.current?.querySelectorAll('span');
          if (existingChars) {
            return gsap.to(existingChars, {
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
                console.log('💥 Dissolution complete (already split)');
                // No animating class to remove since we didn't add it

                setPreparedContent(null);
                setIsContentReady(false);
                onDissolveComplete?.();
              },
            });
          }
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

    // Log container position/margins before animation
    if (containerRef.current && textRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      const textRect = textRef.current.getBoundingClientRect();
      const containerStyle = getComputedStyle(containerRef.current);
      const textStyle = getComputedStyle(textRef.current);

      console.log('📐 BEFORE animation - Container:', {
        x: containerRect.left,
        y: containerRect.top,
        width: containerRect.width,
        height: containerRect.height,
        marginLeft: containerStyle.marginLeft,
        marginTop: containerStyle.marginTop,
      });

      console.log('📐 BEFORE animation - Text:', {
        x: textRect.left,
        y: textRect.top,
        width: textRect.width,
        height: textRect.height,
        marginLeft: textStyle.marginLeft,
        marginTop: textStyle.marginTop,
      });
    }

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

      splitTextInstanceRef.current = SplitText.create(textRef.current, {
        type: 'chars,words', // Just chars and words - no artificial line containers
        smartWrap: true, // Wraps words in nowrap spans to prevent breaking
        tag: 'span', // Use spans for characters - naturally inline
        // Remove linesClass - let natural paragraph structure handle line breaks
        onSplit(self) {
          console.log(
            '✨ Split complete, animating',
            self.chars.length,
            'characters'
          );

          // Make text visible now that it's split and ready for animation
          gsap.set(textRef.current, {
            opacity: 1,
            visibility: 'visible',
          });

          // Add animating class to reduce paragraph spacing
          textRef.current?.classList.add('animating');

          // Log styles during animation
          if (textRef.current) {
            console.log('🎨 DURING ANIMATION - Inspecting styles...');

            // Log response-text container styles
            const textStyles = getComputedStyle(textRef.current);
            console.log('📦 response-text container styles:', {
              display: textStyles.display,
              margin: textStyles.margin,
              padding: textStyles.padding,
              lineHeight: textStyles.lineHeight,
              fontSize: textStyles.fontSize,
            });

            // Log paragraph styles
            const paragraphs = textRef.current.querySelectorAll('p');
            paragraphs.forEach((p, i) => {
              const pStyles = getComputedStyle(p);
              console.log(`📝 Paragraph ${i} styles:`, {
                display: pStyles.display,
                margin: pStyles.margin,
                padding: pStyles.padding,
                lineHeight: pStyles.lineHeight,
                height: p.getBoundingClientRect().height + 'px',
              });
            });

            // Log character div/span styles (first few)
            const chars = textRef.current.querySelectorAll('div, span');
            const sampleChars = Array.from(chars).slice(0, 5);
            sampleChars.forEach((char, i) => {
              const charStyles = getComputedStyle(char);
              console.log(`🔤 Character ${i} (${char.tagName}) styles:`, {
                display: charStyles.display,
                margin: charStyles.margin,
                padding: charStyles.padding,
                lineHeight: charStyles.lineHeight,
                verticalAlign: charStyles.verticalAlign,
                textContent: char.textContent,
              });
            });
          }

          // Initial scattered state - ensure no initial shift
          gsap.set(self.chars, {
            opacity: 0,
            scale: 0.3,
            x: () => (Math.random() - 0.5) * 250,
            y: () => (Math.random() - 0.5) * 250,
            rotation: () => (Math.random() - 0.5) * 120,
            force3D: true,
            transformOrigin: 'center center', // Consistent transform origin
          });

          return gsap.timeline().to(self.chars, {
            opacity: 1,
            scale: 1,
            x: 0,
            y: 0,
            rotation: 0,
            transformOrigin: 'center center', // Keep consistent
            duration: 1.0,
            ease: 'elastic.out(1, 0.5)', // Gentler elastic bounce
            force3D: true,
            stagger: {
              amount: 0.8, // Faster stagger for smoother flow
              from: 'random',
            },
            onComplete: () => {
              console.log('🎯 BOUNCE ANIMATION COMPLETE!');

              // Log container position/margins after animation
              if (containerRef.current && textRef.current) {
                const containerRect =
                  containerRef.current.getBoundingClientRect();
                const textRect = textRef.current.getBoundingClientRect();
                const containerStyle = getComputedStyle(containerRef.current);
                const textStyle = getComputedStyle(textRef.current);

                console.log('📐 AFTER animation - Container:', {
                  x: containerRect.left,
                  y: containerRect.top,
                  width: containerRect.width,
                  height: containerRect.height,
                  marginLeft: containerStyle.marginLeft,
                  marginTop: containerStyle.marginTop,
                });

                console.log('📐 AFTER animation - Text:', {
                  x: textRect.left,
                  y: textRect.top,
                  width: textRect.width,
                  height: textRect.height,
                  marginLeft: textStyle.marginLeft,
                  marginTop: textStyle.marginTop,
                });
              }

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
      // Manually revert SplitText before context cleanup
      if (splitTextInstanceRef.current) {
        splitTextInstanceRef.current.revert();
        splitTextInstanceRef.current = null; // Clear the reference
      }
      ctx.revert(); // Clean up GSAP animations
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
          dangerouslySetInnerHTML={{ __html: preparedContent.html }}
        />
      )}
    </div>
  );
};

export default ResponseEmergence;
