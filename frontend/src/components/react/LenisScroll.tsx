import { useEffect, useRef } from 'react';
import Lenis from 'lenis';

interface LenisScrollProps {
  enableCarouselScroll?: boolean;
}

const LenisScroll: React.FC<LenisScrollProps> = ({ enableCarouselScroll = true }) => {
  const lenisRef = useRef<Lenis | null>(null);
  const lastScrollTime = useRef<number>(0);

  useEffect(() => {
    // Check if we're on mobile
    const isMobile = window.innerWidth <= 999;
    
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
      duration: 1.2,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      gestureOrientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 0.8,
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

    // Handle carousel scroll interception
    const handleWheel = (e: WheelEvent) => {
      if (!enableCarouselScroll) return;

      // Check if we're in the projects section
      const projectsSection = document.getElementById('projects');
      if (!projectsSection) return;

      const rect = projectsSection.getBoundingClientRect();
      const navbarHeight = 60; // From CSS variable
      const inProjectsView = rect.top <= navbarHeight && rect.bottom >= window.innerHeight - 100;

      if (inProjectsView) {
        // Prevent Lenis from scrolling
        lenis.stop();
        
        // Find swiper instance
        const swiperElement = projectsSection.querySelector('.projects-swiper');
        if (!swiperElement) return;
        
        const swiper = (swiperElement as any).swiper;
        if (!swiper) return;

        // Throttle carousel navigation
        const now = Date.now();
        if (now - lastScrollTime.current < 600) return; // 600ms throttle
        
        const scrollDirection = e.deltaY > 0 ? 'down' : 'up';
        
        if (scrollDirection === 'down') {
          if (swiper.isEnd) {
            // At last slide, resume Lenis and scroll to next section
            lenis.start();
            const contactSection = document.getElementById('contact');
            if (contactSection) {
              lenis.scrollTo(contactSection, { offset: 0 });
            }
          } else {
            swiper.slideNext();
            lastScrollTime.current = now;
          }
        } else {
          if (swiper.isBeginning) {
            // At first slide, resume Lenis and scroll to previous section
            lenis.start();
            const aboutSection = document.getElementById('about');
            if (aboutSection) {
              lenis.scrollTo(aboutSection, { offset: 0 });
            }
          } else {
            swiper.slidePrev();
            lastScrollTime.current = now;
          }
        }
        
        e.preventDefault();
        e.stopPropagation();
      } else {
        // Not in carousel, ensure Lenis is running
        lenis.start();
      }
    };

    // Add wheel listener for carousel control
    if (enableCarouselScroll) {
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