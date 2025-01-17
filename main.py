from fastapi import FastAPI
from configuration import init_db
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)



from routes import router

app.include_router(router)

