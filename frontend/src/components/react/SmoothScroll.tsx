import { useEffect, useRef, useState } from 'react';

interface SmoothScrollProps {
  scrollSensitivity?: number;
  debounceTime?: number;
  scrollThreshold?: number;
  animationDuration?: number;
}

const SmoothScroll: React.FC<SmoothScrollProps> = ({
  scrollSensitivity = 5,
  debounceTime = 10,
  scrollThreshold = 20,
  animationDuration = 1000,
}) => {
  const isScrollingRef = useRef<boolean>(false);
  const scrollTimeout = useRef<NodeJS.Timeout>();
  const accumulatedDeltaRef = useRef<number>(0);
  const [isMobile, setIsMobile] = useState<boolean>(false);

  useEffect(() => {
    const checkMobile = (): void => {
      setIsMobile(window.innerWidth <= 999);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (isMobile) {
      document.documentElement.style.scrollSnapType = 'none';
      return;
    }

    const preventScroll = (e: WheelEvent): boolean => {
      if (isScrollingRef.current) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }
      return true;
    };

    const handleWheel = (e: WheelEvent): boolean => {
      if (isScrollingRef.current) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }

      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }

      accumulatedDeltaRef.current += Math.abs(e.deltaY);

      scrollTimeout.current = setTimeout(() => {
        if (accumulatedDeltaRef.current > scrollSensitivity) {
          const sections = document.querySelectorAll<HTMLElement>('section');
          const scrollPosition = window.scrollY;

          let targetSection: HTMLElement | null = null;
          let minDistance = Infinity;

          sections.forEach((section) => {
            const rect = section.getBoundingClientRect();
            const sectionTop = rect.top + scrollPosition;
            const distance =
              e.deltaY > 0
                ? sectionTop - scrollPosition
                : scrollPosition - sectionTop;

            if (distance > 0 && distance < minDistance) {
              minDistance = distance;
              targetSection = section;
            }
          });

          if (
            targetSection &&
            Math.abs(targetSection.getBoundingClientRect().top) >
              scrollThreshold
          ) {
            isScrollingRef.current = true;

            window.addEventListener('wheel', preventScroll, { passive: false });

            targetSection.scrollIntoView({
              behavior: 'smooth',
              block: 'start',
            });

            setTimeout(() => {
              isScrollingRef.current = false;
              window.removeEventListener('wheel', preventScroll);
            }, animationDuration);
          }
        }

        accumulatedDeltaRef.current = 0;
      }, debounceTime);

      return true;
    };

    if (!isMobile) {
      window.addEventListener('wheel', handleWheel, { passive: false });
      document.documentElement.style.scrollSnapType = 'y proximity';
      const sections = document.querySelectorAll<HTMLElement>('section');
      sections.forEach((section) => {
        section.style.scrollSnapAlign = 'start';
      });
    }

    return () => {
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('wheel', preventScroll);
      if (scrollTimeout.current) {
        clearTimeout(scrollTimeout.current);
      }
    };
  }, [
    scrollSensitivity,
    debounceTime,
    scrollThreshold,
    animationDuration,
    isMobile,
  ]);

  return null;
};

export default SmoothScroll;
