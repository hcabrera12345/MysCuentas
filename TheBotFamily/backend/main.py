from fastapi import FastAPI

app = FastAPI(
    title="The Bot Family API",
    description="Backend for the Family Assistant App",
    version="1.0.0"
)

from routers import finance, chat

app.include_router(finance.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {"message": "The Bot Family Brain is Online! 🧠"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "The Bot Family Backend"}
