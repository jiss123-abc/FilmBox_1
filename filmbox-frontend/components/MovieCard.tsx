import { Movie } from "@/types/movie"
import { motion } from "framer-motion"
import { recordInteraction } from "@/lib/api"

function ScoreBar({ value, label, color, delay }: { value: number; label: string; color: string; delay: number }) {
    const percentage = Math.min(value * 100, 100)
    return (
        <div className="mt-3">
            <div className="flex justify-between text-[10px] uppercase tracking-widest text-zinc-400 mb-1.5">
                <span>{label}</span>
                <span className="font-mono">{(value * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.8, delay, ease: "easeOut" }}
                    className={`h-full rounded-full ${color}`}
                />
            </div>
        </div>
    )
}

export default function MovieCard({ movie, rank, index }: { movie: Movie; rank: number; index: number }) {
    const posterUrl = movie.poster_path
        ? `https://image.tmdb.org/t/p/w500${movie.poster_path}`
        : "https://via.placeholder.com/500x750/111/666?text=Coming+Soon"

    return (
        <motion.div
            onClick={() => recordInteraction(movie.id, 'clicked')}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="group relative aspect-[2/3] rounded-2xl overflow-hidden bg-zinc-900 shadow-2xl transition-all duration-300 hover:scale-[1.02] hover:shadow-violet-500/10 cursor-pointer"
        >
            {/* Poster Image */}
            <img
                src={posterUrl}
                alt={movie.title}
                className="absolute inset-0 w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 group-hover:brightness-110"
            />

            {/* Gradient Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent opacity-90 transition-opacity duration-300 group-hover:opacity-100" />

            {/* Rank Badge */}
            <div className="absolute top-4 left-4 z-20 w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white shadow-xl">
                {rank}
            </div>

            {/* Content Container */}
            <div className="absolute inset-x-0 bottom-0 p-6 z-10">
                <div className="transform transition-transform duration-300 group-hover:-translate-y-2">
                    <h2 className="text-xl font-bold text-white mb-1 line-clamp-1 group-hover:text-violet-200 transition-colors">
                        {movie.title}
                    </h2>

                    <div className="flex items-baseline gap-2 mb-4">
                        <span className="text-2xl font-black text-violet-400">
                            {movie.final_score.toFixed(3)}
                        </span>
                        <span className="text-[10px] text-zinc-500 uppercase tracking-tighter">Score</span>
                    </div>

                    <div className="space-y-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 delay-100">
                        <ScoreBar value={movie.base_score} label="Quality" color="bg-emerald-500" delay={index * 0.1 + 0.3} />
                        <ScoreBar value={movie.emotional_weight} label="Match" color="bg-violet-500" delay={index * 0.1 + 0.4} />

                        {movie.explanation && movie.explanation.length > 0 && (
                            <div className="pt-3 mt-3 border-t border-zinc-700/50 space-y-1">
                                {movie.explanation.map((exp, i) => (
                                    <p key={i} className="text-[10px] sm:text-xs text-zinc-300 flex items-start gap-1.5 leading-tight">
                                        <span className="text-violet-400 mt-0.5">•</span>
                                        <span>{exp}</span>
                                    </p>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
