"use client"

import { useEffect, useState, use } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { getMovieDetails, getSimilarMovies, recordInteraction } from "@/lib/api"
import { MovieDetails, Movie } from "@/types/movie"
import MovieCard from "@/components/MovieCard"
import Link from "next/link"

export default function MoviePage({ params }: { params: Promise<{ id: string }> }) {
    const { id: movieIdStr } = use(params)
    const movieId = parseInt(movieIdStr)

    const [movie, setMovie] = useState<MovieDetails | null>(null)
    const [similar, setSimilar] = useState<Movie[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        setLoading(true)
        setError(null)

        // Fetch core details first
        getMovieDetails(movieId)
            .then(data => {
                setMovie(data)
                setLoading(false)
                recordInteraction(movieId, 'clicked')

                // Fetch similar movies separately so they don't block the main page
                getSimilarMovies(movieId, 12)
                    .then(simData => setSimilar(simData.results))
                    .catch(err => {
                        console.error("Similar movies fetch failed:", err)
                        setSimilar([])
                    })
            })
            .catch(err => {
                console.error("Movie details fetch failed:", err)
                setError("Failed to load movie details")
                setLoading(false)
            })
    }, [movieId])

    if (loading) {
        return (
            <div className="min-h-screen bg-black flex items-center justify-center">
                <motion.div
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="text-zinc-500 font-mono tracking-widest uppercase text-xs"
                >
                    Initializing Cinematic Core...
                </motion.div>
            </div>
        )
    }

    if (error || !movie) {
        return (
            <div className="min-h-screen bg-black flex flex-col items-center justify-center p-6 text-center">
                <h2 className="text-2xl font-bold text-white mb-4">The core is unreachable</h2>
                <p className="text-zinc-500 mb-8">{error || "Movie not found"}</p>
                <Link href="/" className="px-6 py-3 bg-white text-black font-bold rounded-full hover:bg-zinc-200 transition-colors">
                    Return to Search
                </Link>
            </div>
        )
    }

    const backdropUrl = movie.poster_path
        ? `https://image.tmdb.org/t/p/original${movie.poster_path}`
        : null

    return (
        <main className="min-h-screen bg-black text-white relative">
            {/* Cinematic Header / Backdrop */}
            <div className="relative h-[70vh] w-full overflow-hidden">
                {backdropUrl && (
                    <motion.img
                        initial={{ scale: 1.1, opacity: 0 }}
                        animate={{ scale: 1, opacity: 0.4 }}
                        transition={{ duration: 1.5 }}
                        src={backdropUrl}
                        alt={movie.title}
                        className="absolute inset-0 w-full h-full object-cover grayscale-[50%]"
                    />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-transparent" />

                <div className="absolute inset-x-0 bottom-0 p-8 md:p-16 max-w-7xl mx-auto flex flex-col md:flex-row items-end gap-8">
                    {/* Poster Card */}
                    <motion.div
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.8, delay: 0.2 }}
                        className="hidden md:block w-64 aspect-[2/3] rounded-2xl overflow-hidden shadow-2xl border border-white/10 shrink-0"
                    >
                        <img
                            src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}
                            alt={movie.title}
                            className="w-full h-full object-cover"
                        />
                    </motion.div>

                    {/* Meta Section */}
                    <div className="flex-1">
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ duration: 0.8, delay: 0.4 }}
                        >
                            <div className="flex flex-wrap gap-2 mb-4">
                                {movie.genres.map(g => (
                                    <span key={g.id} className="px-3 py-1 bg-white/10 backdrop-blur-md rounded-full text-[10px] uppercase font-bold tracking-widest border border-white/10">
                                        {g.name}
                                    </span>
                                ))}
                            </div>
                            <h1 className="text-5xl md:text-7xl font-black mb-4 tracking-tighter uppercase leading-none">
                                {movie.title}
                            </h1>
                            <div className="flex items-center gap-6 text-zinc-400 font-mono text-sm tracking-widest uppercase">
                                <span>{movie.release_date}</span>
                                <span className="w-1 h-1 bg-zinc-600 rounded-full" />
                                <span>{movie.runtime} min</span>
                                <span className="w-1 h-1 bg-zinc-600 rounded-full" />
                                <span className="text-violet-400 font-bold">{movie.vote_average.toFixed(1)} / 10</span>
                            </div>
                        </motion.div>
                    </div>
                </div>
            </div>

            {/* Content Section */}
            <div className="max-w-7xl mx-auto px-8 md:px-16 py-12 grid grid-cols-1 lg:grid-cols-3 gap-16">
                {/* Left: Info */}
                <div className="lg:col-span-2 space-y-12">
                    <section>
                        <h3 className="text-zinc-500 text-xs font-bold tracking-[0.3em] uppercase mb-4">Introduction</h3>
                        <p className="text-xl text-zinc-300 leading-relaxed font-light italic">
                            {movie.overview}
                        </p>
                    </section>

                    <section>
                        <h3 className="text-zinc-500 text-xs font-bold tracking-[0.3em] uppercase mb-6">Principal Cast</h3>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-6">
                            {movie.cast.map((actor, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.6 + (i * 0.05) }}
                                    className="p-4 bg-zinc-900/40 rounded-xl border border-white/5"
                                >
                                    <p className="text-sm font-bold text-white mb-0.5">{actor.name}</p>
                                    <p className="text-[10px] text-zinc-500 uppercase tracking-tighter">{actor.character}</p>
                                </motion.div>
                            ))}
                        </div>
                    </section>
                </div>

                {/* Right: Credits and Details */}
                <div className="space-y-12">
                    <section>
                        <h3 className="text-zinc-500 text-xs font-bold tracking-[0.3em] uppercase mb-4">Director</h3>
                        <div className="p-6 bg-gradient-to-br from-violet-600/20 to-transparent rounded-2xl border border-violet-500/20">
                            <p className="text-2xl font-black">{movie.director?.name || "Unknown"}</p>
                        </div>
                    </section>

                    <section>
                        <h3 className="text-zinc-500 text-xs font-bold tracking-[0.3em] uppercase mb-4">Narrative DNA</h3>
                        <div className="flex flex-wrap gap-2">
                            {movie.keywords.map(k => (
                                <span key={k.id} className="px-2 py-1 bg-zinc-800 text-zinc-400 text-[10px] rounded uppercase font-mono">
                                    #{k.name}
                                </span>
                            ))}
                        </div>
                    </section>

                    <section>
                        <h3 className="text-zinc-500 text-xs font-bold tracking-[0.3em] uppercase mb-4">Production</h3>
                        <div className="space-y-2">
                            <div className="flex justify-between border-b border-white/5 py-2">
                                <span className="text-zinc-500 text-xs uppercase">Original Language</span>
                                <span className="text-xs font-mono">{movie.language || movie.original_language?.toUpperCase()}</span>
                            </div>
                            <div className="flex justify-between border-b border-white/5 py-2">
                                <span className="text-zinc-500 text-xs uppercase">Country</span>
                                <span className="text-xs">{movie.countries?.[0]?.name || "N/A"}</span>
                            </div>
                        </div>
                    </section>
                </div>
            </div>

            {/* Discovery Row */}
            <div className="bg-zinc-900/30 py-20 mt-12">
                <div className="max-w-7xl mx-auto px-8 md:px-16">
                    <h3 className="text-center text-zinc-500 text-xs font-bold tracking-[0.4em] uppercase mb-12">Infinite Discovery Loop</h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
                        <AnimatePresence mode="popLayout">
                            {similar.map((sim, i) => (
                                <MovieCard key={sim.id} movie={sim} rank={i + 1} index={i} />
                            ))}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* Navigation Home */}
            <Link href="/" className="fixed top-8 left-8 z-50 p-3 bg-black/50 backdrop-blur-xl border border-white/10 rounded-full hover:bg-white/10 transition-colors group">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="group-hover:-translate-x-0.5 transition-transform"><path d="m15 18-6-6 6-6" /></svg>
            </Link>
        </main>
    )
}
