from flask import Flask, request, jsonify, render_template, session
from services.chat_service import ChatService
from dotenv import load_dotenv
import os

# Charger les variables d'environnement du fichier .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "une_clé_secrète_par_défaut")  # Clé secrète pour les sessions

# Charger les paramètres de connexion à SQL Server depuis .env
server = os.getenv("SQL_SERVER", "10.46.233.38,1433")
database = os.getenv("SQL_DATABASE", "x3v12")
user = os.getenv("SQL_USER", "sa")
password = os.getenv("SQL_PASSWORD", "Hamzax66*")

# Créer une instance de ChatService avec les paramètres requis
chat_service = ChatService(server=server, database=database, user=user, password=password)

@app.route('/')
def index():
    # Initialiser l'historique des messages dans la session
    if 'message_history' not in session:
        session['message_history'] = []
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')

    # Récupérer l'historique des messages depuis la session
    message_history = session.get('message_history', [])

    # Ajouter le message de l'utilisateur à l'historique
    message_history.append({"role": "user", "content": user_message})

    # Générer la réponse du chatbot en utilisant l'historique
    response = chat_service.get_response(message_history)

    # Ajouter la réponse du chatbot à l'historique
    message_history.append({"role": "assistant", "content": response})

    # Mettre à jour l'historique dans la session
    session['message_history'] = message_history

    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)
