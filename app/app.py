from fastapi import FastAPI, HTTPException, Query
from databases import Database
from pydantic import BaseModel
from typing import Annotated

DATABASE_URL = "postgresql://myuser:1234@localhost/mtdatabase"

database = Database(DATABASE_URL)

class TodoCreate(BaseModel):

    title : str

    descriptions : str = None

    completed : bool = False


class TodoRead(BaseModel):
    title : str
    description : str
    completed : bool

async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

@app.get("/todos")
async def read_todos(
    limit : Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0
):
    query = '''SELECT * FROM todos ORDER BY id LIMIT :limit OFFSET :offset'''
    values = {
        "limit":limit,
        "offset":offset
    }
    try:
        result = await database.fetch_all(
            query=query,
            values=values
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="ПИЗДЕЦ"
            )
        return result
    except HTTPException:
        raise
    except Exception as e :
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения пользоватедя {str(e)}"
            )


@app.post("/todos/{user_id}")

async def create_todo(user_id : int,todo : TodoCreate):

    query = '''INSERT INTO todos(title, descriptions, compelted, user_id) VALUES (:title, :descriptions, :completed, :user_id) RETURNING id'''

    values = {**todo.model_dump(),

        "user_id":user_id}
    try:

        result = await database.execute(
        query=query,
        values=values

     )

        return "Пользователь сохранен"

    except Exception as e:
        raise HTTPException(
        status_code=500,
        detail=f"Ошибка при создании заметки {str(e)}"
        )