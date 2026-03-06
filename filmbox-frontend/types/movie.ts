export interface Movie {
    id: number
    title: string
    final_score: number
    base_score: number
    emotional_weight: number
    similarity_score?: number
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
