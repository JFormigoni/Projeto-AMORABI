"""
Sistema de Biblioteca AMORABI
Backend Flask com SQLite - 100% local, sem internet necessária
Desenvolvido para a Associação de Moradores e Amigos de Ratones, Barra e Imbituba
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3
import os
from datetime import date
import unicodedata

app = Flask(__name__)
CORS(app)

# Handler de erro global para garantir que sempre retorne JSON
@app.errorhandler(Exception)
def handle_exception(e):
    """Captura todas as exceções não tratadas e retorna JSON."""
    import traceback
    print(f"Erro não tratado: {str(e)}")
    print(traceback.format_exc())
    return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

# Caminho do banco de dados SQLite
DB_PATH = os.path.join(os.path.dirname(__file__), "biblioteca.db")


# ─── FUNÇÕES AUXILIARES ─────────────────────────────────────────────────────

def remover_acentos(texto):
    """Remove acentos de uma string para facilitar buscas."""
    if not texto:
        return ""
    # Normaliza para NFD (decompõe caracteres acentuados)
    # Remove marcas diacríticas (categoria 'Mn')
    nfd = unicodedata.normalize('NFD', texto)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


# ─── INICIALIZAÇÃO DO BANCO DE DADOS ────────────────────────────────────────

def init_db():
    """Cria as tabelas do banco de dados se não existirem."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de Livros
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS livros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isbn TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            ano INTEGER,
            genero TEXT,
            quantidade_total INTEGER DEFAULT 1,
            quantidade_disponivel INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT (date('now'))
        )
    """)

    # Tabela de Associados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula INTEGER UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            data_nascimento TEXT,
            telefone_pais TEXT,
            criado_em TEXT DEFAULT (date('now'))
        )
    """)

    # Tabela de Empréstimos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emprestimos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            livro_id INTEGER NOT NULL,
            aluno_id INTEGER NOT NULL,
            data_emprestimo TEXT NOT NULL,
            data_devolucao_prevista TEXT,
            data_devolucao_real TEXT,
            devolvido INTEGER DEFAULT 0,
            FOREIGN KEY (livro_id) REFERENCES livros(id),
            FOREIGN KEY (aluno_id) REFERENCES alunos(id)
        )
    """)

    # Migração: Renomeia coluna codigo para isbn e adiciona campos de quantidade
    try:
        cursor.execute("PRAGMA table_info(livros)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        if "codigo" in colunas and "isbn" not in colunas:
            print("🔄 Migrando banco de dados: codigo → isbn e adicionando quantidade...")
            cursor.execute("""
                CREATE TABLE livros_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn TEXT UNIQUE NOT NULL,
                    titulo TEXT NOT NULL,
                    autor TEXT NOT NULL,
                    ano INTEGER,
                    genero TEXT,
                    quantidade_total INTEGER DEFAULT 1,
                    quantidade_disponivel INTEGER DEFAULT 1,
                    criado_em TEXT DEFAULT (date('now'))
                )
            """)
            cursor.execute("""
                INSERT INTO livros_new (id, isbn, titulo, autor, ano, genero, quantidade_total, quantidade_disponivel, criado_em)
                SELECT id, codigo, titulo, autor, ano, genero, 
                       1, 
                       CASE WHEN disponivel = 1 THEN 1 ELSE 0 END,
                       criado_em 
                FROM livros
            """)
            cursor.execute("DROP TABLE livros")
            cursor.execute("ALTER TABLE livros_new RENAME TO livros")
            print("✅ Migração de livros concluída!")
    except Exception as e:
        print(f"⚠️ Aviso na migração de livros: {e}")

    # Migração: Adiciona data_nascimento aos alunos
    try:
        cursor.execute("PRAGMA table_info(alunos)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        if "data_nascimento" not in colunas:
            print("🔄 Adicionando campo data_nascimento aos alunos...")
            cursor.execute("ALTER TABLE alunos ADD COLUMN data_nascimento TEXT")
            print("✅ Campo data_nascimento adicionado!")
    except Exception as e:
        print(f"⚠️ Aviso na migração de alunos: {e}")

    # Migração: Converte matrícula de TEXT para INTEGER
    try:
        cursor.execute("PRAGMA table_info(alunos)")
        colunas = {col[1]: col[2] for col in cursor.fetchall()}
        
        if colunas.get("matricula") == "TEXT":
            print("🔄 Migrando matrícula de TEXT para INTEGER...")
            cursor.execute("""
                CREATE TABLE alunos_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    matricula INTEGER UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    data_nascimento TEXT,
                    telefone_pais TEXT,
                    criado_em TEXT DEFAULT (date('now'))
                )
            """)
            cursor.execute("""
                INSERT INTO alunos_new (id, matricula, nome, data_nascimento, telefone_pais, criado_em)
                SELECT id, CAST(matricula AS INTEGER), nome, data_nascimento, telefone_pais, criado_em 
                FROM alunos
            """)
            cursor.execute("DROP TABLE alunos")
            cursor.execute("ALTER TABLE alunos_new RENAME TO alunos")
            print("✅ Migração de matrícula concluída!")
    except Exception as e:
        print(f"⚠️ Aviso na migração de matrícula: {e}")

    # Migração: Renomeia coluna email para telefone_pais se necessário
    try:
        cursor.execute("PRAGMA table_info(alunos)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        if "email" in colunas and "telefone_pais" not in colunas:
            print("🔄 Migrando banco de dados: email → telefone_pais...")
            cursor.execute("""
                CREATE TABLE alunos_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    matricula INTEGER UNIQUE NOT NULL,
                    nome TEXT NOT NULL,
                    data_nascimento TEXT,
                    telefone_pais TEXT,
                    criado_em TEXT DEFAULT (date('now'))
                )
            """)
            cursor.execute("""
                INSERT INTO alunos_new (id, matricula, nome, data_nascimento, telefone_pais, criado_em)
                SELECT id, matricula, nome, data_nascimento, email, criado_em FROM alunos
            """)
            cursor.execute("DROP TABLE alunos")
            cursor.execute("ALTER TABLE alunos_new RENAME TO alunos")
            print("✅ Migração concluída!")
    except Exception as e:
        print(f"⚠️ Aviso na migração: {e}")

    conn.commit()
    conn.close()
    print("✅ Banco de dados inicializado com sucesso!")


def get_db():
    """Retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    return conn


