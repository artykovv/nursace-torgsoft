import asyncio
from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.responses import FileResponse
from tasks.sync import sync_torgsoft_csv
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_async_session
import os

app = FastAPI()

@app.get("/")
async def base_router():
    return {
        "message": "Hello world"
    }

@app.get("/files")
async def list_files():
    folder_path = "/app/shared_files"
    try:
        files = os.listdir(folder_path)
    except Exception as e:
        return {"error": str(e)}
    return {"files": files}

@app.get("/read-file")
async def read_file(filename: str):
    filepath = f"/app/shared_files/{filename}"
    if not os.path.isfile(filepath):
        return {"error": "File not found"}
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}

@app.get("/download")
async def download_file(filename: str):
    filepath = f"/app/shared_files/{filename}"
    if not os.path.exists(filepath):
        return {"error": "File not found"}
    return FileResponse(filepath, filename=filename)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    dest = f"/app/shared_files/{file.filename}"
    with open(dest, "wb") as f:
        f.write(await file.read())
    return {"message": f"{file.filename} uploaded successfully"}


@app.post("/")
async def sync_router(
    synced: bool,
    session: AsyncSession = Depends(get_async_session)
):
    if synced:
        print("Syncing products...")
        task = asyncio.create_task(sync_torgsoft_csv())
        return {
            "message": "start product sync"
        }
    else:
        print("Products not synced")
        return {
            "message": "Products not synced"
        }
    