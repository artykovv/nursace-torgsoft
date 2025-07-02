import asyncio
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from tasks.sync import sync_torgsoft_csv
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_async_session


app = FastAPI()

@app.get("/")
async def base_router():
    return {
        "message": "Hello world"
    }

@app.post("/")
async def sync_router(
    synced: bool,
    session: AsyncSession = Depends(get_async_session)
):
    if synced:
        print("Syncing products...")
        task = asyncio.create_task(sync_torgsoft_csv())
        return task
    else:
        print("Products not synced")
        return {
            "message": "Products not synced"
        }
    