"use client"

import { useEffect, useState, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { explore } from "@/lib/api"
import { Movie } from "@/types/movie"
import MovieCard from "@/components/MovieCard"
import Skeleton from "@/components/Skeleton"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"

function ResultsContent() {
    const params = useSearchParams()
    const query = params.get("q") || ""

    const [results, setResults] = useState<Movie[]>([])
    const [archetype, setArchetype] = useState("")
    const [explanation, setExplanation] = useState("")
    const [emotionalVector, setEmotionalVector] = useState<Record<string, number> | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState("")

    useEffect(() => {
        async function fetchResults() {
            try {
                const data = await explore(query)
                setResults(data.results)
                setArchetype(data.archetype)
                setExplanation(data.explanation || "")
                setEmotionalVector(data.emotional_vector || null)
            } catch (err) {
                console.error(err)
                setError("Failed to fetch recommendations. Please try again.")
            } finally {
                setLoading(false)
            }
        }

        if (query) fetchResults()
    }, [query])

    if (loading) {
        return (
            <main className="min-h-screen bg-black text-white p-8 relative overflow-hidden">
                <div className="relative z-10 max-w-6xl mx-auto">
                    <div className="h-8 w-48 bg-zinc-900 rounded-lg animate-pulse mb-8" />
                    <div className="h-12 w-96 bg-zinc-900 rounded-lg animate-pulse mb-12" />
                    <Skeleton />
                </div>
            </main>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen bg-black text-white flex flex-col items-center justify-center">
                <p className="text-red-400 mb-4">{error}</p>
                <Link href="/" className="text-violet-400 hover:underline">
                    ← Back to search
                </Link>
            </div>
        )
    }

    return (
        <main className="min-h-screen bg-black text-white p-8 relative overflow-hidden">
            {/* Background Glow */}
            <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-violet-600/8 rounded-full blur-[100px] pointer-events-none" />

            <div className="relative z-10 max-w-6xl mx-auto">
                {/* Header */}
                <Link
                    href="/"
                    className="text-zinc-500 hover:text-white text-sm transition-colors duration-300 mb-6 inline-block"
                >
                    ← Back to FILMBOX
                </Link>

                <h1 className="text-4xl font-bold mb-2">
                    Results for{" "}
                    <span className="bg-gradient-to-r from-violet-400 to-violet-200 bg-clip-text text-transparent">
                        &ldquo;{query}&rdquo;
                    </span>
                </h1>

                {/* Archetype Badge */}
                {archetype && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex items-center gap-3 mb-2"
                    >
                        <span className="px-4 py-1 rounded-full bg-violet-600/20 border border-violet-500/30 text-violet-300 text-xs font-medium uppercase tracking-widest">
                            Detected: {archetype}
                        </span>
                    </motion.div>
                )}

                {/* Explanation */}
                {explanation && (
                    <p className="text-zinc-400 text-sm mb-4 max-w-2xl">{explanation}</p>
                )}

                {/* Emotional Fingerprint Visualization */}
                {emotionalVector && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="flex flex-wrap gap-2 mb-8"
                    >
                        {Object.entries(emotionalVector)
                            .filter(([_, val]) => val > 0.05)
                            .sort((a, b) => b[1] - a[1])
                            .map(([key, val]) => (
                                <span key={key} className="px-3 py-1.5 rounded-full bg-zinc-800/50 border border-zinc-700/50 text-zinc-300 text-xs tracking-wide flex items-center shadow-inner">
                                    <span className="capitalize text-violet-100">{key.replace('_', ' ')}</span>
                                    <span className="ml-2 text-violet-400/80 font-mono">{(val * 100).toFixed(0)}%</span>
                                </span>
                            ))}
                    </motion.div>
                )}

                {/* Results Grid */}
                <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
                    {results.map((movie, index) => (
                        <MovieCard
                            key={movie.id}
                            movie={movie}
                            rank={index + 1}
                            index={index}
                        />
                    ))}
                </div>

                {/* Footer */}
                {results.length === 0 && (
                    <p className="text-zinc-500 text-center mt-12">No results found for this query.</p>
                )}
            </div>
        </main>
    )
}

export default function ResultsPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen bg-black text-white flex items-center justify-center">
                    <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                </div>
            }
        >
            <ResultsContent />
        </Suspense>
    )
}
