import requests
import re
import time
from threading import Thread, Lock
from queue import Queue
from datetime import datetime
from flask import Flask, request, jsonify

class CTFSubmitter:
    def __init__(self):
        # Configurazione (DA MODIFICARE DOMANI)
        self.SERVER_URL = "http://10.10.0.1:8080/flags"  # Endpoint ufficiale
        self.TEAM_TOKEN = "d98453257da6f0b806c894b0802d3983"            # Sostituire con token reale
        self.FLAG_REGEX = re.compile(r"^[A-Z0-9]{31}=$")  # Regex ufficiale
        
        # Strutture dati thread-safe
        self.flag_queue = Queue()
        self.lock = Lock()
        self.last_submission = 0
        self.rate_limit = 30  # Max 30 richieste/minuto

        # Avvia thread
        Thread(target=self.submitter_thread, daemon=True).start()
        Thread(target=self.start_http_server, daemon=True).start()

    def decode_flag(self, flag):
        """Decodifica le informazioni della flag"""
        try:
            return {
                'round': int(flag[0:2], 36),
                'team': int(flag[2:4], 36),
                'service': int(flag[4:6], 36),
                'full_flag': flag
            }
        except:
            return None

    def validate_flag(self, flag):
        """Verifica il formato e la validità temporale"""
        if not self.FLAG_REGEX.match(flag):
            return False, "Formato non valido"
        
        decoded = self.decode_flag(flag)
        if not decoded:
            return False, "Decodifica fallita"
        
        # Qui aggiungere controllo round se necessario
        return True, "Valida"

    def submit_flags(self, flags):
        """Invia un batch di flag al server"""
        if not flags:
            return []

        try:
            response = requests.put(
                self.SERVER_URL,
                headers={'X-Team-Token': self.TEAM_TOKEN},
                json=flags,
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Errore HTTP {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            print(f"Errore connessione: {str(e)}")
            return []

    def submitter_thread(self):
        """Thread per l'invio rate-limited"""
        while True:
            now = time.time()
            elapsed = now - self.last_submission
            
            # Rispetta il rate limiting (30/minuto)
            if elapsed < 2.0:  # 60/30 = 2s tra le richieste
                time.sleep(2.0 - elapsed)
            
            # Raccoglie fino a 100 flag per richiesta (entro 100KB)
            batch = []
            while len(batch) < 100 and not self.flag_queue.empty():
                flag = self.flag_queue.get()
                batch.append(flag)
            
            if batch:
                results = self.submit_flags(batch)
                self.last_submission = time.time()
                
                with self.lock:
                    for result in results:
                        status = result.get('status', 'ERROR')
                        msg = result.get('msg', 'Nessun messaggio')
                        print(f"[{status}] {msg}")

    def start_http_server(self):
        """Avvia il server HTTP per ricevere flag"""
        app = Flask(__name__)
        
        @app.route('/submit', methods=['POST'])
        def http_add_flag():
            flag = request.form.get('flag', '').strip()
            valid, msg = self.validate_flag(flag)
            if valid:
                with self.lock:
                    self.flag_queue.put(flag)
                return jsonify({"status": "OK", "flag": flag[:6] + "..."})
            return jsonify({"status": "ERROR", "message": msg}), 400

        @app.route('/queue', methods=['GET'])
        def get_queue():
            with self.lock:
                size = self.flag_queue.qsize()
            return jsonify({"queue_size": size})

        print(f"\n[+] Server HTTP in ascolto su http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, threaded=True)

    def add_flag(self, flag):
        """Aggiungi una flag manualmente"""
        valid, msg = self.validate_flag(flag)
        if valid:
            with self.lock:
                self.flag_queue.put(flag)
                print(f"[+] Flag accettata: {flag[:6]}... (Team {self.decode_flag(flag)['team']})")
            return True
        else:
            print(f"[-] Flag rifiutata: {msg}")
            return False

    def start_cli(self):
        """Interfaccia a riga di comando"""
        print(f"""
        === CTF Flag Submitter ===
        Server: {self.SERVER_URL}
        Token: {self.TEAM_TOKEN[:4]}...{self.TEAM_TOKEN[-4:]}
        HTTP Endpoint: http://localhost:5000/submit
        ----------------------------
        Comandi:
        - 'submit FLAG' per aggiungere flag
        - 'status' per vedere la coda
        - 'exit' per uscire
        """)
        
        while True:
            try:
                cmd = input("> ").strip()
                if cmd.lower() == 'exit':
                    break
                elif cmd.lower() == 'status':
                    print(f"Flag in coda: {self.flag_queue.qsize()}")
                elif cmd.startswith('submit '):
                    flag = cmd[7:].strip()
                    self.add_flag(flag)
                else:
                    print("Comando non riconosciuto")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Errore: {str(e)}")

if __name__ == "__main__":
    submitter = CTFSubmitter()
    submitter.start_cli()   