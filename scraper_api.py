import os
from flask import Flask, request, jsonify
from supabase import create_client
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

app = Flask(__name__)

# Configurações lidas do ambiente do Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/recolher-iuc', methods=['POST'])
def api_recolher_iuc():
    data = request.get_json()
    nif = data.get('nif')
    
    # Simulação da lógica que discutimos
    return jsonify({"status": "sucesso", "nif": nif, "mensagem": "Bot iniciado"}), 200

if __name__ == '__main__':
    app.run(port=5000)
