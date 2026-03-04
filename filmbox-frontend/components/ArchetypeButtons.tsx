"use client"

import { useRouter } from "next/navigation"

const ARCHETYPES = [
    { name: "Blockbuster", emoji: "💥" },
    { name: "Feel-Good", emoji: "☀️" },
    { name: "Dark & Gritty", emoji: "🌑" },
    { name: "Mind-Bending", emoji: "🌀" },
    { name: "Emotional", emoji: "💧" },
    { name: "Comfort", emoji: "🍿" },
]

export default function ArchetypeButtons() {
    const router = useRouter()

    return (
        <div className="flex flex-wrap justify-center gap-3 mt-8">
            {ARCHETYPES.map((type) => (
                <button
                    key={type.name}
                    onClick={() =>
                        router.push(`/results?q=${encodeURIComponent(type.name)}`)
                    }
                    className="
            group
            px-5 py-2.5 rounded-full
            bg-zinc-800/60 backdrop-blur-sm
            border border-zinc-700/40
            text-zinc-300 text-sm font-medium
            hover:bg-zinc-700/60 hover:text-white
            hover:border-violet-500/30
            hover:shadow-[0_0_15px_rgba(139,92,246,0.15)]
            transition-all duration-300
            cursor-pointer
          "
                >
                    <span className="mr-1.5 group-hover:scale-110 inline-block transition-transform duration-300">
                        {type.emoji}
                    </span>
                    {type.name}
                </button>
            ))}
        </div>
    )
}
