# FilmBox Backend App

from fastapi import FastAPI

app = FastAPI(title="FilmBox", description="Deterministic Emotional Movie Recommender")

@app.get("/")
def read_root():
    return {"message": "Welcome to FilmBox API"}
