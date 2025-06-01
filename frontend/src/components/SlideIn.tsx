import React from 'react';
import { useInView } from 'react-intersection-observer';

interface SlideInProps {
  children: React.ReactNode;
  delay?: number;
  direction?: 'left' | 'right';
  distance?: number;
}

const SlideIn: React.FC<SlideInProps> = ({
  children,
  delay = 0,
  direction = 'left',
  distance = 50,
}) => {
  const { ref, inView } = useInView({
    triggerOnce: true,
    threshold: 0.1,
  });

  return (
    <div
      ref={ref}
      style={{
        opacity: inView ? 1 : 0,
        transform: inView
          ? 'translateX(0)'
          : `translateX(${direction === 'left' ? -distance : distance}px)`,
        transition: `all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) ${delay}s`,
      }}
    >
      {children}
    </div>
  );
};

export default SlideIn;
