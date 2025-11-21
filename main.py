from fastapi import FastAPI, File, UploadFile, Form, HTTPException
import os
import shutil
from tortoise.contrib.fastapi import register_tortoise
from fastapi.middleware.cors import CORSMiddleware
from backend.models import User
from tortoise.transactions import in_transaction
from backend.deepface_utils import reconhecer_usuario
from backend.models import Log
from fastapi.responses import HTMLResponse 

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "*", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos os métodos (POST, GET, etc.)
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'backend/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def get_root_page():
    try:

        with open("tela_inicial.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Erro 404: Arquivo tela_inicial.html não encontrado.</h1><p>Certifique-se de que o arquivo está na mesma pasta do main.py.</p>", status_code=404)


# Este endpoint já insere no banco e retorna o usuário criado.
@app.post("/usuario")
async def criar_usuario(
    nome: str = Form(...), 
    nivel_seguranca: int = Form(...), 
    division: str = Form(...), 
    file: UploadFile = File(...)
    ):

    # Verifica se o nível está correto
    if nivel_seguranca not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="O nível de segurança deve ser 1, 2 ou 3.")

    file_ext = os.path.splitext(file.filename)[1]
    # Cria o caminho do arquivo com o nome e nível do usuário
    file_dest = os.path.join(UPLOAD_FOLDER, f"{nome.replace(' ', '_')}_{nivel_seguranca}{file_ext}")
    
    # Salva o arquivo
    with open(file_dest, "wb") as dest:
        shutil.copyfileobj(file.file, dest)
        

    async with in_transaction():
        # Cria o registro no banco de dados
        user = await User.create(
            nome=nome,
            nivel_seguranca=nivel_seguranca,
            division=division,
            image_path=file_dest
        )
        return {"id": user.id, 
                "nome": user.nome, 
                "nivel_seguranca": user.nivel_seguranca,
                "division": user.division,
                "image_path": user.image_path,
                }
    

# Isso retorna todos os usuários cadastrados, ajudando a validar facilmente o banco e a visualização dos dados pela API.
@app.get("/usuarios")
async def listar_usuarios():
    usuarios = await User.all().values(
        "id", 
        "nome", 
        "nivel_seguranca", 
        "division", 
        "image_path")
    return usuarios

# Endpoint de autenticação facial
@app.post("/autenticar")
async def autenticar(file: UploadFile = File(...)):
    UPLOAD_TEMP = "backend/uploads/temp"
    os.makedirs(UPLOAD_TEMP, exist_ok=True)
    temp_path = os.path.join(UPLOAD_TEMP, file.filename)
    
    # Salva a imagem temporária de autenticação
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Carregar todos os usuários e paths das imagens
    usuarios = await User.all().values("id", "nome", "nivel_seguranca", "image_path")
    paths = [u["image_path"] for u in usuarios if u["image_path"]]
    
    # Chama a função de reconhecimento do DeepFace
    result = reconhecer_usuario(temp_path, paths)
    os.remove(temp_path)

    # Inicializa usuario como None para o caso de não haver match
    usuario = None
    if result and "db_img" in result:
        # Identificar usuário pelo caminho da imagem que foi reconhecida
        usuario = next((u for u in usuarios if u["image_path"] == result["db_img"]), None)
    
    # Log da tentativa
    await Log.create(
        nome=usuario["nome"] if usuario else None,
        nivel_seguranca=usuario["nivel_seguranca"] if usuario else None,
        acesso=bool(result and usuario),
        msg=("Acesso permitido" if result and usuario else "Usuário não reconhecido ou acesso negado")
    )

    if not result:
        return {"acesso": False, "msg": "Usuário não reconhecido!"}
    
    if usuario:
        return {
            "acesso": True,
            "nome": usuario["nome"],
            "nivel_seguranca": usuario["nivel_seguranca"],
            "distance": result["distance"]
        }
    else:
        return {
            "acesso": False, 
            "msg": "Usuário não encontrado no banco!"
        }

# Para limpar todos os usuários (útil para testes)
@app.delete("/usuarios/apagar_todos")
async def apagar_todos():
    await User.all().delete()
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
    return {"resultado": "Todos os usuários e arquivos removidos."}

# Listar logs de acesso (Para que eu tenha controle das tentativas de acesso)
@app.get("/logs")
async def listar_logs():
    return await Log.all().order_by("-timestamp").values()


# Configuração do Tortoise ORM
register_tortoise(
    app,
    db_url="sqlite://backend/db.sqlite3",
    modules={"models": ["backend.models"]},
    generate_schemas=True,
    add_exception_handlers=True,
)