# ─── ROTA PRINCIPAL ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve a página principal da aplicação."""
    return render_template("index.html")


# ─── ROTAS DE LIVROS ─────────────────────────────────────────────────────────

@app.route("/api/livros", methods=["GET"])
def listar_livros():
    """Retorna todos os livros cadastrados ou busca por ID/ISBN/título."""
    busca = request.args.get("busca", "").strip()
    ordenar_por = request.args.get("ordenar_por", "titulo").strip()
    ordem = request.args.get("ordem", "ASC").strip().upper()
    
    # Validação dos parâmetros de ordenação
    colunas_validas = ["isbn", "titulo", "autor", "ano", "genero", "quantidade_total", "quantidade_disponivel", "id"]
    if ordenar_por not in colunas_validas:
        ordenar_por = "titulo"
    
    if ordem not in ["ASC", "DESC"]:
        ordem = "ASC"
    
    conn = get_db()
    
    if busca:
        # Se a busca for apenas números, busca exata por ID
        if busca.isdigit():
            livros = conn.execute(
                f"""SELECT * FROM livros 
                   WHERE id = ?
                   ORDER BY {ordenar_por} {ordem}""",
                (int(busca),)
            ).fetchall()
            
            # Se não encontrou por ID, não faz busca parcial
            if not livros:
                conn.close()
                return jsonify([])
        else:
            # Busca com normalização de acentos para título e autor
            # Pega todos os livros e filtra em Python para ignorar acentos
            todos_livros = conn.execute(
                f"SELECT * FROM livros ORDER BY {ordenar_por} {ordem}"
            ).fetchall()
            
            busca_normalizada = remover_acentos(busca.lower())
            livros = [
                livro for livro in todos_livros
                if (busca_normalizada in remover_acentos(livro["titulo"].lower()) or
                    busca_normalizada in remover_acentos(livro["autor"].lower()) or
                    busca.lower() in livro["isbn"].lower())
            ]
    else:
        livros = conn.execute(
            f"SELECT * FROM livros ORDER BY {ordenar_por} {ordem}"
        ).fetchall()
    
    conn.close()
    return jsonify([dict(l) for l in livros])


