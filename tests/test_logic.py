import unittest
from uno_logic import MoteurUno, Carte, Joueur

class TestUnoLogic(unittest.TestCase):

    def setUp(self):
        """Cette fonction s'exécute avant chaque test."""
        self.jeu = MoteurUno()
        self.jeu.ajouter_joueur("Alice", "sid_1")
        self.jeu.ajouter_joueur("Bob", "sid_2")

    def test_compatibilite_cartes(self):
        """Teste si les cartes peuvent être posées les unes sur les autres."""
        rouge_5 = Carte('Rouge', '5')
        rouge_8 = Carte('Rouge', '8')
        bleu_5 = Carte('Bleu', '5')
        vert_2 = Carte('Vert', '2')
        joker = Carte('Noir', 'Joker')

        self.assertTrue(rouge_8.est_compatible(rouge_5, None))
        self.assertTrue(bleu_5.est_compatible(rouge_5, None))
        self.assertFalse(vert_2.est_compatible(rouge_5, None))
        self.assertTrue(joker.est_compatible(vert_2, None))

    def test_demarrage_jeu(self):
        """Vérifie que le jeu distribue bien les cartes."""
        self.jeu.demarrer_jeu()
        
        self.assertTrue(len(self.jeu.talon) > 0)
        self.assertEqual(len(self.jeu.joueurs[0].main), 7)
        self.assertEqual(len(self.jeu.joueurs[1].main), 7)

    def test_jouer_carte_valide(self):
        """Simule un coup valide."""
        self.jeu.demarrer_jeu()
        
        joueur_actuel = self.jeu.joueurs[self.jeu.tour_actuel]
        sid_actuel = joueur_actuel.sid
        
        self.jeu.talon = [Carte('Rouge', '5')]
        carte_a_jouer = Carte('Rouge', '8')
        joueur_actuel.main = [carte_a_jouer] 

        succes, msg = self.jeu.jouer_coup(sid_actuel, 0)

        self.assertTrue(succes, f"Le coup aurait dû être valide. Erreur renvoyée : {msg}")
        self.assertEqual(len(joueur_actuel.main), 0, "Le joueur ne devrait plus avoir de cartes")
        self.assertEqual(self.jeu.talon[-1].valeur, '8', "La carte sur le talon devrait être le 8")

    def test_mauvais_tour(self):
        """Vérifie qu'Alice ne peut pas jouer si c'est au tour de Bob."""
        self.jeu.demarrer_jeu()
        sid_qui_ne_joue_pas = self.jeu.joueurs[1].sid if self.jeu.tour_actuel == 0 else self.jeu.joueurs[0].sid
        
        succes, msg = self.jeu.jouer_coup(sid_qui_ne_joue_pas, 0)
        self.assertFalse(succes)
        self.assertIn("pas votre tour", msg.lower())

    def test_effet_plus_2(self):
        """Vérifie que le +2 donne bien 2 cartes à l'adversaire."""
        self.jeu.demarrer_jeu()
        
        joueur_1 = self.jeu.joueurs[0]
        joueur_2 = self.jeu.joueurs[1]
        
    
        self.jeu.tour_actuel = 0
        self.jeu.talon = [Carte('Rouge', '5')]
        joueur_1.main = [Carte('Rouge', '+2'), Carte('Bleu', '7')]
        
        succes, msg = self.jeu.jouer_coup(joueur_1.sid, 0)
        
        self.assertTrue(succes, f"Le +2 a été refusé par le moteur : {msg}")
        
        self.assertEqual(len(joueur_2.main), 9, f"Joueur 2 a {len(joueur_2.main)} cartes au lieu de 9")
        
        self.assertEqual(self.jeu.tour_actuel, 0, "Le tour n'est pas revenu au Joueur 1 après le saut de tour")

if __name__ == '__main__':
    unittest.main()