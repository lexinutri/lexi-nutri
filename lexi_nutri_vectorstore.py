from openai import OpenAI
import os
import time

# Substitua aqui com sua API key
client = OpenAI(api_key="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")

# Caminho para os arquivos
pasta = "./pdfs"
arquivos = [
    os.path.join(pasta, nome)
    for nome in os.listdir(pasta)
    if os.path.isfile(os.path.join(pasta, nome))
]

# Cria o vector store e faz upload dos arquivos nele
print("Criando vector store e fazendo upload dos arquivos...")
vector_store = client.beta.vector_stores.create(name="LexiNutriDocs")

for caminho in arquivos:
    with open(caminho, "rb") as f:
        client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=[f]
        )

# Cria o assistente com file_search vinculado ao vector_store
print("Criando assistente com file_search...")
assistant = client.beta.assistants.create(
    name="Lexi Nutri",
    instructions="Use apenas os documentos anexados como fonte. Não invente nada.",
    model="gpt-4-turbo",
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
)

# Cria thread e envia pergunta
thread = client.beta.threads.create()

client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Quais são os critérios obrigatórios para rotulagem frontal segundo a legislação atual?"
)

# Executa run
print("Executando run...")
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
)

while True:
    status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    if status.status == "completed":
        break
    elif status.status == "failed":
        print("Erro na execução.")
        exit()
    time.sleep(1)

# Mostra resposta
resposta = client.beta.threads.messages.list(thread_id=thread.id)
print("\n--- Resposta do Assistente ---\n")
for msg in resposta.data:
    print(msg.content[0].text.value)

print(f"Vector Store ID: {vector_store.id}")

print(f"Assistant ID: {assistant.id}")
