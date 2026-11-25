import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app, db, User

def make_admin(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"{username} est maintenant administrateur !")
        else:
            print(f"Utilisateur '{username}' introuvable.")

if __name__ == "__main__":
    pseudo = input("Entrez le pseudo à promouvoir Admin : ")
    make_admin(pseudo)