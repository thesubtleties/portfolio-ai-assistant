import { useEffect, useRef } from 'react';
import Lenis from 'lenis';

interface LenisScrollProps {
  enableCarouselScroll?: boolean;
}

const LenisScroll: React.FC<LenisScrollProps> = ({
  enableCarouselScroll = true,
}) => {
  const lenisRef = useRef<Lenis | null>(null);
  const lastScrollTime = useRef<number>(0);

  useEffect(() => {
    // Check if we're on mobile
    const isMobile = window.innerWidth <= 999;

    // Detect Safari browser
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

    // Detect laptop screens (not large desktops)
    // Laptops typically have width 1000-1600px and height <= 1080px
    const isLaptop =
      window.innerWidth >= 1000 &&
      window.innerWidth <= 1600 &&
      window.innerHeight <= 1080;

    // Initialize Lenis only for desktop
    if (isMobile) {
      // For mobile, just handle anchor links
      const handleAnchorClick = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        const anchor = target.closest('a[href^="#"]');

        if (anchor) {
          e.preventDefault();
          const href = anchor.getAttribute('href');
          if (href && href !== '#') {
            const targetElement = document.querySelector(href);
            if (targetElement) {
              targetElement.scrollIntoView({ behavior: 'smooth' });
            }
          }
        }
      };

      document.addEventListener('click', handleAnchorClick);
      return () => {
        document.removeEventListener('click', handleAnchorClick);
      };
    }

    // Desktop Lenis setup
    const lenis = new Lenis({
      duration: 0.6,
      easing: (t) => 1 - Math.pow(1 - t, 3), // Cubic ease-out (iPhone-style)
      lerp: 0.1,
      orientation: 'vertical',
      gestureOrientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 1,
      touchMultiplier: 2,
      infinite: false,
    });

    lenisRef.current = lenis;

    // Animation loop
    function raf(time: number) {
      lenis.raf(time);
      requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    // Track if we're locked in carousel
    let carouselLocked = false;

    // Handle carousel scroll interception
    const handleWheel = (e: WheelEvent) => {
      if (!enableCarouselScroll) return;

      // Check if we're in the projects section
      const projectsSection = document.getElementById('projects');
      if (!projectsSection) return;

      const rect = projectsSection.getBoundingClientRect();
      const navbarHeight = 60; // From CSS variable
      const inProjectsView =
        rect.top <= navbarHeight && rect.bottom >= window.innerHeight - 100;

      if (inProjectsView) {
        // Find swiper instance
        const swiperElement = projectsSection.querySelector('.projects-swiper');
        if (!swiperElement) return;

        const swiper = (swiperElement as any).swiper;
        if (!swiper) return;

        const scrollDirection = e.deltaY > 0 ? 'down' : 'up';

        // Check if we should exit carousel mode
        if (
          (scrollDirection === 'down' && swiper.isEnd) ||
          (scrollDirection === 'up' && swiper.isBeginning)
        ) {
          // We're at the edge, allow normal scrolling to continue
          if (carouselLocked) {
            carouselLocked = false;
            lenis.start();
          }
          return;
        }

        // We're in carousel mode
        if (!carouselLocked) {
          carouselLocked = true;
          lenis.stop();
        }

        // Throttle carousel navigation
        const now = Date.now();
        if (now - lastScrollTime.current < 200) return; // 200ms throttle to prevent double slides

        if (scrollDirection === 'down') {
          swiper.slideNext();
        } else {
          swiper.slidePrev();
        }
        lastScrollTime.current = now;

        e.preventDefault();
        e.stopPropagation();
      } else {
        // Not in carousel view
        if (carouselLocked) {
          carouselLocked = false;
          lenis.start();
        }
      }
    };

    // Add wheel listener for carousel control (not on laptops due to trackpad issues)
    if (enableCarouselScroll && !isLaptop) {
      window.addEventListener('wheel', handleWheel, { passive: false });
    }

    // Handle anchor links
    const handleAnchorClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const anchor = target.closest('a[href^="#"]');

      if (anchor) {
        e.preventDefault();
        const href = anchor.getAttribute('href');
        if (href && href !== '#') {
          // Exit carousel mode if we're in it
          if (carouselLocked) {
            carouselLocked = false;
            lenis.start();
          }

          const targetElement = document.querySelector(href);
          if (targetElement) {
            lenis.scrollTo(targetElement as HTMLElement, { offset: 0 });
          }
        }
      }
    };

    document.addEventListener('click', handleAnchorClick);

    // Cleanup
    return () => {
      lenis.destroy();
      window.removeEventListener('wheel', handleWheel);
      document.removeEventListener('click', handleAnchorClick);
    };
  }, [enableCarouselScroll]);

  return null;
};

export default LenisScroll;
