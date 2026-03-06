export default function Skeleton() {
    return (
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
                <div
                    key={i}
                    className="aspect-[2/3] rounded-2xl bg-zinc-900 overflow-hidden relative"
                >
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />

                    <div className="absolute inset-x-0 bottom-0 p-6 space-y-4">
                        <div className="h-6 w-2/3 bg-zinc-800 rounded-lg" />
                        <div className="h-8 w-1/3 bg-zinc-800 rounded-lg" />
                        <div className="space-y-2">
                            <div className="h-2 w-full bg-zinc-800 rounded-full" />
                            <div className="h-2 w-full bg-zinc-800 rounded-full" />
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}
