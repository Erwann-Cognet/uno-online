import random

COULEURS = ['Rouge', 'Jaune', 'Vert', 'Bleu']
VALEURS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '+2', 'Inversion', 'Passer']
VALEURS_WILD = ['Joker', '+4']

class Carte:
    def __init__(self, couleur, valeur):
        self.couleur = couleur
        self.valeur = valeur
        self.id = f"{valeur}_{couleur}_{random.randint(10000, 99999)}"

    def __repr__(self): return f"{self.valeur} {self.couleur}"
    def to_dict(self): return {"couleur": self.couleur, "valeur": self.valeur, "id": self.id}

    def est_compatible(self, carte_talon, couleur_choisie):
        if couleur_choisie: return self.couleur == couleur_choisie or self.couleur == 'Noir'
        return self.couleur == 'Noir' or self.couleur == carte_talon.couleur or self.valeur == carte_talon.valeur
               
    def est_strictement_identique(self, carte_talon):
        return self.couleur == carte_talon.couleur and self.valeur == carte_talon.valeur

class Joueur:
    def __init__(self, nom, sid, est_bot=False):
        self.nom = nom
        self.sid = sid
        self.est_bot = est_bot
        self.main = []
        self.a_dit_uno = False
        self.est_vulnerable_uno = False

    def to_dict(self):
        return {
            "nom": self.nom,
            "nb_cartes": len(self.main),
            "sid": self.sid,
            "a_dit_uno": self.a_dit_uno,
            "est_bot": self.est_bot
        }

    def piocher(self, carte):
        self.main.append(carte)
        self.trier_main()
        self.a_dit_uno = False 
        self.est_vulnerable_uno = False

    def jouer_carte(self, index):
        return self.main.pop(index)
    
    def trier_main(self):
        ordre_c = {'Rouge': 1, 'Vert': 2, 'Bleu': 3, 'Jaune': 4, 'Noir': 5}
        def val_score(v):
            if v.isdigit(): return int(v)
            if v == '+2': return 10; 
            if v == 'Inversion': return 11; 
            if v == 'Passer': return 12; 
            if v == 'Joker': return 13; 
            if v == '+4': return 14; 
            return 0
        self.main.sort(key=lambda x: (ordre_c[x.couleur], val_score(x.valeur)))

def creer_paquet():
    paquet = []
    for couleur in COULEURS:
        paquet.append(Carte(couleur, '0'))
        for _ in range(2):
            for valeur in VALEURS[1:]:
                paquet.append(Carte(couleur, valeur))
    for _ in range(4):
        paquet.append(Carte('Noir', VALEURS_WILD[0]))
        paquet.append(Carte('Noir', VALEURS_WILD[1]))
    return paquet

