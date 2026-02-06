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

# Configurações Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_driver():
    print("A configurar o Selenium WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # Localização do Chrome instalada pelo render-build.sh
    chrome_bin = os.path.join(os.environ.get('STORAGE_DIR', '/tmp'), 'chrome/opt/google/chrome/google-chrome')
    if os.path.exists(chrome_bin):
        print(f"Chrome binário encontrado em: {chrome_bin}")
        options.binary_location = chrome_bin
    else:
        print("Aviso: Binário do Chrome não encontrado no caminho do Render. A tentar padrão...")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

@app.route('/recolher-iuc', methods=['POST'])
def api_recolher_iuc():
    data = request.get_json()
    nif = data.get('nif')
    print(f"\n--- [INÍCIO] Processando NIF: {nif} ---")
    
    driver = None
    try:
        # 1. Buscar a senha na tabela de credenciais
        print("A procurar credenciais no Supabase...")
        res = supabase.table("clientes_credenciais").select("password_encrypted").eq("username", nif).eq("tipo_servico", "AT").execute()
        
        if not res.data:
            print(f"ERRO: NIF {nif} não encontrado na tabela clientes_credenciais.")
            return jsonify({"status": "erro", "mensagem": "NIF não encontrado nas credenciais"}), 404
        
        senha = res.data[0]['password_encrypted']
        print("Credenciais obtidas com sucesso.")

        # 2. Inicializar Navegador
        driver = get_driver()
        wait = WebDriverWait(driver, 20)

        # 3. Login no Portal das Finanças
        print("A aceder ao formulário de login das Finanças...")
        driver.get("https://www.portaldasfinancas.gov.pt/main/loginForm.jsp")
        
        print("A preencher dados de acesso...")
        wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(nif)
        driver.find_element(By.ID, "password").send_keys(senha)
        
        print("A clicar no botão de login...")
        driver.find_element(By.ID, "sbmtLogin").click()

        # 4. Verificar se o login teve sucesso (aguardar elemento da área privada)
        time.sleep(3)
        print("Login efetuado. A navegar para a página do IUC...")
        
        # 5. Navegar para a página do IUC
        driver.get("https://sitfiscal.portaldasfinancas.gov.pt/iuc/consultar")
        time.sleep(2)

        # 6. Gravar log de sucesso no Supabase
        print("A registar sucesso na tabela iuc_registos...")
        supabase.table("iuc_registos").insert({
            "cliente_nif": nif,
            "situacao": "Sucesso",
            "data_recolha": datetime.now().isoformat(),
            "notas": "Login efetuado e página de consulta alcançada."
        }).execute()

        print(f"--- [FIM] Processo concluído para o NIF: {nif} ---")
        return jsonify({"status": "sucesso", "nif": nif, "mensagem": "Recolha concluída"}), 200

    except Exception as e:
        error_msg = str(e)
        print(f"ERRO CRÍTICO: {error_msg}")
        print(traceback.format_exc()) # Imprime o erro completo nos logs do Render
        
        return jsonify({
            "status": "erro", 
            "mensagem": "Falha interna no robô",
            "detalhes": error_msg
        }), 500

    finally:
        if driver:
            print("A fechar o navegador...")
            driver.quit()

if __name__ == '__main__':
    # O Render usa a porta 10000 por defeito
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
