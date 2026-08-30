import React from 'react';
import { motion } from 'motion/react';
import bgImg from '../assets/images/studio_bg_hd.png';

export const BackgroundBeams: React.FC = () => {
  // Independent vertical light beams configuration
  const beams = [
    { left: '6%', width: '45px', delay: 0, duration: 11, opacity: 0.45, blur: '35px' },
    { left: '16%', width: '60px', delay: 2, duration: 15, opacity: 0.65, blur: '45px' },
    { left: '26%', width: '50px', delay: 4, duration: 13, opacity: 0.5, blur: '40px' },
    { left: '38%', width: '70px', delay: 1, duration: 17, opacity: 0.75, blur: '55px' },
    { left: '50%', width: '85px', delay: 3, duration: 14, opacity: 0.6, blur: '50px' },
    { left: '64%', width: '70px', delay: 2.5, duration: 18, opacity: 0.75, blur: '55px' },
    { left: '76%', width: '55px', delay: 4.5, duration: 12, opacity: 0.5, blur: '40px' },
    { left: '86%', width: '65px', delay: 1.5, duration: 16, opacity: 0.65, blur: '50px' },
    { left: '94%', width: '45px', delay: 3.5, duration: 14, opacity: 0.4, blur: '35px' },
  ];

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0 bg-black select-none">
      {/* 1. Base Crystal Clear HD Studio Background */}
      <img
        src={bgImg}
        alt="Studio Background"
        className="absolute inset-0 w-full h-full object-cover object-center"
        loading="eager"
      />

      {/* 2. Dynamic Vertical Moving Light Beams */}
      {beams.map((beam, i) => (
        <motion.div
          key={i}
          className="absolute top-0 bottom-0 pointer-events-none mix-blend-screen"
          style={{
            left: beam.left,
            width: beam.width,
            filter: `blur(${beam.blur})`,
            background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(10,26,92,0.7) 25%, rgba(48,84,255,0.95) 50%, rgba(10,26,92,0.7) 75%, rgba(0,0,0,0) 100%)',
          }}
          animate={{
            y: ['-12%', '12%', '-12%'],
            opacity: [beam.opacity * 0.5, beam.opacity, beam.opacity * 0.5],
            scaleX: [1, 1.25, 1],
          }}
          transition={{
            duration: beam.duration,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: beam.delay,
          }}
        />
      ))}

      {/* 3. Ambient Volumetric Breathing Glow (Center & Floor) */}
      <motion.div 
        className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[850px] h-[550px] rounded-full pointer-events-none mix-blend-screen"
        style={{
          background: 'radial-gradient(circle, rgba(48,84,255,0.3) 0%, rgba(10,26,92,0.15) 50%, rgba(0,0,0,0) 80%)',
          filter: 'blur(80px)',
        }}
        animate={{
          scale: [0.95, 1.12, 0.95],
          opacity: [0.6, 0.9, 0.6],
        }}
        transition={{
          duration: 7,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />

      {/* 4. Floor Dynamic Blue Spotlight Pulse */}
      <motion.div
        className="absolute bottom-4 left-1/2 -translate-x-1/2 w-4/5 max-w-4xl h-24 rounded-full pointer-events-none mix-blend-screen"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(48,84,255,0.5) 0%, rgba(10,26,92,0.2) 60%, transparent 80%)',
          filter: 'blur(30px)',
        }}
        animate={{
          opacity: [0.5, 0.85, 0.5],
          scaleX: [0.95, 1.08, 0.95],
        }}
        transition={{
          duration: 5,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
      />
    </div>
  );
};
