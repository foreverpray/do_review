from fastapi import FastAPI, Body, File, UploadFile, Form,Depends
from pydantic import BaseModel
import uvicorn
import requests
app = FastAPI()

class GIT_Change(BaseModel):

    code_path: str


class GIT_Change_response(BaseModel):
    result: str


def process_logic(code_path):
    r = requests.get(code_path)
    with open("demo3.zip", "wb") as code:
        code.write(r.content)
    import 
    return "result path"


@app.post("/payload/",
          tags=["接收来自仓库的代码地址"],
          summary="来自仓库的post信息",
          description="当仓库中代码版本发生改变时接收到信息",
          response_model=GIT_Change_response)
async def explain_uibot_code_inner(req: GIT_Change):
    req = req.dict()
    resa = process_logic(req["code_path"])
    return dict(result=resa)


if __name__ == '__main__':
    uvicorn.run(app="fast_demo:app", host="localhost", port=8887, reload=True)