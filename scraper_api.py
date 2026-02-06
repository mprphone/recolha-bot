import os
import time
from flask import Flask, request, jsonify
from supabase import create_client
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

app = Flask(__name__)

# Configurações Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # No Render, o Chrome é instalado via render-build.sh nesta pasta:
    chrome_bin = os.path.join(os.environ.get('STORAGE_DIR', '/tmp'), 'chrome/opt/google/chrome/google-chrome')
    if os.path.exists(chrome_bin):
        options.binary_location = chrome_bin
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

@app.route('/recolher-iuc', methods=['POST'])
def api_recolher_iuc():
    data = request.get_json()
    nif = data.get('nif')
    
    try:
        # 1. Buscar a senha na sua tabela de credenciais
        res = supabase.table("clientes_credenciais").select("password_encrypted").eq("username", nif).eq("tipo_servico", "AT").single().execute()
        if not res.data:
            return jsonify({"status": "erro", "mensagem": "NIF não encontrado nas credenciais"}), 404
        
        senha = res.data['password_encrypted']
        driver = get_driver()
        wait = WebDriverWait(driver, 20)

        # 2. Login no Portal das Finanças
        driver.get("https://www.portaldasfinanças.gov.pt/pt/home.action")
        # Aqui entra a lógica de clicar em Login, preencher NIF e Senha
        # Nota: O Portal das Finanças usa campos específicos (username e password)
        
        # Exemplo de fluxo de login (ajustar conforme os IDs atuais do portal)
        driver.get("https://www.portaldasfinancas.gov.pt/main/loginForm.jsp")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(nif)
        driver.find_element(By.ID, "password").send_keys(senha)
        driver.find_element(By.ID, "sbmtLogin").click()

        # 3. Navegar para a página do IUC
        time.sleep(2)
        driver.get("https://sitfiscal.portaldasfinancas.gov.pt/iuc/consultar")

        # 4. Extrair dados e gravar na tabela 'iuc_registos'
        # (Esta parte depende de como as matrículas aparecem na tabela do portal)
        
        supabase.table("iuc_registos").insert({
            "cliente_nif": nif,
            "situacao": "Sucesso",
            "data_recolha": datetime.now().isoformat(),
            "notas": "Login efetuado com sucesso"
        }).execute()

        driver.quit()
        return jsonify({"status": "sucesso", "nif": nif}), 200

    except Exception as e:
        return jsonify({"status": "erro", "detalhes": str(e)}), 500

if __name__ == '__main__':
    app.run(port=10000)