@app.route("/api/livros", methods=["POST"])
def adicionar_livro():
    """Cadastra um novo livro."""
    dados = request.json

    # Validação básica dos campos obrigatórios
    if not dados.get("isbn") or not dados.get("titulo") or not dados.get("autor"):
        return jsonify({"erro": "ISBN, título e autor são obrigatórios."}), 400

    quantidade = dados.get("quantidade_total", 1)
    if quantidade < 1:
        return jsonify({"erro": "Quantidade deve ser pelo menos 1."}), 400

    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO livros (isbn, titulo, autor, ano, genero, quantidade_total, quantidade_disponivel)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                dados["isbn"].strip(),
                dados["titulo"].strip(),
                dados["autor"].strip(),
                dados.get("ano"),
                dados.get("genero", "").strip(),
                quantidade,
                quantidade,
            ),
        )
        conn.commit()
        return jsonify({"mensagem": "Livro cadastrado com sucesso!"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"erro": f"Já existe um livro com o ISBN '{dados['isbn']}'."}), 409
    finally:
        conn.close()


@app.route("/api/livros/<int:livro_id>", methods=["PUT"])
def editar_livro(livro_id):
    """Edita um livro existente."""
    dados = request.json

    if not dados.get("isbn") or not dados.get("titulo") or not dados.get("autor"):
        return jsonify({"erro": "ISBN, título e autor são obrigatórios."}), 400

    quantidade = dados.get("quantidade_total", 1)
    if quantidade < 1:
        return jsonify({"erro": "Quantidade deve ser pelo menos 1."}), 400

    conn = get_db()
    try:
        # Verifica se o livro existe
        livro_atual = conn.execute("SELECT * FROM livros WHERE id = ?", (livro_id,)).fetchone()
        if not livro_atual:
            conn.close()
            return jsonify({"erro": "Livro não encontrado."}), 404

        # Calcula a diferença de quantidade
        diferenca = quantidade - livro_atual["quantidade_total"]
        nova_disponivel = livro_atual["quantidade_disponivel"] + diferenca

        # Verifica se a nova quantidade disponível é válida
        if nova_disponivel < 0:
            conn.close()
            return jsonify({"erro": f"Não é possível reduzir a quantidade. Há {livro_atual['quantidade_total'] - livro_atual['quantidade_disponivel']} exemplar(es) emprestado(s)."}), 400

        conn.execute(
            """UPDATE livros 
               SET isbn = ?, titulo = ?, autor = ?, ano = ?, genero = ?, 
                   quantidade_total = ?, quantidade_disponivel = ?
               WHERE id = ?""",
            (
                dados["isbn"].strip(),
                dados["titulo"].strip(),
                dados["autor"].strip(),
                dados.get("ano"),
                dados.get("genero", "").strip(),
                quantidade,
                nova_disponivel,
                livro_id,
            ),
        )
        conn.commit()
        return jsonify({"mensagem": "Livro atualizado com sucesso!"})
    except sqlite3.IntegrityError:
        return jsonify({"erro": f"Já existe outro livro com o ISBN '{dados['isbn']}'."}), 409
    finally:
        conn.close()