class MoteurUno:
    def __init__(self):
        self.joueurs = []
        self.spectateurs = []
        self.pioche = []
        self.talon = []
        self.tour_actuel = 0
        self.sens_jeu = 1
        self.couleur_choisie = None
        self.jeu_commence = False
        self.dernier_message = "En attente..."
        self.regles = { "stack_plus2": False, "stack_plus4": False, "jump_in": False }
        self.cumul_peine = 0
        self.attente_challenge = False
        self.joueur_plus4_sid = None 
        self.contexte_avant_plus4 = None 

    def ajouter_joueur(self, nom, sid):
        for j in self.joueurs + self.spectateurs:
            if j.nom == nom: return False, "Pseudo pris."
        
        if self.jeu_commence:
            self.spectateurs.append(Joueur(nom, sid))
            return True, "Spectateur"
        
        if len(self.joueurs) >= 10:
            return False, "Salle pleine (10 max)."

        self.joueurs.append(Joueur(nom, sid))
        return True, "OK"
    
    def ajouter_bot(self):
        if self.jeu_commence: return False, "Impossible en jeu."
        if len(self.joueurs) >= 10: return False, "Salle pleine."
        idx = len([j for j in self.joueurs if j.est_bot]) + 1
        self.joueurs.append(Joueur(f"Bot {idx}", f"bot_{random.randint(10000,99999)}", True))
        return True, "Bot ajouté"

    def retirer_dernier_bot(self):
        if self.jeu_commence: return False, "Impossible en jeu."
        bots = [j for j in self.joueurs if j.est_bot]
        if not bots: return False, "Aucun bot."
        self.joueurs.remove(bots[-1])
        return True, "Bot retiré"

    def retirer_joueur(self, sid):
        self.joueurs = [j for j in self.joueurs if j.sid != sid]
        self.spectateurs = [j for j in self.spectateurs if j.sid != sid]
        return True

    def demarrer_jeu(self, regles_custom={}):
        self.joueurs.extend(self.spectateurs)
        self.spectateurs = []

        if len(self.joueurs) < 2: return False, "Pas assez de joueurs."
        
        self.regles.update(regles_custom)
        self.jeu_commence = True
        self.pioche = creer_paquet()
        random.shuffle(self.pioche)
        self.talon = []
        self.couleur_choisie = None
        self.cumul_peine = 0
        self.sens_jeu = 1
        self.attente_challenge = False
        
        for j in self.joueurs:
            j.main = []
            j.a_dit_uno = False
            j.est_vulnerable_uno = False
            for _ in range(7): self.piocher_pour_joueur(j)
                
        while True:
            c = self.pioche.pop()
            self.talon.append(c)
            if c.couleur != 'Noir' and c.valeur not in ['+2', 'Inversion', 'Passer']: break
            else: self.pioche.insert(0, c)
        
        self.tour_actuel = 0
        self.dernier_message = "C'est parti !"
        return True, "OK"

    def piocher_pour_joueur(self, joueur, nb=1):
        for _ in range(nb):
            if not self.pioche:
                if len(self.talon) > 1:
                    top = self.talon.pop()
                    self.pioche = self.talon
                    self.talon = [top]
                    random.shuffle(self.pioche)
                else: break
            if self.pioche: joueur.piocher(self.pioche.pop())

    def passer_au_joueur_suivant(self):
        self.tour_actuel = (self.tour_actuel + self.sens_jeu) % len(self.joueurs)

    def trouver_joueur_par_sid(self, sid):
        for i, j in enumerate(self.joueurs):
            if j.sid == sid: return i, j
        return -1, None

    def calculer_coup_bot(self):
        joueur = self.joueurs[self.tour_actuel]
        if not joueur.est_bot: return None
        if self.attente_challenge: return {"action": "piocher"}

        carte_talon = self.talon[-1]
        
        if self.cumul_peine > 0:
            for i, c in enumerate(joueur.main):
                can_stack = False
                if self.regles["stack_plus2"] and c.valeur == '+2' and carte_talon.valeur == '+2': can_stack = True
                if self.regles["stack_plus4"] and c.valeur == '+4': can_stack = True
                if can_stack: return {"action": "jouer", "index": i, "couleur": None}
            return {"action": "piocher"}

        for i, c in enumerate(joueur.main):
            if c.est_compatible(carte_talon, self.couleur_choisie):
                couleur = None
                if c.couleur == 'Noir':
                    counts = {'Rouge':0, 'Bleu':0, 'Vert':0, 'Jaune':0}
                    for cards in joueur.main:
                        if cards.couleur != 'Noir': counts[cards.couleur] += 1
                    couleur = max(counts, key=counts.get)
                return {"action": "jouer", "index": i, "couleur": couleur}
        return {"action": "piocher"}

    def action_annoncer_uno(self, sid):
        _, joueur = self.trouver_joueur_par_sid(sid)
        if not joueur: return False, "Introuvable"
        if len(joueur.main) <= 2:
            joueur.a_dit_uno = True
            joueur.est_vulnerable_uno = False
            return True, f"{joueur.nom} crie UNO !"
        else:
            self.piocher_pour_joueur(joueur, 2)
            return True, f"{joueur.nom} ment (+2 cartes)"

    def action_contre_uno(self, sid_accusateur):
        if not self.jeu_commence: return False, ""
        for j in self.joueurs:
            if len(j.main) == 1 and not j.a_dit_uno:
                self.piocher_pour_joueur(j, 2)
                j.est_vulnerable_uno = False
                j.a_dit_uno = False
                return True, f"CONTRE-UNO ! {j.nom} prend +2 !"
        return False, "Personne n'a oublié."

    def action_contester_plus4(self, sid_accusateur):
        if not self.attente_challenge: return False, ""
        idx_acc, accusateur = self.trouver_joueur_par_sid(sid_accusateur)
        _, coupable = self.trouver_joueur_par_sid(self.joueur_plus4_sid)
        if idx_acc != self.tour_actuel: return False, "Pas votre tour."

        a_menti = False
        prev_c = self.contexte_avant_plus4
        sur_plus2 = (isinstance(prev_c, Carte) and prev_c.valeur == '+2') or (isinstance(prev_c, str) and prev_c == '+2')
        
        for c in coupable.main:
            if sur_plus2:
                if c.valeur == '+2': a_menti = True; break
            else:
                couleur_ref = self.contexte_avant_plus4 if isinstance(self.contexte_avant_plus4, str) else self.contexte_avant_plus4.couleur
                if c.couleur == couleur_ref: a_menti = True; break

        self.attente_challenge = False
        self.cumul_peine = 0
        
        if a_menti:
            self.piocher_pour_joueur(coupable, 4)
            return True, f"MENTEUR ! {coupable.nom} prend 4 cartes !"
        else:
            self.piocher_pour_joueur(accusateur, 6) 
            self.passer_au_joueur_suivant()
            return True, f"ÉCHEC ! {accusateur.nom} prend 6 cartes !"

    def jouer_coup(self, sid_joueur, index_carte, couleur_choisie=None):
        idx_j, joueur = self.trouver_joueur_par_sid(sid_joueur)
        if not joueur: return False, "Erreur"
        if self.attente_challenge: return False, "Challenge en cours."

        carte = joueur.main[index_carte]
        carte_talon = self.talon[-1]
        est_mon_tour = (idx_j == self.tour_actuel)
        est_jump_in = False

        if not est_mon_tour:
            if self.regles["jump_in"] and carte.est_strictement_identique(carte_talon):
                est_jump_in = True
                self.tour_actuel = idx_j
                self.cumul_peine = 0 
            else: return False, "Pas votre tour."

        if self.cumul_peine > 0:
            autorise = False
            if self.regles["stack_plus2"] and carte.valeur == '+2' and carte_talon.valeur == '+2': autorise = True
            elif self.regles["stack_plus4"] and carte.valeur == '+4': autorise = True
            if not autorise: return False, "Contrez ou piochez !"

        if not est_jump_in and not carte.est_compatible(carte_talon, self.couleur_choisie): return False, "Incompatible."
        if carte.couleur == 'Noir' and couleur_choisie is None: return False, "Couleur requise."

        joueur.jouer_carte(index_carte)
        if carte.valeur == '+4':
            self.joueur_plus4_sid = joueur.sid
            self.contexte_avant_plus4 = self.couleur_choisie if self.couleur_choisie else carte_talon

        self.talon.append(carte)
        if self.couleur_choisie and carte.couleur != 'Noir': self.couleur_choisie = None

        msg = f"{joueur.nom} joue {carte}"
        if est_jump_in: msg += " (JUMP-IN !)"

        if len(joueur.main) == 1:
            if joueur.est_bot: joueur.a_dit_uno = True
            elif not joueur.a_dit_uno: joueur.est_vulnerable_uno = True
        else:
            joueur.est_vulnerable_uno = False
            joueur.a_dit_uno = False

        if len(joueur.main) == 0:
            self.jeu_commence = False
            self.dernier_message = f"VICTOIRE ! {joueur.nom} gagne !"
            return True, "VICTOIRE"

        self.gerer_effets_apres_coup(carte, couleur_choisie)
        
        self.dernier_message = f"{msg}. Tour de {self.joueurs[self.tour_actuel].nom}."
        if self.attente_challenge: self.dernier_message += " (Challenge ?)"
        elif self.cumul_peine > 0: self.dernier_message += f" (Doit prendre +{self.cumul_peine})"

        return True, "OK"

    def gerer_effets_apres_coup(self, carte, couleur_choisie):
        val = carte.valeur
        if val == 'Inversion':
            self.sens_jeu *= -1
            if len(self.joueurs) == 2: self.passer_au_joueur_suivant()
        elif val == 'Passer': self.passer_au_joueur_suivant()
        elif val in ['Joker', '+4']: self.couleur_choisie = couleur_choisie
        
        if val == '+2': self.cumul_peine += 2
        elif val == '+4': self.cumul_peine += 4

        self.passer_au_joueur_suivant()
        
        if val == '+4':
            self.attente_challenge = True
            return

        apply_now = False
        # A +2 can be answered by a +2 (stack_plus2) or by a +4 (stack_plus4): only apply it right away if neither rule is on.
        if val == '+2' and not (self.regles["stack_plus2"] or self.regles["stack_plus4"]): apply_now = True
        
        if apply_now:
            self.piocher_pour_joueur(self.joueurs[self.tour_actuel], self.cumul_peine)
            self.cumul_peine = 0
            self.passer_au_joueur_suivant()

    def action_piocher(self, sid):
        idx, joueur = self.trouver_joueur_par_sid(sid)
        if idx != self.tour_actuel: return False, "Pas votre tour."

        if self.attente_challenge:
            self.attente_challenge = False
            self.piocher_pour_joueur(joueur, self.cumul_peine)
            self.cumul_peine = 0
            self.passer_au_joueur_suivant()
            self.dernier_message = f"{joueur.nom} accepte le +4."
            return True, "Accepté"

        if self.cumul_peine > 0:
            self.piocher_pour_joueur(joueur, self.cumul_peine)
            self.cumul_peine = 0
            self.passer_au_joueur_suivant()
            self.dernier_message = f"{joueur.nom} prend la peine."
            return True, "Peine subie"
        
        self.piocher_pour_joueur(joueur, 1)
        self.passer_au_joueur_suivant()
        self.dernier_message = f"{joueur.nom} pioche."
        return True, "Pioché"

    def get_etat_complet(self):
        return {
            "en_cours": self.jeu_commence,
            "joueurs": [j.to_dict() for j in self.joueurs],
            "spectateurs": [s.to_dict() for s in self.spectateurs], 
            "talon": self.talon[-1].to_dict() if self.talon else None,
            "couleur_active": self.couleur_choisie,
            "tour_index": self.tour_actuel,
            "message": self.dernier_message,
            "sens": self.sens_jeu,
            "cumul_peine": self.cumul_peine,
            "attente_challenge": self.attente_challenge
        }
    
    def get_main_joueur(self, sid):
        _, j = self.trouver_joueur_par_sid(sid)
        if j:
            j.trier_main()
            return [c.to_dict() for c in j.main]
        return []