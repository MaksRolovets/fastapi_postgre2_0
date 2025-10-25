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
    
@app.patch("/todos")
async def update_todo(
    ids : Annotated[str, Query(..., description="ID задач через запятую: 1,2,3")],
    completed : Annotated[bool, Query(..., descriptions = "Статус выполнения")]):
    try:
         id_list = [int(id.strip()) for id in ids.split(',')]
    except:
        HTTPException(status_code=500, detail="Пизда данным, введи их нормально!")

    query = '''UPDATE tasks SET completed = :completed,
                                completed_at = CASE 
                                    WHEN :completed = true THEN NOW()::timestamp(0)
                                    ELSE NULL
                            END 
                        WHERE id = ANY(:id_list) RETURNING id'''
    values = {
        "completed":completed,
        "id_list":id_list
}   
    try:
        result = await database.fetch_all(
            query=query,
            values=values
        )

        if not result:
            raise HTTPException(
                status_code=404,
                detail="ну это ни в какие рамки"
            )
        return result
    except HTTPException:
        raise
    except Exception as e :
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка получения пользоватедя {str(e)}"
            )
    
# поправить поля created, добавить нормальную валидацию даты и расчет времени 
'''SELECT 
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600), 2) AS avg_completion_time_hours
FROM tasks
WHERE completed = true
  AND completed_at IS NOT NULL
  AND created_at IS NOT NULL
  AND completed_at > created_at;''' # расчет среднего времени
  # добавить эндроинт putch