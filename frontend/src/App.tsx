import React, { useEffect, useRef } from 'react';
import { motion } from 'motion/react';
import Hls from 'hls.js';
import { ShoppingCart, MessageCircle } from 'lucide-react';
import robotImg from './assets/images/raya_robot_hd.png';

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const videoSrc = "https://stream.mux.com/T6oQJQ02cQ6N01TR6iHwZkKFkbepS34dkkIc9iukgy400g.m3u8";

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (Hls.isSupported()) {
      const hls = new Hls({ enableWorker: true });
      hls.loadSource(videoSrc);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch((e) => console.log("Auto-play prevented:", e));
      });
      return () => {
        hls.destroy();
      };
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = videoSrc;
      video.addEventListener("loadedmetadata", () => {
        video.play().catch((e) => console.log("Auto-play prevented:", e));
      });
    }
  }, []);

  return (
    <div className="relative bg-[#000000] text-white min-h-screen flex flex-col justify-between overflow-hidden font-sans select-none px-4">
      {/* 1. Minimal Top Navbar with Sunburst Icon + RAYA SHOP */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-transparent px-6 sm:px-10 py-5 flex items-center">
        <a href="/" className="flex items-center gap-3 text-white focus:outline-none group">
          {/* Sunburst Icon (24x24px SVG) */}
          <div className="w-6 h-6 flex items-center justify-center text-white">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" fill="currentColor"/>
              <path d="M12 2v2"/>
              <path d="M12 20v2"/>
              <path d="m4.93 4.93 1.41 1.41"/>
              <path d="m17.66 17.66 1.41 1.41"/>
              <path d="M2 12h2"/>
              <path d="M20 12h2"/>
              <path d="m6.34 17.66-1.41 1.41"/>
              <path d="m19.07 4.93-1.41 1.41"/>
            </svg>
          </div>
          <span className="font-black tracking-wider text-xl sm:text-2xl text-white uppercase font-sans">
            RAYA SHOP
          </span>
        </a>
      </header>

      {/* 2. Background Video Layer */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
        <video
          ref={videoRef}
          muted
          loop
          playsInline
          autoPlay
          poster="https://images.unsplash.com/photo-1647356191320-d7a1f80ca777?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhYnN0cmFjdCUyMGRhcmslMjB0ZWNobm9sb2d5JTIwbmV1cmFsJTIwbmV0d29ya3xlbnwxfHx8fDE3Njg5NzIyNTV8MA&ixlib=rb-4.1.0&q=80&w=1080"
          className="w-full h-full object-cover opacity-60"
        />

        {/* Video Overlay */}
        <div className="absolute inset-0 bg-black/60 backdrop-blur-[2px]" />

        {/* Decorative Gradients */}
        <div className="absolute top-[-20%] left-[20%] w-[600px] h-[600px] rounded-full bg-blue-900/20 blur-[120px] mix-blend-screen pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[20%] w-[500px] h-[500px] rounded-full bg-indigo-900/20 blur-[120px] mix-blend-screen pointer-events-none" />
      </div>

      {/* 3. Hero Content (Centered) */}
      <main className="relative z-10 max-w-4xl mx-auto w-full flex flex-col items-center text-center pt-24 sm:pt-28 pb-8 my-auto">
        {/* Top AI Agent Robot with Gentle Float & Interactive Hover Motion */}
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="relative mb-3 cursor-pointer group"
        >
          {/* Subtle Glow behind Robot */}
          <div className="absolute -inset-4 rounded-full bg-gradient-to-r from-[#3054ff] to-[#4d7cff] opacity-35 blur-xl group-hover:opacity-80 group-hover:blur-2xl transition-all duration-500" />

          {/* Floating Robot Container */}
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            whileHover={{ 
              scale: 1.10, 
              y: -14,
              transition: { type: 'spring', stiffness: 350, damping: 20 }
            }}
            whileTap={{ scale: 0.95 }}
            className="relative w-36 h-44 sm:w-44 sm:h-52 md:w-52 md:h-60 flex items-center justify-center filter drop-shadow-[0_15px_30px_rgba(0,0,0,0.8)] group-hover:drop-shadow-[0_0_40px_rgba(48,84,255,0.9)] transition-all duration-300"
          >
            <img
              src={robotImg}
              alt="Raya AI Shopping Assistant"
              className="w-full h-full object-contain select-none pointer-events-none"
              loading="eager"
            />
          </motion.div>
        </motion.div>

        {/* Headlines */}
        <div className="space-y-1 sm:space-y-2 max-w-3xl mx-auto">
          {/* Line 1: RayaShop Agent */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-4xl sm:text-6xl md:text-7xl lg:text-[76px] font-extrabold tracking-tight text-white leading-[1.05] drop-shadow-[0_0_35px_rgba(255,255,255,0.3)] font-sans"
          >
            RayaShop Agent
          </motion.h1>

          {/* Line 2: For Smarter Shopping */}
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-3xl sm:text-5xl md:text-6xl lg:text-[64px] font-extrabold tracking-tight text-[#4d7cff] leading-[1.05] drop-shadow-[0_0_35px_rgba(77,124,255,0.9)] font-sans"
          >
            For Smarter Shopping
          </motion.h2>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.8 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="pt-2 text-base sm:text-lg md:text-xl text-white font-normal max-w-xl mx-auto leading-relaxed"
          >
            One request. Thousands of products. The right choice for you
          </motion.p>
        </div>

        {/* CTA Buttons (Both on 1 line, both with white background) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-8 sm:mt-10 flex flex-row items-center justify-center gap-4 sm:gap-6 w-full max-w-xl mx-auto"
        >
          {/* Button 1: Official Store */}
          <a
            href="https://www.rayashop.com/en"
            target="_blank"
            rel="noopener noreferrer"
            className="group relative flex items-center justify-between gap-4 px-6 sm:px-7 py-3.5 sm:py-4 bg-white text-black rounded-[22px] shadow-[0_0_35px_rgba(48,84,255,0.7)] hover:shadow-[0_0_55px_rgba(48,84,255,1)] hover:scale-105 active:scale-95 transition-all duration-300"
          >
            <span className="font-extrabold text-base sm:text-lg tracking-wide text-black whitespace-nowrap">
              Official Store
            </span>
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-[14px] bg-[#2b59ff] flex items-center justify-center text-white shadow-[0_0_15px_rgba(43,89,255,0.8)] group-hover:rotate-12 transition-transform duration-300 flex-shrink-0">
              <ShoppingCart className="w-5 h-5" strokeWidth={2.2} />
            </div>
          </a>

          {/* Button 2: Ask Agent (White background, single line text) */}
          <a
            href="/chat"
            className="group relative flex items-center justify-between gap-4 px-6 sm:px-7 py-3.5 sm:py-4 bg-white text-black rounded-[22px] shadow-[0_0_35px_rgba(48,84,255,0.7)] hover:shadow-[0_0_55px_rgba(48,84,255,1)] hover:scale-105 active:scale-95 transition-all duration-300"
          >
            <span className="font-extrabold text-base sm:text-lg tracking-wide text-black whitespace-nowrap">
              Ask Agent
            </span>
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-[14px] bg-[#2b59ff] flex items-center justify-center text-white shadow-[0_0_15px_rgba(43,89,255,0.8)] group-hover:scale-110 transition-transform duration-300 flex-shrink-0">
              <MessageCircle className="w-5 h-5" strokeWidth={2.2} />
            </div>
          </a>
        </motion.div>
      </main>

      {/* 4. Bottom Spacing */}
      <div className="relative z-10 h-6 pointer-events-none" />
    </div>
  );
}
