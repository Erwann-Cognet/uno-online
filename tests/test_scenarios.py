import unittest
from uno_logic import MoteurUno, Carte

class TestScenarioUno(unittest.TestCase):
    def setUp(self):
        """Initialisation propre avant chaque scénario"""
        self.jeu = MoteurUno()
        self.jeu.ajouter_joueur("Alice", "id_alice")
        self.jeu.ajouter_joueur("Bob", "id_bob")
        self.jeu.demarrer_jeu()

    def test_scenario_victoire_directe(self):
        """
        SCÉNARIO 1 : Victoire en un coup.
        Situation : Alice n'a plus qu'une carte, compatible avec le talon.
        Attendu : Elle la joue, la partie s'arrête, message de victoire.
        """
        print("\n--- Test Scénario : Victoire Directe ---")
        
        self.jeu.talon = [Carte('Rouge', '5')]            
        self.jeu.joueurs[0].main = [Carte('Rouge', '9')] 
        self.jeu.joueurs[1].main = [Carte('Bleu', '1')]   
        
        self.jeu.tour_actuel = 0
        
        succes, msg = self.jeu.jouer_coup("id_alice", 0)

        self.assertTrue(succes, "Le coup devrait être accepté")
        self.assertEqual(len(self.jeu.joueurs[0].main), 0, "Alice ne doit plus avoir de cartes")
        self.assertFalse(self.jeu.jeu_commence, "La partie doit être marquée comme finie")
        self.assertIn("VICTOIRE", msg, "Le message doit annoncer la victoire")
        print("Alice a gagné correctement.")

    def test_scenario_attaque_plus_2(self):
        """
        SCÉNARIO 2 : Enchaînement d'effets.
        Situation : Alice joue un +2.
        Attendu : Bob pioche 2 cartes, passe son tour, et c'est de nouveau à Alice.
        """
        print("\n--- Test Scénario : Attaque +2 ---")

        self.jeu.talon = [Carte('Jaune', '3')]
        
        c_plus2 = Carte('Jaune', '+2')
        c_huit = Carte('Jaune', '8')
        self.jeu.joueurs[0].main = [c_plus2, c_huit]
        
        self.jeu.joueurs[1].main = [Carte('Bleu', '1')]
        
        self.jeu.pioche = [Carte('Vert', '0'), Carte('Vert', '0'), Carte('Vert', '0')]
        
        self.jeu.tour_actuel = 0 

        succes, msg = self.jeu.jouer_coup("id_alice", 0)
        self.assertTrue(succes)
        print("-> Alice a joué +2.")

        nb_cartes_bob = len(self.jeu.joueurs[1].main)
        self.assertEqual(nb_cartes_bob, 3, f"Bob devrait avoir 3 cartes, il en a {nb_cartes_bob}")
        
        nom_joueur_actuel = self.jeu.joueurs[self.jeu.tour_actuel].nom
        self.assertEqual(nom_joueur_actuel, "Alice", f"C'est à {nom_joueur_actuel} de jouer, ça devrait être Alice")
        print(" Effet +2 validé : Bob a pioché et passé son tour.")

        succes, msg = self.jeu.jouer_coup("id_alice", 0)
        self.assertIn("VICTOIRE", msg)
        print(" Alice a rejoué et gagné.")

if __name__ == '__main__':
    unittest.main()