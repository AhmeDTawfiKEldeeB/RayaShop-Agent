import React, { useState } from 'react';
import { ChevronDown, Menu, X } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-transparent px-6 py-4 flex items-center justify-between font-sans">
      {/* Left: Sunburst Icon (24x24px SVG) */}
      <a href="/" className="flex items-center gap-3 text-white focus:outline-none">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
      </a>

      {/* Center Nav Links (Desktop) */}
      <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-white/80">
        <a href="#products" className="flex items-center gap-1 hover:text-white transition-colors duration-200">
          <span>Products</span>
          <ChevronDown className="w-4 h-4 text-white/60" />
        </a>
        <a href="#customer-stories" className="hover:text-white transition-colors duration-200">
          Customer Stories
        </a>
        <a href="#resources" className="hover:text-white transition-colors duration-200">
          Resources
        </a>
        <a href="#pricing" className="hover:text-white transition-colors duration-200">
          Pricing
        </a>
      </nav>

      {/* Right Actions */}
      <div className="hidden sm:flex items-center gap-4">
        <a
          href="https://www.rayashop.com/en"
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-white/80 hover:text-white transition-colors duration-200"
        >
          Book A Demo
        </a>
        <a
          href="/chat"
          className="px-5 py-2.5 rounded-full bg-white text-black font-semibold text-sm hover:bg-slate-100 shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:scale-105 active:scale-95 transition-all duration-300"
        >
          Get Started
        </a>
      </div>

      {/* Mobile Menu Toggle */}
      <div className="flex md:hidden items-center gap-3">
        <a
          href="/chat"
          className="px-4 py-1.5 rounded-full bg-white text-black font-semibold text-xs"
        >
          Get Started
        </a>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-1.5 text-white/80 hover:text-white focus:outline-none"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden absolute top-full left-0 right-0 bg-black/95 backdrop-blur-2xl border-b border-white/10 px-6 py-6 space-y-4 animate-in fade-in slide-in-from-top-4 duration-300">
          <nav className="flex flex-col space-y-3 text-base font-medium text-white/80">
            <a href="#products" onClick={() => setMobileMenuOpen(false)} className="py-1 hover:text-[#3054ff]">
              Products
            </a>
            <a href="#customer-stories" onClick={() => setMobileMenuOpen(false)} className="py-1 hover:text-[#3054ff]">
              Customer Stories
            </a>
            <a href="#resources" onClick={() => setMobileMenuOpen(false)} className="py-1 hover:text-[#3054ff]">
              Resources
            </a>
            <a href="#pricing" onClick={() => setMobileMenuOpen(false)} className="py-1 hover:text-[#3054ff]">
              Pricing
            </a>
          </nav>
          <div className="pt-4 border-t border-white/10 flex flex-col gap-3">
            <a
              href="https://www.rayashop.com/en"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full text-center py-2.5 text-sm font-semibold border border-white/20 rounded-xl text-white"
            >
              Book A Demo
            </a>
            <a
              href="/chat"
              className="w-full text-center py-2.5 text-sm font-bold bg-[#3054ff] rounded-xl text-white shadow-[0_0_20px_rgba(48,84,255,0.5)]"
            >
              Get Started
            </a>
          </div>
        </div>
      )}
    </header>
  );
};
