from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import time
import os

client = OpenAI(api_key="sua-api-key-aqui")

app = FastAPI()

# Permitir requisições do seu domínio WordPress
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Substitua por seu domínio real para segurança
    allow_methods=["*"],
    allow_headers=["*"],
)

# ID fixo do seu vector store (opcional, se quiser reaproveitar)
VECTOR_STORE_ID = None

# Carrega arquivos e cria vector store apenas uma vez
def inicializar_vector_store():
    global VECTOR_STORE_ID
    if VECTOR_STORE_ID:
        return VECTOR_STORE_ID

    pasta = "./pdfs"
    arquivos = [
        os.path.join(pasta, nome)
        for nome in os.listdir(pasta)
        if os.path.isfile(os.path.join(pasta, nome))
    ]

    vector_store = client.beta.vector_stores.create(name="LexiNutriDocs")
    for caminho in arquivos:
        with open(caminho, "rb") as f:
            client.beta.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=[f]
            )

    VECTOR_STORE_ID = vector_store.id
    return VECTOR_STORE_ID

# Modelo do corpo da requisição
class Pergunta(BaseModel):
    pergunta: str

@app.post("/lexi-nutri")
def responder(pergunta: Pergunta):
    vector_store_id = inicializar_vector_store()

    assistant = client.beta.assistants.create(
        name="Lexi Nutri",
        instructions="Responda com base nos documentos anexados. Sempre que mencionar um anexo de legislação, traga o conteúdo completo se possível.",
        model="gpt-4-turbo",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
    )

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=pergunta.pergunta
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    while True:
        status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if status.status == "completed":
            break
        elif status.status == "failed":
            return {"resposta": "Erro na execução do assistente."}
        time.sleep(1)

    resposta = client.beta.threads.messages.list(thread_id=thread.id)
    texto = resposta.data[0].content[0].text.value
    return {"resposta": texto}
