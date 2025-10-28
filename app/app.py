from fastapi import FastAPI, HTTPException, Query
from databases import Database
from pydantic import BaseModel
from datetime import date
from time import time
from typing import Annotated, Optional # пароль для mdatabase myuser:1234

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
    sort_by : Annotated[Optional[str], Query()] = "id",
    completed : Optional[bool] = None,
    created_after : Optional[date] = None,
    created_before : Optional[date] = None,
    title_contains : Optional[str] = None
):
    if sort_by.startswith('-'):
        field = sort_by[1:]
        order = "DESC"
    else:
        field = sort_by
        order = "ASC"
    query = f'''SELECT * FROM tasks'''
    conditions = []
    values = {
        "limit":limit,
        "offset":offset
    }

    if completed is not None:
        conditions.append("completed = :completed")
        values["completed"] = completed

    if created_after:
        conditions.append("created_at >= :created_after")
        values["created_after"] = created_after

    if created_before:
        conditions.append("created_at <= :created_before")
        values["created_before"] = created_before

    if title_contains:
        conditions.append("title ILIKE :title_contains")
        values["title_contains"] = f"%{title_contains}%"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += f" ORDER BY {field} {order} LIMIT :limit OFFSET :offset"

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

@app.get("/todos/analytis")
async def analytics():
    start_time = time()
    query1 = '''SELECT 
    COUNT(*) as total_tasks,
    COUNT(*) FILTER (WHERE completed = true) as completed_true,
    COUNT(*) FILTER (WHERE completed = false) as completed_false,
    COALESCE(ROUND(
        AVG(CASE
            WHEN completed = true 
            AND completed_at IS NOT NULL 
            AND created_at IS NOT NULL 
            AND completed_at > created_at
            THEN EXTRACT(EPOCH FROM (completed_at - created_at)) / 3600
            ELSE NULL  -- важно для AVG
        END), 
        2
    ), 0) AS avg_completion_time_hours
FROM tasks;
    '''
    query2 = """
    SELECT 
        TRIM(TO_CHAR(created_at AT TIME ZONE :timezone, 'Day')) as day_name,
        COUNT(*) as day_count
    FROM tasks 
    GROUP BY TRIM(TO_CHAR(created_at AT TIME ZONE :timezone, 'Day'))
    """


    try:
        stats = await database.fetch_one(query1)
        days_data = await database.fetch_all(query=query2, values={"timezone":"Europe/Moscow"})
        end_time = (time() - start_time) * 1000
        print(end_time)
        weekday_distribution = {row["day_name"]: row["day_count"] for row in days_data}
        return {"stats":stats, "days_data":days_data, "weekday":weekday_distribution}
    except Exception as e:
        raise HTTPException(
        status_code=500,
        detail=f"Ошибка при вызове аналитики {str(e)}"
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