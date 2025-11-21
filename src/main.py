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
import cv2
from backend.deepface_utils import reconhecer_usuario
from backend.deepface_cache import get_cache
import asyncio
from backend.models import User

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

        with open("index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Erro 404: Arquivo index.html não encontrado.</h1><p>Certifique-se de que o arquivo está na mesma pasta do main.py.</p>", status_code=404)

# Rota para a Tela de Cadastro
@app.get("/cadastro.html", response_class=HTMLResponse)
async def get_cadastro_page():
    try:
        with open("cadastro.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Erro: Arquivo cadastro.html não encontrado.</h1>", status_code=404)

# Rota para a Tela de Autenticação
@app.get("/autenticacao.html", response_class=HTMLResponse)
async def get_autenticacao_page():
    try:
        with open("autenticacao.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Erro: Arquivo autenticacao.html não encontrado.</h1>", status_code=404)

# Rota para a Tela de Sucesso (após o cadastro)
@app.get("/sucesso_cadastro.html", response_class=HTMLResponse)
async def get_sucesso_page():
    try:
        with open("sucesso_cadastro.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Erro: Arquivo sucesso_cadastro.html não encontrado.</h1>", status_code=404)

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
    # após criar user:
    cache = get_cache()
    # tenta atualizar cache com a nova imagem (não bloqueante)
    try:
        cache.update_single(file_dest)
    except Exception:
        pass
    

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
    import uuid

    UPLOAD_TEMP = "backend/uploads/temp"
    os.makedirs(UPLOAD_TEMP, exist_ok=True)

    # gera nome seguro
    temp_path = os.path.abspath(os.path.join(UPLOAD_TEMP, f"{uuid.uuid4()}.jpg"))

    # salva imagem temporária
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # busca todos os usuários cadastrados
    usuarios = await User.all().values("id","nome","nivel_seguranca","image_path")

    # converte paths para absoluto
    paths = [os.path.abspath(u["image_path"]) for u in usuarios if u["image_path"]]

    # chama deepface
    result = reconhecer_usuario(temp_path, paths)

    # apaga imagem temporária
    os.remove(temp_path)

    # identifica usuario
    usuario = None
    if result and "db_img" in result:
        usuario = next(
            (u for u in usuarios if os.path.abspath(u["image_path"]) == os.path.abspath(result["db_img"])),
            None
        )

    # registra log
    await Log.create(
        nome=usuario["nome"] if usuario else None,
        nivel_seguranca=usuario["nivel_seguranca"] if usuario else None,
        acesso=bool(result and usuario),
        msg="Acesso permitido" if usuario else "Usuário não reconhecido"
    )

    # retorno para o front
    if not usuario:
        return {"acesso": False, "msg": "Usuário não reconhecido!"}

    return {
        "acesso": True,
        "nome": usuario["nome"],
        "nivel_seguranca": usuario["nivel_seguranca"],
        "distance": result["distance"]
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

async def build_cache_on_startup():
    cache = get_cache()
    usuarios = await User.all().values("image_path")
    paths = [u["image_path"] for u in usuarios if u["image_path"]]
    cache.build_from_paths(paths)