@app.route("/api/livros/<int:livro_id>", methods=["DELETE"])
def excluir_livro(livro_id):
    """Exclui um livro pelo ID (somente se não tiver empréstimo ativo)."""
    conn = get_db()

    # Verifica se há empréstimo ativo
    emprestimo_ativo = conn.execute(
        "SELECT id FROM emprestimos WHERE livro_id = ? AND devolvido = 0", (livro_id,)
    ).fetchone()

    if emprestimo_ativo:
        conn.close()
        return jsonify({"erro": "Não é possível excluir: livro possui empréstimo ativo."}), 400

    conn.execute("DELETE FROM livros WHERE id = ?", (livro_id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Livro excluído com sucesso!"})


# ─── ROTAS DE ASSOCIADOS ─────────────────────────────────────────────────────

@app.route("/api/alunos", methods=["GET"])
def listar_alunos():
    """Retorna todos os associados cadastrados ou busca por matrícula/nome."""
    busca = request.args.get("busca", "").strip()
    ordenar_por = request.args.get("ordenar_por", "matricula").strip()
    ordem = request.args.get("ordem", "ASC").strip().upper()
    
    # Validação dos parâmetros de ordenação
    colunas_validas = ["matricula", "nome", "data_nascimento", "id"]
    if ordenar_por not in colunas_validas:
        ordenar_por = "matricula"
    
    if ordem not in ["ASC", "DESC"]:
        ordem = "ASC"
    
    conn = get_db()
    
    if busca:
        # Se a busca for apenas números, busca exata por ID ou matrícula
        if busca.isdigit():
            busca_int = int(busca)
            alunos = conn.execute(
                f"""SELECT * FROM alunos 
                   WHERE id = ? OR matricula = ?
                   ORDER BY {ordenar_por} {ordem}""",
                (busca_int, busca_int)
            ).fetchall()
        else:
            # Busca com normalização de acentos
            # Pega todos os alunos e filtra em Python para ignorar acentos
            todos_alunos = conn.execute(
                f"SELECT * FROM alunos ORDER BY {ordenar_por} {ordem}"
            ).fetchall()
            
            busca_normalizada = remover_acentos(busca.lower())
            alunos = [
                aluno for aluno in todos_alunos
                if busca_normalizada in remover_acentos(aluno["nome"].lower())
            ]
    else:
        alunos = conn.execute(
            f"SELECT * FROM alunos ORDER BY {ordenar_por} {ordem}"
        ).fetchall()
    
    conn.close()
    return jsonify([dict(a) for a in alunos])


@app.route("/api/alunos", methods=["POST"])
def adicionar_aluno():
    """Cadastra um novo associado com matrícula automática."""
    dados = request.json

    # Validação dos campos obrigatórios
    if not dados.get("nome"):
        return jsonify({"erro": "Nome é obrigatório."}), 400
    
    if not dados.get("data_nascimento") or not dados.get("data_nascimento").strip():
        return jsonify({"erro": "Data de nascimento é obrigatória."}), 400
    
    if not dados.get("telefone_pais") or not dados.get("telefone_pais").strip():
        return jsonify({"erro": "Telefone é obrigatório."}), 400

    conn = get_db()
    try:
        # Gera a próxima matrícula automaticamente (INTEGER)
        ultima_matricula = conn.execute(
            "SELECT MAX(matricula) FROM alunos"
        ).fetchone()[0]
        
        proxima_matricula = (ultima_matricula or 0) + 1
        
        conn.execute(
            "INSERT INTO alunos (matricula, nome, data_nascimento, telefone_pais) VALUES (?, ?, ?, ?)",
            (
                proxima_matricula,
                dados["nome"].strip(),
                dados["data_nascimento"].strip(),
                dados["telefone_pais"].strip(),
            ),
        )
        conn.commit()
        return jsonify({
            "mensagem": f"Associado cadastrado com sucesso! Matrícula: {proxima_matricula}",
            "matricula": proxima_matricula
        }), 201
    except Exception as e:
        return jsonify({"erro": f"Erro ao cadastrar associado: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/alunos/<int:aluno_id>", methods=["PUT"])
def editar_aluno(aluno_id):
    """Edita um associado existente."""
    dados = request.json

    # Validação dos campos obrigatórios
    if not dados.get("nome"):
        return jsonify({"erro": "Nome é obrigatório."}), 400
    
    if not dados.get("telefone_pais") or not dados.get("telefone_pais").strip():
        return jsonify({"erro": "Telefone é obrigatório."}), 400

    conn = get_db()
    try:
        # Verifica se o associado existe
        aluno = conn.execute("SELECT * FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
        if not aluno:
            conn.close()
            return jsonify({"erro": "Associado não encontrado."}), 404

        conn.execute(
            """UPDATE alunos 
               SET nome = ?, data_nascimento = ?, telefone_pais = ?
               WHERE id = ?""",
            (
                dados["nome"].strip(),
                dados.get("data_nascimento", "").strip() or None,
                dados["telefone_pais"].strip(),
                aluno_id,
            ),
        )
        conn.commit()
        return jsonify({"mensagem": "Associado atualizado com sucesso!"})
    except Exception as e:
        return jsonify({"erro": f"Erro ao atualizar associado: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/alunos/<int:aluno_id>", methods=["DELETE"])
def excluir_aluno(aluno_id):
    """Exclui um associado pelo ID (somente se não tiver empréstimo ativo)."""
    conn = get_db()

    emprestimo_ativo = conn.execute(
        "SELECT id FROM emprestimos WHERE aluno_id = ? AND devolvido = 0", (aluno_id,)
    ).fetchone()

    if emprestimo_ativo:
        conn.close()
        return jsonify({"erro": "Não é possível excluir: associado possui empréstimo ativo."}), 400

    conn.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Associado excluído com sucesso!"})


# ─── ROTAS DE EMPRÉSTIMOS ─────────────────────────────────────────────────────

@app.route("/api/emprestimos", methods=["GET"])
def listar_emprestimos():
    """Retorna todos os empréstimos com dados do livro e do aluno."""
    # Filtros opcionais
    filtro_status = request.args.get("status", "").strip()  # "ativo", "devolvido", "atrasado"
    filtro_aluno = request.args.get("aluno", "").strip()
    filtro_livro = request.args.get("livro", "").strip()
    ordenar_por = request.args.get("ordenar_por", "data_emprestimo").strip()
    ordem = request.args.get("ordem", "DESC").strip().upper()
    
    # Validação dos parâmetros de ordenação
    colunas_validas = ["data_emprestimo", "data_devolucao_prevista", "data_devolucao_real", "livro_titulo", "aluno_nome", "aluno_matricula", "devolvido"]
    if ordenar_por not in colunas_validas:
        ordenar_por = "data_emprestimo"
    
    if ordem not in ["ASC", "DESC"]:
        ordem = "DESC"
    
    # Mapeia nomes de colunas para o SQL correto
    ordem_sql = {
        "livro_titulo": "l.titulo",
        "aluno_nome": "a.nome",
        "aluno_matricula": "a.matricula",
        "data_emprestimo": "e.data_emprestimo",
        "data_devolucao_prevista": "e.data_devolucao_prevista",
        "data_devolucao_real": "e.data_devolucao_real",
        "devolvido": "e.devolvido"
    }.get(ordenar_por, f"e.{ordenar_por}")
    
    conn = get_db()
    
    query = f"""
        SELECT
            e.id,
            e.data_emprestimo,
            e.data_devolucao_prevista,
            e.data_devolucao_real,
            e.devolvido,
            l.id AS livro_id,
            l.titulo AS livro_titulo,
            l.isbn AS livro_isbn,
            a.id AS aluno_id,
            a.nome AS aluno_nome,
            a.matricula AS aluno_matricula,
            a.telefone_pais AS aluno_telefone
        FROM emprestimos e
        JOIN livros l ON e.livro_id = l.id
        JOIN alunos a ON e.aluno_id = a.id
    """
    
    conditions = []
    params = []
    
    if filtro_status == "ativo":
        conditions.append("e.devolvido = 0")
    elif filtro_status == "devolvido":
        conditions.append("e.devolvido = 1")
    elif filtro_status == "atrasado":
        conditions.append("e.devolvido = 0 AND e.data_devolucao_prevista < date('now')")
    
    if filtro_aluno:
        conditions.append("(a.nome LIKE ? OR a.matricula LIKE ?)")
        params.extend([f"%{filtro_aluno}%", f"%{filtro_aluno}%"])
    
    if filtro_livro:
        conditions.append("(l.titulo LIKE ? OR l.isbn LIKE ?)")
        params.extend([f"%{filtro_livro}%", f"%{filtro_livro}%"])
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # Adiciona ordenação secundária para manter consistência
    if ordenar_por == "devolvido":
        query += f" ORDER BY {ordem_sql} {ordem}, e.data_emprestimo DESC"
    else:
        query += f" ORDER BY {ordem_sql} {ordem}"
    
    emprestimos = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(e) for e in emprestimos])


@app.route("/api/emprestimos", methods=["POST"])
def registrar_emprestimo():
    """Registra um ou mais empréstimos."""
    try:
        dados = request.json
        
        if not dados:
            return jsonify({"erro": "Dados não fornecidos."}), 400

        # Suporta tanto livro_id único quanto livros_ids (array)
        livros_ids = dados.get("livros_ids", [])
        if not livros_ids and dados.get("livro_id"):
            livros_ids = [dados["livro_id"]]
        
        if not livros_ids or not dados.get("aluno_id"):
            return jsonify({"erro": "Pelo menos um livro e um aluno são obrigatórios."}), 400
        
        # Validação obrigatória da data de devolução prevista
        if not dados.get("data_devolucao_prevista"):
            return jsonify({"erro": "A data de devolução prevista é obrigatória."}), 400

        conn = get_db()
        data_hoje = date.today().isoformat()
        emprestimos_criados = 0
        erros = []

        try:
            for livro_id in livros_ids:
                # Verifica se o livro está disponível
                livro = conn.execute(
                    "SELECT titulo, quantidade_disponivel FROM livros WHERE id = ?", (livro_id,)
                ).fetchone()

                if not livro:
                    erros.append(f"Livro ID {livro_id} não encontrado.")
                    continue

                if livro["quantidade_disponivel"] <= 0:
                    erros.append(f"'{livro['titulo']}' não possui exemplares disponíveis.")
                    continue

                # Registra o empréstimo
                conn.execute(
                    """INSERT INTO emprestimos (livro_id, aluno_id, data_emprestimo, data_devolucao_prevista)
                       VALUES (?, ?, ?, ?)""",
                    (
                        livro_id,
                        dados["aluno_id"],
                        data_hoje,
                        dados.get("data_devolucao_prevista"),
                    ),
                )

                # Decrementa a quantidade disponível
                conn.execute(
                    "UPDATE livros SET quantidade_disponivel = quantidade_disponivel - 1 WHERE id = ?", (livro_id,)
                )
                emprestimos_criados += 1

            conn.commit()
            
            if emprestimos_criados == 0:
                return jsonify({"erro": "Nenhum empréstimo foi registrado. " + " ".join(erros)}), 400
            
            mensagem = f"{emprestimos_criados} empréstimo(s) registrado(s) com sucesso!"
            if erros:
                mensagem += " Avisos: " + " ".join(erros)
            
            return jsonify({"mensagem": mensagem}), 201
            
        except Exception as e:
            conn.rollback()
            print(f"Erro ao registrar empréstimos: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return jsonify({"erro": f"Erro ao registrar empréstimos: {str(e)}"}), 500
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Erro geral: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"erro": f"Erro ao processar requisição: {str(e)}"}), 500


@app.route("/api/emprestimos/<int:emprestimo_id>", methods=["PUT"])
def editar_emprestimo(emprestimo_id):
    """Edita a data de devolução prevista de um empréstimo."""
    dados = request.json

    conn = get_db()
    try:
        # Verifica se o empréstimo existe
        emprestimo = conn.execute(
            "SELECT * FROM emprestimos WHERE id = ?", (emprestimo_id,)
        ).fetchone()

        if not emprestimo:
            conn.close()
            return jsonify({"erro": "Empréstimo não encontrado."}), 404

        if emprestimo["devolvido"]:
            conn.close()
            return jsonify({"erro": "Não é possível editar um empréstimo já devolvido."}), 400

        conn.execute(
            "UPDATE emprestimos SET data_devolucao_prevista = ? WHERE id = ?",
            (dados.get("data_devolucao_prevista"), emprestimo_id),
        )
        conn.commit()
        return jsonify({"mensagem": "Data de devolução atualizada com sucesso!"})
    except Exception as e:
        return jsonify({"erro": f"Erro ao atualizar empréstimo: {str(e)}"}), 500
    finally:
        conn.close()


@app.route("/api/emprestimos/<int:emprestimo_id>/devolver", methods=["PUT"])
def devolver_livro(emprestimo_id):
    """Marca um empréstimo como devolvido."""
    conn = get_db()

    emprestimo = conn.execute(
        "SELECT livro_id, devolvido FROM emprestimos WHERE id = ?", (emprestimo_id,)
    ).fetchone()

    if not emprestimo:
        conn.close()
        return jsonify({"erro": "Empréstimo não encontrado."}), 404

    if emprestimo["devolvido"]:
        conn.close()
        return jsonify({"erro": "Este empréstimo já foi devolvido."}), 400

    data_hoje = date.today().isoformat()

    # Atualiza o empréstimo
    conn.execute(
        "UPDATE emprestimos SET devolvido = 1, data_devolucao_real = ? WHERE id = ?",
        (data_hoje, emprestimo_id),
    )

    # Incrementa a quantidade disponível
    conn.execute(
        "UPDATE livros SET quantidade_disponivel = quantidade_disponivel + 1 WHERE id = ?", 
        (emprestimo["livro_id"],)
    )

    conn.commit()
    conn.close()
    return jsonify({"mensagem": "Livro devolvido com sucesso!"})


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Retorna estatísticas gerais para o painel."""
    conn = get_db()
    total_livros = conn.execute("SELECT SUM(quantidade_total) FROM livros").fetchone()[0] or 0
    livros_disponiveis = conn.execute("SELECT SUM(quantidade_disponivel) FROM livros").fetchone()[0] or 0
    total_alunos = conn.execute("SELECT COUNT(*) FROM alunos").fetchone()[0]
    emprestimos_ativos = conn.execute("SELECT COUNT(*) FROM emprestimos WHERE devolvido = 0").fetchone()[0]
    conn.close()

    return jsonify({
        "total_livros": total_livros,
        "livros_disponiveis": livros_disponiveis,
        "livros_emprestados": total_livros - livros_disponiveis,
        "total_alunos": total_alunos,
        "emprestimos_ativos": emprestimos_ativos,
    })


# ─── INICIALIZAÇÃO ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("\n📚 Sistema AMORABI iniciado!")
    print("🌐 Acesse: http://localhost:5000\n")
    app.run(debug=True, port=5000)
