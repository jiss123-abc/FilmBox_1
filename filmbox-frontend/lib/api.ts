import { ExploreResponse, ProfileResponse, MovieDetails, SimilarResponse } from "@/types/movie"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8012"

export function getSessionId(): string {
    if (typeof window === "undefined") return ""
    let sid = localStorage.getItem("filmbox_session_id")
    if (!sid) {
        sid = crypto.randomUUID()
        localStorage.setItem("filmbox_session_id", sid)
    }
    return sid
}

export async function explore(query: string): Promise<ExploreResponse> {
    const res = await fetch(
        `${API_URL}/explore?query=${encodeURIComponent(query)}`,
        {
            headers: {
                "X-Session-ID": getSessionId()
            }
        }
    )

    if (!res.ok) {
        throw new Error("API error")
    }

    return res.json()
}

export async function recommend(archetype: string, limit: number = 30): Promise<ExploreResponse> {
    const res = await fetch(
        `${API_URL}/recommend?archetype=${encodeURIComponent(archetype)}&limit=${limit}`
    )

    if (!res.ok) {
        throw new Error("API error")
    }

    return res.json()
}

export async function recordInteraction(movieId: number, action: 'liked' | 'saved' | 'clicked') {
    const sessionId = getSessionId()
    if (!sessionId) return

    try {
        await fetch(`${API_URL}/interactions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                movie_id: movieId,
                action
            })
        })
    } catch (e) {
        // Silently fail for analytics
        console.error("Interaction tracking failed", e)
    }
}

export async function getProfile(sessionId: string): Promise<ProfileResponse> {
    const res = await fetch(`${API_URL}/profile`, {
        headers: {
            "X-Session-ID": sessionId
        }
    })

    if (!res.ok) {
        throw new Error("Failed to load profile")
    }

    return res.json()
}

export async function getMovieDetails(id: number): Promise<MovieDetails> {
    const res = await fetch(`${API_URL}/movies/${id}`)
    if (!res.ok) {
        throw new Error("Failed to fetch movie details")
    }
    return res.json()
}

export async function getSimilarMovies(id: number, limit: number = 12): Promise<SimilarResponse> {
    const res = await fetch(`${API_URL}/movies/${id}/similar?limit=${limit}`)
    if (!res.ok) {
        throw new Error("Failed to fetch similar movies")
    }
    return res.json()
}
