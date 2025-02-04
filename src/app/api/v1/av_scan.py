from fastapi import FastAPI, File, UploadFile
import os
from ...core.logger import logging

app = FastAPI()

UPLOAD_DIR = "/code/Imported_Files"

@app.post("/upload_scan/")
async def upload_file(file: UploadFile = File(...)):
    """Save uploaded file and scan with ClamAV."""
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    scan_result = scan_file(file_path)
    return {"filename": file.filename, "scan_result": scan_result}
