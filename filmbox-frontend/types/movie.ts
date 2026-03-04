export interface Movie {
    id: number
    title: string
    final_score: number
    base_score: number
    emotional_weight: number
}

export interface ExploreResponse {
    archetype: string
    count: number
    results: Movie[]
    explanation?: string
}
