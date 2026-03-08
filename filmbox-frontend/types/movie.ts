export interface Movie {
    id: number
    title: string
    final_score?: number
    base_score?: number
    emotional_weight?: number
    similarity_score?: number
    vote_average?: number
    popularity?: number
    poster_path?: string
    explanation?: string[]
}

export interface ExploreResponse {
    archetype: string
    count: number
    results: Movie[]
    emotional_vector?: Record<string, number>
    explanation?: string
}

export interface TopArchetype {
    name: string
    score: number
}

export interface ProfileResponse {
    interaction_count: number
    taste_vector?: Record<string, number>
    top_archetypes?: TopArchetype[]
}

// --- Movie Details Types ---

export interface Genre {
    id: number
    name: string
}

export interface CastMember {
    id: number
    name: string
    character: string
}

export interface Director {
    id: number
    name: string
}

export interface MovieDetails extends Movie {
    overview: string
    release_date: string
    runtime: number
    vote_average: number
    vote_count: number
    popularity: number
    original_language?: string
    genres: Genre[]
    director?: Director
    cast: CastMember[]
    keywords: { id: number; name: string }[]
    countries: { id: number; name: string }[]
    language?: string
}

export interface SimilarResponse {
    seed_movie_id: number
    seed_movie_title: string
    count: number
    results: Movie[]
}
