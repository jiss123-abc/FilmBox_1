import { Movie } from "@/types/movie"

function ScoreBar({ value, label, color }: { value: number; label: string; color: string }) {
    const percentage = Math.min(value * 100, 100)
    return (
        <div className="mt-2">
            <div className="flex justify-between text-xs text-zinc-500 mb-1">
                <span>{label}</span>
                <span>{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full h-1.5 bg-zinc-700/50 rounded-full overflow-hidden">
                <div
                    className={`h-full rounded-full transition-all duration-700 ease-out ${color}`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    )
}

export default function MovieCard({ movie, rank }: { movie: Movie; rank: number }) {
    return (
        <div
            className="
        group relative
        bg-zinc-900/70 backdrop-blur-sm
        border border-zinc-800/60
        p-6 rounded-2xl
        hover:border-violet-500/30
        hover:shadow-[0_0_30px_rgba(139,92,246,0.1)]
        transition-all duration-500
      "
        >
            {/* Rank Badge */}
            <div className="absolute -top-3 -left-3 w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold shadow-lg">
                {rank}
            </div>

            {/* Title */}
            <h2 className="text-xl font-semibold text-white mb-1 group-hover:text-violet-300 transition-colors duration-300">
                {movie.title}
            </h2>

            {/* Final Score */}
            <p className="text-2xl font-bold text-violet-400 mb-4">
                {movie.final_score.toFixed(4)}
            </p>

            {/* Score Breakdown */}
            <ScoreBar value={movie.base_score} label="Quality Score" color="bg-emerald-500" />
            <ScoreBar value={movie.emotional_weight} label="Emotional Match" color="bg-violet-500" />
        </div>
    )
}
