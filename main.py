from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import pymysql

app = FastAPI(
    title="API de Ciência de Dados",
    description="API construída pela turma durante a Aula 1.",
    version="1.0.0",
)

    
    
def conectar():
# Em um sistema real, a senha ficaria numa variável de ambiente,
# nunca escrita no código.
    return pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="ceub123456",
        database="escola",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


@app.get("/")
def inicio():
    return {"mensagem": "Minha primeira API!"}


@app.get("/sobre")
def sobre():
    return {
        "disciplina": "Programação para Ciência de Dados",
        "aula": 1,
        "versao_api": "1.0.0",
    }



@app.get("/saude")
def saude():
    try:
        with conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute("SELECT DATABASE() AS banco, VERSION() AS versao")
                info = cursor.fetchone()
    except pymysql.err.OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao banco de dados",
        )

    return {
        "status": "ok",
        "banco": info["banco"],
        "versao": info["versao"],
    }


@app.get("/alunos")
def listar_alunos(curso: str | None = None, ano: int | None = None):
    sql = "SELECT a.id, a.nome, a.email, a.ano_ingresso, c.sigla AS curso FROM alunos a JOIN cursos c ON c.id = a.curso_id"
    condicoes = []
    parametros = []
    if curso:
        condicoes.append("c.sigla = %s")
        parametros.append(curso)
    if ano:
        condicoes.append("a.ano_ingresso = %s")
        parametros.append(ano)
    if condicoes:
        sql += " WHERE " + " AND ".join(condicoes)
    sql += " ORDER BY a.id"
    with conectar() as conexao:
     with conexao.cursor() as cursor:
      cursor.execute(sql, parametros)
      alunos = cursor.fetchall()

     return {
         "total": len(alunos),
           "alunos": alunos,
}

@app.get("/alunos/{aluno_id}")
def consultar_aluno(aluno_id: int):
    sql = "SELECT a.id, a.nome, a.email, a.ano_ingresso, c.sigla AS curso FROM alunos a JOIN cursos c ON c.id = a.curso_id WHERE a.id = %s"
    with conectar() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute(sql, (aluno_id,))
            aluno = cursor.fetchone()
    if aluno is None:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return aluno

@app.get("/alunos/{aluno_id}/notas")
def notas_do_aluno(aluno_id: int):
    with conectar() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute("SELECT nome FROM alunos WHERE id = %s", (aluno_id,))
            aluno = cursor.fetchone()

            if aluno is None:
                raise HTTPException(status_code=404, detail="Aluno não encontrado")

            cursor.execute(
                "SELECT d.nome AS disciplina, n.nota "
                "FROM notas n "
                "JOIN disciplinas d ON d.id = n.disciplina_id "
                "WHERE n.aluno_id = %s "
                "ORDER BY d.nome",
                (aluno_id,),
            )

            notas = cursor.fetchall()
            media = None
            if notas:
                media = round(sum(n["nota"] for n in notas) / len(notas), 2)

            return {
                "aluno": aluno["nome"],
                "quantidade": len(notas),
                "media": media,
                "notas": notas,
            }

from pydantic import BaseModel, EmailStr

class NovoAluno(BaseModel):
    nome: str
    email: EmailStr
    curso_id: int
    ano_ingresso: int

@app.post("/alunos", status_code=201)
def cadastrar_aluno(novo_aluno: NovoAluno):
    sql = """
        INSERT INTO alunos (nome, email, curso_id, ano_ingresso)
        VALUES (%s, %s, %s, %s)
    """
    valores = (
        novo_aluno.nome,
        novo_aluno.email,
        novo_aluno.curso_id,
        novo_aluno.ano_ingresso,
    )

    try:
        with conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql, valores)
                novo_id = cursor.lastrowid
            conexao.commit()
    except pymysql.err.IntegrityError as erro:
        codigo = erro.args[0]
        if codigo == 1062:
            raise HTTPException(
                status_code=409,
                detail="Já existe um aluno com este e-mail",
            )
        if codigo == 1452:
            raise HTTPException(
                status_code=422,
                detail="Curso não encontrado",
            )
        raise

    return {
        "mensagem": "Aluno cadastrado com sucesso",
        "id": novo_id,
    }
class AtualizarAluno(BaseModel):
    nome: str
    email: EmailStr
    curso_id: int
    ano_ingresso: int


@app.put("/alunos/{aluno_id}")
def atualizar_aluno(aluno_id: int, aluno: NovoAluno):
    sql = """
        UPDATE alunos
        SET nome = %s,
            email = %s,
            curso_id = %s,
            ano_ingresso = %s
        WHERE id = %s
    """

    valores = (
        aluno.nome,
        aluno.email,
        aluno.curso_id,
        aluno.ano_ingresso,
        aluno_id,
    )

    try:
        with conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(sql, valores)

                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=404,
                        detail="Aluno não encontrado"
                    )

            conexao.commit()

    except pymysql.err.IntegrityError as erro:
        codigo = erro.args[0]

        if codigo == 1062:
            raise HTTPException(
                status_code=409,
                detail="Já existe um aluno com este e-mail"
            )

        if codigo == 1452:
            raise HTTPException(
                status_code=422,
                detail="Curso não encontrado"
            )

        raise

    return {
        "mensagem": "Aluno atualizado com sucesso",
        "id": aluno_id, }
@app.delete("/alunos/{aluno_id}")
def deletar_aluno(aluno_id: int):
    try:
        with conectar() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM alunos WHERE id = %s",
                    (aluno_id,)
                )

                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=404,
                        detail="Aluno não encontrado"
                    )

            conexao.commit()

    except pymysql.err.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Não foi possível excluir o aluno"
        )

    return {
        "mensagem": "Aluno excluído com sucesso",
        "id": aluno_id
    }