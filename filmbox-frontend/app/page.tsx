"use client"

import { useEffect, useState } from "react"
import SearchBox from "@/components/SearchBox"
import ArchetypeButtons from "@/components/ArchetypeButtons"
import { getProfile, getSessionId } from "@/lib/api"
import { ProfileResponse } from "@/types/movie"
import { motion } from "framer-motion"

export default function Home() {
  const [profile, setProfile] = useState<ProfileResponse | null>(null)

  useEffect(() => {
    const sessionId = getSessionId()
    getProfile(sessionId)
      .then(setProfile)
      .catch(console.error)
  }, [])

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

        {/* Taste Profile UI */}
        {profile && profile.interaction_count >= 3 && profile.taste_vector && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-12 p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl w-full max-w-md backdrop-blur-sm shadow-2xl"
          >
            <h3 className="text-zinc-500 text-xs font-bold tracking-[0.2em] uppercase mb-6 text-center">
              Your Taste Profile
            </h3>
            <div className="space-y-4">
              {profile.top_archetypes?.slice(0, 4).map((archetype) => (
                <div key={archetype.name} className="flex items-center justify-between group">
                  <span className="text-zinc-300 text-sm font-medium capitalize transition-colors group-hover:text-white">
                    {archetype.name.replace('_', ' ')}
                  </span>
                  <div className="flex items-center gap-4">
                    <div className="w-32 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${archetype.score * 100}%` }}
                        transition={{ duration: 1.2, ease: "easeOut", delay: 0.1 }}
                        className="h-full bg-gradient-to-r from-violet-600 to-indigo-400"
                      />
                    </div>
                    <span className="text-zinc-500 text-xs font-mono w-8 text-right">
                      {(archetype.score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Footer Hint */}
        <p className="mt-12 text-zinc-600 text-xs">
          Powered by deterministic scoring • No randomness • Pure math
        </p>
      </div>
    </main>
  )
}
