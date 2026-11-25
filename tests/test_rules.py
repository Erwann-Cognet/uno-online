import unittest
from uno_logic import MoteurUno, Carte, Joueur

class TestUnoNewRules(unittest.TestCase):

    def setUp(self):
        """Initialisation avant chaque test"""
        self.jeu = MoteurUno()
        self.jeu.ajouter_joueur("Alice", "id_alice")
        self.jeu.ajouter_joueur("Bob", "id_bob")
        self.jeu.ajouter_joueur("Charlie", "id_charlie")
        self.jeu.demarrer_jeu() 

    def test_tri_main(self):
        """Vérifie que la main du joueur est bien triée par couleur puis valeur."""
        joueur = self.jeu.joueurs[0]
        joueur.main = [
            Carte('Bleu', '9'),
            Carte('Rouge', '1'),
            Carte('Noir', '+4'),
            Carte('Vert', '5'),
            Carte('Bleu', '0')
        ]
        
        joueur.trier_main()
        
        self.assertEqual(joueur.main[0].couleur, 'Rouge')
        self.assertEqual(joueur.main[1].couleur, 'Vert')
        self.assertEqual(joueur.main[2].couleur, 'Bleu')
        self.assertEqual(joueur.main[2].valeur, '0') 
        self.assertEqual(joueur.main[4].couleur, 'Noir')
        print("Test Tri : OK")

    def test_stack_plus4_sur_plus2(self):
        """Vérifie qu'on peut poser un +4 sur un +2 si la règle est active."""
        self.jeu.regles["stack_plus4"] = True
        
        alice = self.jeu.joueurs[0] 
        bob = self.jeu.joueurs[1]   
        charlie = self.jeu.joueurs[2] 
        
        self.jeu.talon = [Carte('Rouge', '5')]
        alice.main = [Carte('Rouge', '+2'), Carte('Bleu', '7')]
        
        ok, msg = self.jeu.jouer_coup(alice.sid, 0)
        self.assertTrue(ok)
        
        self.assertEqual(self.jeu.tour_actuel, 1)
        self.assertEqual(self.jeu.cumul_peine, 2)
        
        bob.main = [Carte('Noir', '+4'), Carte('Vert', '3')]
        
        ok, msg = self.jeu.jouer_coup(bob.sid, 0, 'Bleu')
        
        self.assertTrue(ok, f"Le +4 sur +2 devrait être accepté. Msg: {msg}")
        
        self.assertTrue(self.jeu.attente_challenge)
        self.assertEqual(self.jeu.cumul_peine, 6)
        print("Test Stack +4 sur +2 : OK")

    def test_bluff_plus4_succes_accusateur(self):
        """Alice bluffe (elle a la couleur demandée) et Bob la démasque."""
        alice = self.jeu.joueurs[0]
        bob = self.jeu.joueurs[1]
        
        self.jeu.talon = [Carte('Rouge', '5')]
        self.jeu.contexte_avant_plus4 = Carte('Rouge', '5') 
        
        alice.main = [Carte('Rouge', '9'), Carte('Noir', '+4')]
        
        self.jeu.jouer_coup(alice.sid, 1, 'Bleu')
        
        self.assertTrue(self.jeu.attente_challenge)
        self.assertEqual(self.jeu.joueur_plus4_sid, alice.sid)
        
        nb_cartes_alice_avant = len(alice.main)
        
        ok, msg = self.jeu.action_contester_plus4(bob.sid)
        
        self.assertTrue(ok)
        self.assertIn("MENTEUR", msg)
        
        self.assertEqual(len(alice.main), nb_cartes_alice_avant + 4)
        
        self.assertEqual(self.jeu.cumul_peine, 0)
        print("Test Bluff Démasqué : OK")

    def test_bluff_echec_accusateur(self):
        """Alice joue un +4 légitime (pas de couleur). Bob conteste à tort."""
        alice = self.jeu.joueurs[0]
        bob = self.jeu.joueurs[1]
        
        self.jeu.talon = [Carte('Rouge', '5')]
        self.jeu.contexte_avant_plus4 = Carte('Rouge', '5')
        
        alice.main = [Carte('Bleu', '9'), Carte('Noir', '+4')]        
        self.jeu.jouer_coup(alice.sid, 1, 'Vert')
        
        nb_cartes_bob_avant = len(bob.main)
        ok, msg = self.jeu.action_contester_plus4(bob.sid)
        
        self.assertTrue(ok)
        self.assertIn("ÉCHEC", msg)
        
        self.assertEqual(len(bob.main), nb_cartes_bob_avant + 6)
        
        self.assertEqual(len(alice.main), 1)
        print("Test Accusation Ratée : OK")

if __name__ == '__main__':
    unittest.main()