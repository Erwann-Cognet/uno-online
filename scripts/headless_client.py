import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import socketio
import requests
import time
import random
import sys


BASE_URL = "http://127.0.0.1:5000"
ROOM_NAME = "Headless"
GAME_SPEED = 1.0 

class HeadlessPlayer:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session() 
        self.sio = socketio.Client()
        self.hand = []
        self.game_state = {}
        self.my_turn = False
        self.is_host = False

        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('etat_jeu', self.on_game_state)
        self.sio.on('ma_main', self.on_hand_update)
        self.sio.on('info', self.on_info)
        self.sio.on('erreur', self.on_error)

    def log(self, msg):
        print(f"[{self.username}] {msg}")


    def register_and_login(self):
        # 1. Inscription
        reg_data = {"username": self.username, "password": self.password}
        try:
            self.session.post(f"{BASE_URL}/api/register", json=reg_data)

        except Exception as e:
            self.log(f"Erreur API: {e}")


        res = self.session.post(f"{BASE_URL}/api/login", json=reg_data)
        if res.status_code == 200 and res.json().get("success"):
            self.log("Connecté (HTTP)")
            return True
        else:
            self.log(f"Echec Login: {res.text}")
            return False

    def connect_socket(self):

        cookies = self.session.cookies.get_dict()
        headers = {'Cookie': "; ".join([f"{k}={v}" for k, v in cookies.items()])}
        
        try:
            self.sio.connect(BASE_URL, headers=headers)
        except Exception as e:
            self.log(f"Erreur connexion Socket: {e}")

    def on_connect(self):
        self.log("Socket Connecté 🔌")
        self.sio.emit('rejoindre', {'room': ROOM_NAME, 'password': ''})

    def on_disconnect(self):
        self.log("Déconnecté ❌")

    def on_info(self, data):
        self.log(f"INFO: {data['message']}")

    def on_error(self, data):
        self.log(f"ERREUR: {data['message']}")

    def on_hand_update(self, data):
        self.hand = data['cartes']

    def on_game_state(self, state):
        self.game_state = state
        
        joueurs = state['joueurs']
        idx_tour = state['tour_index']
        
        if not state['en_cours']:
            if self.is_host and len(joueurs) >= 2:
                self.log("Je lance la partie ! 🚀")
                time.sleep(1)
                self.sio.emit('demarrer', {'regles': {'stack_plus2': True, 'stack_plus4': True}})
            return

        if "VICTOIRE" in state['message']:
            self.log(f"Fin de partie détectée : {state['message']}")
            sys.exit(0) 


        mon_nom = self.username
        nom_actuel = joueurs[idx_tour]['nom']
        
        if nom_actuel == mon_nom:
            self.log(" C'EST MON TOUR !")
            time.sleep(GAME_SPEED) 
            self.play_turn(state)

    def play_turn(self, state):
        """Logique simple (similaire aux bots)"""
        if state.get('attente_challenge'):
            self.log("Je subis le challenge (je pioche)")
            self.sio.emit('piocher')
            return

        talon = state['talon']
        couleur_active = state['couleur_active']
        
        carte_jouable_idx = -1
        couleur_a_jouer = None

        for i, carte in enumerate(self.hand):
            compatible = False
            if couleur_active:
                if carte['couleur'] == couleur_active or carte['couleur'] == 'Noir': compatible = True
            else:
                if carte['couleur'] == 'Noir': compatible = True
                elif carte['couleur'] == talon['couleur']: compatible = True
                elif carte['valeur'] == talon['valeur']: compatible = True
            
            if compatible:
                carte_jouable_idx = i
                if carte['couleur'] == 'Noir':
                    couleur_a_jouer = random.choice(['Rouge', 'Bleu', 'Vert', 'Jaune'])
                break
        
        if carte_jouable_idx != -1:
            c = self.hand[carte_jouable_idx]
            self.log(f"Je joue {c['valeur']} {c['couleur']}")
            self.sio.emit('jouer_carte', {'index': carte_jouable_idx, 'couleur': couleur_a_jouer})
            
            if len(self.hand) == 2:
                self.sio.emit('annoncer_uno')
        else:
            self.log("Je ne peux pas jouer, je pioche.")
            self.sio.emit('piocher')



def run_headless_simulation():
    print("--- Démarrage de la simulation Headless ---")
    
    bots = []
    for i in range(1, 4): 
        p = HeadlessPlayer(f"Tester_{i}", f"local-test-{i}")
        if i == 1: p.is_host = True # 
        bots.append(p)

    for bot in bots:
        if bot.register_and_login():
            bot.connect_socket()
            time.sleep(0.5) 

    print(f"--- 3 Joueurs connectés dans {ROOM_NAME} ---")
    print("--- Observez les logs pour détecter les bugs ---")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Arrêt de la simulation.")
        for bot in bots:
            bot.sio.disconnect()

if __name__ == "__main__":
    run_headless_simulation()