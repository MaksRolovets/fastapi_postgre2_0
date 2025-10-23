from fastapi import FastAPI, HTTPException, Query
from databases import Database
from pydantic import BaseModel
from typing import Annotated # пароль для mdatabase myuser:1234

DATABASE_URL = "postgresql://myuser:1234@localhost/TODOS"

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
    offset: Annotated[int, Query(ge=0)] = 0,
    sort_by : Annotated[str, Query()] = "id"
):
    if sort_by.startswith('-'):
        field = sort_by[1:]
        order = "DESC"
    else:
        field = sort_by
        order = "ASC"
    query = f'''SELECT * FROM tasks ORDER BY {field} {order} LIMIT :limit OFFSET :offset'''
    values = {
        #"sort_by":sort_by,
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

async def create_todo(todo : TodoCreate):

    query = '''INSERT INTO tasks(title, descriptions, compelted) VALUES (:title, :descriptions, :completed) RETURNING id'''

    values = {**todo.model_dump()}
    try:

        result = await database.execute(
        query=query,
        values=values

     )

        return {"Пользователь сохранен":result}

    except Exception as e:
        raise HTTPException(
        status_code=500,
        detail=f"Ошибка при создании заметки {str(e)}"
        )
    
# поправить поля created, добавить нормальную валидацию даты и расчет времени 