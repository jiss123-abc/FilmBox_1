"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

export default function SearchBox() {
    const [query, setQuery] = useState("")
    const [focused, setFocused] = useState(false)

    const router = useRouter()

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!query.trim()) return
        router.push(`/results?q=${encodeURIComponent(query)}`)
    }

    return (
        <form onSubmit={handleSubmit} className="w-full max-w-2xl relative">
            <div
                className={`
          relative rounded-2xl transition-all duration-500
          ${focused
                        ? "shadow-[0_0_40px_rgba(139,92,246,0.3)]"
                        : "shadow-[0_0_20px_rgba(139,92,246,0.1)]"
                    }
        `}
            >
                <input
                    className="
            w-full px-6 py-5 rounded-2xl
            bg-zinc-900/80 backdrop-blur-sm
            text-white text-lg
            border border-zinc-700/50
            outline-none
            placeholder:text-zinc-500
            focus:border-violet-500/50
            transition-all duration-300
          "
                    placeholder="What are you in the mood for?"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setFocused(true)}
                    onBlur={() => setFocused(false)}
                />
                <button
                    type="submit"
                    className="
            absolute right-3 top-1/2 -translate-y-1/2
            px-5 py-2.5 rounded-xl
            bg-violet-600 hover:bg-violet-500
            text-white font-medium text-sm
            transition-all duration-300
            hover:shadow-[0_0_20px_rgba(139,92,246,0.4)]
          "
                >
                    Discover
                </button>
            </div>
        </form>
    )
}
