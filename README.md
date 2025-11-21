🔐 KeyFace — Sistema de Autenticação Facial (APS)

KeyFace é um sistema completo de controle de acesso por reconhecimento facial, desenvolvido como APS acadêmica.  
Ele inclui:

✔ Backend em FastAPI**  
✔ Front-end HTML/CSS/JS responsivo**  
✔ Reconhecimento facial com DeepFace**  
✔ Dashboard com gráficos (Chart.js)**  
✔ Controle de níveis de acesso**  
✔ Painéis diferentes para cada tipo de usuário**

🚀 Tecnologias Utilizadas

🔹 Backend
- FastAPI
- Tortoise ORM (SQLite)
- DeepFace + OpenCV
- CORS Middleware
- Uvicorn

🔹 Frontend
- HTML5 + CSS3 (responsivo)
- JavaScript puro
- Captura via Webcam API
- Chart.js para dashboards
- LocalStorage para sessões

🏗️ Estrutura do Projeto

/backend
├── main.py
├── models.py
├── deepface_utils.py
└── uploads/
├── temp/
└── imagens cadastradas

/frontend
├── index.html
├── cadastro.html
├── autenticacao.html
├── painel_ministerio.html
├── painel_diretoria.html
└── painel_comum.html

⚙️ Como executar

1️⃣ Criar ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

2️⃣ Instalar dependências
pip install -r requirements.txt

3️⃣ Rodar a API
uvicorn backend.main:app --reload

4️⃣ Abrir o frontend

Abra index.html no navegador.

🔐 Como funciona o reconhecimento

- O usuário faz cadastro capturando sua foto pela webcam.
- O backend salva a imagem.
- Durante a autenticação:
    - uma nova imagem da webcam é enviada para a API
    - DeepFace compara todas as imagens cadastradas
    - retorna o usuário com menor distância facial

🧭 Níveis de Acesso

Nível	    Usuário	        Tela Acessada
1	        Ministério	    Painel completo (gráficos + logs + usuários)
2	        Diretoria	    Usuários + notícias
3	        Comum	        Notícias internas

📊 Painel do Ministério

Inclui:
- Gráfico de usuários por divisão
- Gráfico por nível de segurança
- Gráfico de acessos recentes
- Lista de usuários cadastrados
- Lista de logs de acesso