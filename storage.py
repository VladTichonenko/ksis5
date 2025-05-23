from typing import Optional
from fastapi import FastAPI, Header, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from pathlib import Path
from datetime import datetime
import shutil

app = FastAPI()
storage_dir = Path("storage")

def get_full_path(path: str) -> Path:
    safe_path = (storage_dir / path).resolve()
    if not safe_path.is_relative_to(storage_dir.resolve()):
        raise HTTPException(status_code = 400, detail = "Invalid path")
    return safe_path


@app.put("/files/{path:path}")
async def upload_or_copy_file(
    path: str,
    file: Optional[UploadFile] = File(None),
    x_copy_from: Optional[str] = Header(None, alias="X-Copy-From")
):
    full_path = get_full_path(path)
    full_path.parent.mkdir(parents = True, exist_ok = True)
    
    if x_copy_from:
        source_path = get_full_path(x_copy_from)
        if not source_path.exists() or not source_path.is_file():
            raise HTTPException(status_code = 404, detail = "Source file not found")
        shutil.copy2(source_path, full_path)
        return JSONResponse(status_code = 200, content = {"message": "File was copied"})
    
    if file is None:
        raise HTTPException(status_code = 400, detail = "File was not selected")
    
    with open(full_path, "wb") as f:
        f.write(await file.read())
    return Response(status_code=201, content = "File was loaded")
    
    
@app.get("/files/{path:path}")
def get_file_or_dir(path: str):
    full_path = get_full_path(path)
    if not full_path.exists():
        raise HTTPException(status_code = 404, detail = "Not found")
    
    if full_path.is_file():
        return FileResponse(full_path, media_type="application/octet-stream", filename=full_path.name)

    if full_path.is_dir():
        files = []
        directories = []
        for item in full_path.iterdir():
            if item.is_file():
                files.append(item.name)
            elif item.is_dir():
                directories.append(item.name)
        return JSONResponse(
            status_code=200,
            content={
                "files": files,
                "directories": directories
            }
        )
    
@app.head("/files/{path:path}")
def get_file_info(path:str):
    full_path = get_full_path(path)
    if not full_path.is_file():
        raise HTTPException(status_code = 404, detail = "File not found")
    
    stat = full_path.stat()
    headers = {
        "Content-Length": str(stat.st_size),
        "Last-Modified":str(datetime.utcfromtimestamp(stat.st_mtime)),
    }
    return Response(headers = headers)


@app.delete("/files/{path:path}")
def delete_path(path: str):
    full_path = get_full_path(path)
    if not full_path.exists():
        raise HTTPException(status_code = 404, detail = "Not found")
    
    try: 
        if full_path.is_file():
            full_path.unlink()  
        else:
            shutil.rmtree(full_path)
        return Response(status_code=204, content = "File was successfully removed")
    except Exception as e:
        raise HTTPException(status_code = 500 , detail = f"Error: {e}")