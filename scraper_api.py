import os
import time
import traceback
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

# Configurações Supabase (Lidas das Environment Variables do Render)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_driver():
    print("--- [CONFIG] Iniciando Selenium WebDriver ---")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Lista de caminhos possíveis para o Chrome no ambiente Render
    possible_bins = [
        "/usr/bin/google-chrome",
        "/opt/google/chrome/google-chrome",
        os.path.join(os.getcwd(), 'chrome/opt/google/chrome/google-chrome'),
        os.path.join(os.environ.get('STORAGE_DIR', '/tmp'), 'chrome/opt/google/chrome/google-chrome')
    ]
    
    chrome_found = False
    for bin_path in possible_bins:
        if os.path.exists(bin_path):
            print(f"✅ Sucesso: Chrome encontrado em: {bin_path}")
            options.binary_location = bin_path
            chrome_found = True
            break
    
    if not chrome_found:
        print("❌ CRÍTICO: O binário do Chrome não foi encontrado em nenhum caminho esperado.")

    # Instalação automática do Driver compatível
    print("A instalar/atualizar o ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

@app.route('/recolher-iuc', methods=['POST'])
def api_recolher_iuc():
    data = request.get_json()
    nif = data.get('nif')
    print(f"\n--- [INÍCIO] Tarefa recebida para NIF: {nif} ---")
    
    driver = None
    try:
        # 1. Procurar credenciais no Supabase
        print("A consultar tabela 'clientes_credenciais'...")
        res = supabase.table("clientes_credenciais").select("password_encrypted").eq("username", nif).eq("tipo_servico", "AT").execute()
        
        if not res.data:
            print(f"⚠️ Erro: NIF {nif} não tem credenciais configuradas (tipo_servico='AT').")
            return jsonify({"status": "erro", "mensagem": "NIF não encontrado nas credenciais"}), 404
        
        senha = res.data[0]['password_encrypted']
        print("✅ Credenciais obtidas.")

        # 2. Abrir o Navegador
        driver = get_driver()
        wait = WebDriverWait(driver, 20)

        # 3. Fluxo de Login no Portal das Finanças
        print("A abrir página de login do Portal das Finanças...")
        driver.get("https://www.portaldasfinancas.gov.pt/main/loginForm.jsp")
        
        print("A preencher formulário...")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(nif)
        driver.find_element(By.ID, "password").send_keys(senha)
        
        print("A submeter login...")
        driver.find_element(By.ID, "sbmtLogin").click()

        # Aguardar processamento do login
        time.sleep(4)
        
        # 4. Navegar para Consulta de IUC
        print("A navegar para a página de consulta de IUC...")
        driver.get("https://sitfiscal.portaldasfinancas.gov.pt/iuc/consultar")
        time.sleep(3)

        # 5. Registar Sucesso no Supabase
        print("A atualizar registo de atividade no Supabase...")
        supabase.table("iuc_registos").insert({
            "cliente_nif": nif,
            "situacao": "Sucesso",
            "data_recolha": datetime.now().isoformat(),
            "notas": "Login efetuado com sucesso através do bot."
        }).execute()

        print(f"--- [FIM] Processo concluído com sucesso para o NIF: {nif} ---")
        return jsonify({"status": "sucesso", "nif": nif}), 200

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"❌ ERRO DURANTE A EXECUÇÃO:\n{error_details}")
        return jsonify({
            "status": "erro", 
            "mensagem": "Falha interna no processamento do bot",
            "detalhes": str(e)
        }), 500

    finally:
        if driver:
            print("A fechar navegador...")
            driver.quit()

if __name__ == '__main__':
    # O Render atribui uma porta automaticamente na variável PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

