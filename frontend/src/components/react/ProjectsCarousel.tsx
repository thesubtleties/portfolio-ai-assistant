import React from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination } from 'swiper/modules';
import ProjectCard from './ProjectCard';

// Import Swiper styles
import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';

interface Project {
  id: string;
  title: string;
  description: string;
  tech: string[];
  liveLink: string;
  githubLink: string;
  image?: string;
}

interface ProjectsCarouselProps {
  projects: Project[];
}

export default function ProjectsCarousel({ projects }: ProjectsCarouselProps) {
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
      onSlideChange={(swiper) => {
        // Force re-render to update active styles
        swiper.update();
      }}
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
