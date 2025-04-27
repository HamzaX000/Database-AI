import os
import requests
import json
import pyodbc
import re
import nltk
from nltk.tokenize import word_tokenize
from dotenv import load_dotenv

# Vérifier la connexion Internet
def check_internet_connection():
    try:
        response = requests.get("https://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Télécharger les données nécessaires si elles ne sont pas déjà présentes
if check_internet_connection():
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
else:
    print("La connexion Internet n'est pas disponible. Veuillez vérifier votre connexion.")

# Charger les variables d'environnement du fichier .env
load_dotenv()

OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")


class ChatService:
    def __init__(self, server, database, user, password):
        self.server = server
        self.database = database
        self.user = user
        self.password = password

    def is_sql_question(self, question):
        # Mots-clés SQL standards
        sql_keywords = [
            "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
            "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY", "TABLE", "SCHEMA",
            "DATABASE", "SERVER", "COLUMN", "INDEX", "VIEW", "FUNCTION", "PROCEDURE"
        ]
        
        # Phrases spécifiques liées aux bases de données
        sql_phrases = [
            "afficher les données", "chercher dans la table", "combien y a-t-il",
            "trouver les enregistrements", "quelle est la taille", "donnez-moi les colonnes",
            "montrez-moi les résultats", "quels sont les champs", "nombre total",
            "liste des tables", "schéma de", "exécutez cette requête",
            "stockage de la base de données", "taille de la base de données",
            "afficher les enregistrements", "combien d'enregistrements", "trouver les données",
            "quelle est la structure", "donnez-moi les informations", "montrez-moi les informations",
            "quels sont les enregistrements", "nombre d'enregistrements", "liste des enregistrements",
            "schéma de la table", "exécutez la requête", "stockage de la table",
            "taille de la table", "afficher les colonnes", "combien de colonnes",
            "trouver les colonnes", "quelle est la structure de la table", "donnez-moi les colonnes de la table",
            "montrez-moi les colonnes de la table", "quels sont les champs de la table",
            "nombre de champs de la table", "liste des champs de la table", "schéma de la base de données",
            "exécutez cette requête SQL", "stockage de la base de données SQL", "taille de la base de données SQL",
            "afficher les données de la table", "combien d'enregistrements dans la table",
            "trouver les enregistrements dans la table", "quelle est la taille de la table",
            "donnez-moi les informations de la table", "montrez-moi les informations de la table",
            "quels sont les enregistrements de la table", "nombre d'enregistrements de la table",
            "liste des enregistrements de la table", "schéma de la table SQL", "exécutez la requête SQL sur la table",
            "stockage de la table SQL", "taille de la table SQL", "afficher les colonnes de la table SQL",
            "combien de colonnes dans la table SQL", "trouver les colonnes de la table SQL",
            "quelle est la structure de la table SQL", "donnez-moi les colonnes de la table SQL",
            "montrez-moi les colonnes de la table SQL", "quels sont les champs de la table SQL",
            "nombre de champs de la table SQL", "liste des champs de la table SQL"
        ]
        
        # Vérifier si la question contient des mots-clés SQL ou des phrases spécifiques
        if any(re.search(rf'\b{keyword}\b', question, re.IGNORECASE) for keyword in sql_keywords):
            return True
        if any(phrase.lower() in question.lower() for phrase in sql_phrases):
            return True
        
        return False

    def analyze_question(self, question):
        tokens = word_tokenize(question)
        tagged_tokens = nltk.pos_tag(tokens)
        named_entities = nltk.ne_chunk(tagged_tokens)
        
        # Extraire les informations pertinentes
        size_query = False
        for entity in named_entities:
            if isinstance(entity, nltk.tree.Tree):
                if entity.label() == 'ORGANIZATION' and 'base de données' in entity.leaves():
                    size_query = True
                    break
        return size_query

    def extract_context(self, message_history):
        context = ""
        for message in message_history:
            if message["role"] == "user":
                context += f"Utilisateur : {message['content']}\n"
            elif message["role"] == "assistant":
                context += f"Assistant : {message['content']}\n"
        return context.strip()

    def generate_conversational_response(self, message_history):
        context = self.extract_context(message_history)
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Vous êtes un assistant conversationnel utile. Répondez aux questions de manière naturelle et amicale."},
                {"role": "user", "content": context},
                {"role": "user", "content": message_history[-1]["content"]},
            ],
            "temperature": 0.7,
            "max_tokens": 250,
        }
        response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"Erreur lors de la génération de la réponse conversationnelle : {response.text}")

    def generate_sql_query(self, question):
        if self.analyze_question(question):
            return "SELECT SUM(size_on_disk_bytes) AS database_size FROM sys.dm_db_partition_stats;"
        else:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "Vous êtes un assistant qui convertit des questions en langage naturel en requêtes SQL pour SQL Server."},
                    {"role": "user", "content": f"Convertir la question suivante en une requête SQL :\n\n{question}\n\nRequête SQL :"}
                ],
                "temperature": 0.5,
                "max_tokens": 100,
            }
            response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload))
            if response.status_code == 200:
                sql_query = response.json()["choices"][0]["message"]["content"].strip()
                return sql_query
            else:
                raise Exception(f"Erreur lors de la génération de la requête SQL : {response.text}")

    def execute_sql_query(self, sql_query):
        try:
            conn = pyodbc.connect(
                "DRIVER={SQL Server};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.user};"
                f"PWD={self.password};"
            )

            cursor = conn.cursor()
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            cursor.close()
            conn.close()
            return rows, columns
        except pyodbc.Error as e:
            error_message = str(e).split("\n")[0]  # Extraire le premier message d'erreur
            return [], []  # Retourner des résultats vides
        except Exception as e:
            raise Exception(f"Une erreur inattendue s'est produite : {str(e)}")

    def format_query_results_as_html(self, rows, columns):
        if not rows:
            return "Aucun résultat trouvé."
        html_table = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
        html_table += "<tr>"
        for column in columns:
            html_table += f"<th style='padding: 8px; background-color: #f2f2f2;'>{column}</th>"
        html_table += "</tr>"
        for row in rows:
            html_table += "<tr>"
            for value in row:
                html_table += f"<td style='padding: 8px;'>{value}</td>"
            html_table += "</tr>"
        html_table += "</table>"
        return html_table

    def format_query_results_as_json(self, rows, columns):
        result_list = []
        for row in rows:
            result_list.append(dict(zip(columns, row)))
        return json.dumps(result_list, indent=4)

    def get_response(self, message_history):
        user_message = message_history[-1]["content"]
        try:
            if self.is_sql_question(user_message):
                sql_query = self.generate_sql_query(user_message)
                rows, columns = self.execute_sql_query(sql_query)
                if not rows:
                    return "Aucun résultat trouvé."
                html_table = self.format_query_results_as_html(rows, columns)
                json_result = self.format_query_results_as_json(rows, columns)
                return f"La réponse :\n<pre>{sql_query}</pre>\n\nRésultats : {html_table}"
            else:
                return self.generate_conversational_response(message_history)
        except Exception as e:
            return f"Désolé, une erreur s'est produite : {str(e)}"
