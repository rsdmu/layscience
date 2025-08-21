'use client'

export default function Hero() {
  return (
    <header className="relative bg-studio-gradient">
      <div className="container-lg">
        <div className="flex items-center justify-between pt-6">
          <div className="text-5xl md:text-7xl font-display tracking-wideish leading-none text-white drop-shadow">
            <span className="block">LAYSCIENCE</span>
            <span className="block -mt-2">ART</span>
          </div>
          <div className="hidden md:block rotate-90 absolute right-2 top-24">
            <span className="font-display tracking-widest text-white/80">SCIENCE</span>
          </div>
        </div>
        <div className="h-64 md:h-80 w-full overflow-hidden mt-6">
          {/* Decorative network lines */}
          <svg viewBox="0 0 800 320" className="w-full h-full">
            <defs>
              <linearGradient id="fade" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="black" stopOpacity="0.25" />
                <stop offset="100%" stopColor="black" stopOpacity="0.05" />
              </linearGradient>
            </defs>
            {Array.from({length: 80}).map((_,i)=>(
              <line key={i}
                    x1={(i*37)%800}
                    y1={0}
                    x2={(i*97)%800}
                    y2={320}
                    stroke="url(#fade)" strokeWidth="2"/>
            ))}
          </svg>
        </div>
      </div>
      <div className="border-b border-black/10"></div>
    </header>
  )
}
