import SearchBox from "@/components/SearchBox"
import ArchetypeButtons from "@/components/ArchetypeButtons"

export default function Home() {
  return (
    <main className="min-h-screen bg-black text-white flex flex-col items-center justify-center p-6 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-violet-600/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center">
        {/* Logo */}
        <h1 className="text-6xl font-extrabold tracking-tight mb-2 bg-gradient-to-r from-white via-violet-200 to-violet-400 bg-clip-text text-transparent">
          FILMBOX
        </h1>
        <p className="text-zinc-500 text-lg mb-10 tracking-wide">
          Emotional Movie Discovery Engine
        </p>

        {/* Search */}
        <SearchBox />

        {/* Quick Archetypes */}
        <ArchetypeButtons />

        {/* Footer Hint */}
        <p className="mt-12 text-zinc-600 text-xs">
          Powered by deterministic scoring • No randomness • Pure math
        </p>
      </div>
    </main>
  )
}
