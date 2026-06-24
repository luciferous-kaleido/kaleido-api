import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI

app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/hello")
def hello():
    create_data()
    return {"Hello": "World V6"}


@app.get("/error")
def error():
    raise Exception("test")


def create_data():
    file_path = "/app/data/statics/count.json"
    try:
        with open(file_path) as f:
            data: dict = json.load(f)
    except FileNotFoundError:
        data: dict = {"count": 0}

    data["count"] = data["count"] + 1

    with NamedTemporaryFile("w", encoding="utf-8", dir="/app/data", delete=False) as f:
        temp_path = Path(f.name)
        json.dump(data, f, ensure_ascii=False)
        f.flush()
        os.fsync((f.fileno()))

    os.chmod(temp_path, 0o644)
    os.replace(temp_path, file_path)
