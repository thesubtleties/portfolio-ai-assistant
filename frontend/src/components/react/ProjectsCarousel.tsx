import { useCallback } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination } from 'swiper/modules';
import type { Swiper as SwiperType } from 'swiper';
import ProjectCard from './ProjectCard';

// Import Swiper styles
import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';

interface Badge {
  image: string;
  alt: string;
  tooltip: string;
}

interface Project {
  id: string;
  title: string;
  description: string;
  tech: string[];
  liveLink?: string;
  githubLink?: string;
  image?: string;
  badge?: Badge;
}

interface ProjectsCarouselProps {
  projects: Project[];
}

export default function ProjectsCarousel({ projects }: ProjectsCarouselProps) {
  // Optimize slide change handler with useCallback
  const handleSlideChange = useCallback((swiper: SwiperType) => {
    // Use requestAnimationFrame for smoother updates
    requestAnimationFrame(() => {
      swiper.update();
    });
  }, []);

  return (
    <Swiper
      modules={[Navigation, Pagination]}
      spaceBetween={40}
      slidesPerView={1}
      centeredSlides={true}
      grabCursor={true}
      initialSlide={0}
      navigation
      pagination={{
        clickable: true,
        dynamicBullets: true,
      }}
      breakpoints={{
        768: {
          slidesPerView: 2,
          spaceBetween: 30,
        },
        1024: {
          slidesPerView: 2,
          spaceBetween: 40,
        },
      }}
      className="projects-swiper"
      slideActiveClass="swiper-slide-active"
      onSlideChange={handleSlideChange}
      style={{
        padding: '20px 0',
      }}
    >
      {projects?.map((project) => (
        <SwiperSlide key={project.id}>
          <ProjectCard project={project} />
        </SwiperSlide>
      ))}
    </Swiper>
  );
}