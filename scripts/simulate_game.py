import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from uno_logic import MoteurUno
import random
import time

def simulation_rapide():
    print("--- Démarrage de la simulation ---")
    jeu = MoteurUno()
    jeu.ajouter_joueur("Bot1", "sid_1")
    jeu.ajouter_joueur("Bot2", "sid_2")
    jeu.ajouter_joueur("Bot3", "sid_3")
    
    succes, msg = jeu.demarrer_jeu()
    print(f"Jeu démarré : {msg}")
    
    tours = 0
    max_tours = 1000 
    
    while jeu.jeu_commence and tours < max_tours:
        tours += 1
        joueur_actuel = jeu.joueurs[jeu.tour_actuel]
        sid = joueur_actuel.sid
        
        carte_jouable_index = -1
        couleur_choisie = None
        
        for index, carte in enumerate(joueur_actuel.main):
            carte_talon = jeu.talon[-1]
            if carte.est_compatible(carte_talon, jeu.couleur_choisie):
                carte_jouable_index = index

                if carte.couleur == 'Noir':
                    couleur_choisie = random.choice(['Rouge', 'Bleu', 'Vert', 'Jaune'])
                break
        

        if carte_jouable_index != -1:
            succes, msg = jeu.jouer_coup(sid, carte_jouable_index, couleur_choisie)
            if succes:
                print(f"Tour {tours}: {msg}")
                if "VICTOIRE" in msg:
                    print(f"--- FIN DE LA SIMULATION : {joueur_actuel.nom} a gagné en {tours} tours ---")
                    break
            else:
                print(f"Erreur inattendue : {msg}")
        else:

            succes, msg = jeu.action_piocher(sid)
            print(f"Tour {tours}: {joueur_actuel.nom} ne peut pas jouer et pioche.")

    if tours >= max_tours:
        print("--- Match nul (trop long) ---")

if __name__ == "__main__":
    simulation_rapide()