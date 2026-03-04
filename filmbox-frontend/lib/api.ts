import { ExploreResponse } from "@/types/movie"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://filmbox-api.onrender.com"

export async function explore(query: string): Promise<ExploreResponse> {
    const res = await fetch(
        `${API_URL}/explore?query=${encodeURIComponent(query)}`
    )

    if (!res.ok) {
        throw new Error("API error")
    }

    return res.json()
}

export async function recommend(archetype: string, limit: number = 20): Promise<ExploreResponse> {
    const res = await fetch(
        `${API_URL}/recommend?archetype=${encodeURIComponent(archetype)}&limit=${limit}`
    )

    if (!res.ok) {
        throw new Error("API error")
    }

    return res.json()
}
