import os
from functools import wraps
from flask import Flask, request, jsonify, session, abort
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect, close_room
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, GameHistory
from uno_logic import MoteurUno

app = Flask(__name__, static_folder="static", static_url_path="")
# Set SECRET_KEY in the environment for any real deployment.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-me')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'uno.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
socketio = SocketIO(app, cors_allowed_origins=os.environ.get("CORS_ORIGINS", "*"), manage_session=False)


games = {} 
player_rooms = {}

@login_manager.user_loader
def load_user(user_id): return User.query.get(int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({"success": False, "message": "Accès refusé. Admin requis."}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index(): return app.send_static_file("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first(): return jsonify({"success": False, "message": "Pris"})
    u = User(username=data['username'], password_hash=generate_password_hash(data['password']))
    db.session.add(u); db.session.commit()
    return jsonify({"success": True})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    u = User.query.filter_by(username=data['username']).first()
    if u and check_password_hash(u.password_hash, data['password']):
        login_user(u); return jsonify({"success": True, "user": u.to_dict()})
    return jsonify({"success": False, "message": "Erreur"})

@app.route("/api/logout", methods=["POST"])
@login_required
def logout(): logout_user(); return jsonify({"success": True})

@app.route("/api/me")
def me():
    if current_user.is_authenticated: return jsonify({"authenticated": True, "user": current_user.to_dict()})
    return jsonify({"authenticated": False})

@app.route("/api/delete_account", methods=["DELETE"])
@login_required
def delete_account():
    db.session.delete(current_user); db.session.commit(); logout_user()
    return jsonify({"success": True, "message": "Compte supprimé."})


@app.route("/api/rooms", methods=["GET"])
def list_rooms():
    public_rooms = []
    for rid, info in games.items():
        if info["public"]:
            engine = info["engine"]
            count = len(engine.joueurs) + len(engine.spectateurs)
            status = "En jeu" if engine.jeu_commence else "En attente"
            public_rooms.append({"name": rid, "count": count, "status": status})
    return jsonify(public_rooms)



@app.route("/api/admin/games", methods=["GET"])
@admin_required
def admin_list_games():
    """Liste toutes les parties en cours."""
    liste = []
    for room_name, info in games.items():
        jeu = info["engine"]
        joueurs_noms = [j.nom for j in jeu.joueurs]
        liste.append({
            "room": room_name,
            "players": joueurs_noms,
            "started": jeu.jeu_commence,
            "turn": jeu.tour_actuel
        })
    return jsonify(liste)

@app.route("/api/admin/users", methods=["GET"])
@admin_required
def admin_list_users():
    """Liste tous les utilisateurs."""
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@app.route("/api/admin/rooms/<room_id>", methods=["DELETE"])
@admin_required
def admin_delete_room(room_id):
    """Supprime une salle."""
    if room_id in games:
        socketio.emit("erreur", {"message": "Salle fermée par l'admin."}, to=room_id)
        jeu = games[room_id]["engine"]
        for j in jeu.joueurs:
            if j.sid in player_rooms: del player_rooms[j.sid]
        del games[room_id]
        close_room(room_id)
        return jsonify({"success": True, "message": f"Salle {room_id} supprimée."})
    return jsonify({"success": False, "message": "Salle introuvable."})

@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
@admin_required
def admin_delete_user(user_id):
    """Supprime un utilisateur."""
    u = User.query.get(user_id)
    if not u: return jsonify({"success": False, "message": "Introuvable."})
    if u.id == current_user.id: return jsonify({"success": False, "message": "Suicide interdit ici."})
    db.session.delete(u)
    db.session.commit()
    return jsonify({"success": True, "message": f"Utilisateur {u.username} supprimé."})


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    return jsonify([u.to_dict() for u in User.query.order_by(User.elo.desc()).limit(10).all()])

@app.route("/api/friends", methods=["GET"])
@login_required
def get_friends(): return jsonify([f.to_dict() for f in current_user.friends.all()])

@app.route("/api/friends/add", methods=["POST"])
@login_required
def add_friend():
    t = User.query.filter_by(username=request.json.get("username")).first()
    if not t or t == current_user or t in current_user.friends: return jsonify({"success": False, "message": "Impossible."})
    current_user.friends.append(t); t.friends.append(current_user); db.session.commit()
    return jsonify({"success": True, "message": "Ajouté !"})


def get_game(sid):
    rid = player_rooms.get(sid)
    if rid and rid in games: return games[rid]["engine"], rid
    return None, None

def broadcast_etat(rid):
    if rid not in games: return
    jeu = games[rid]["engine"]
    emit("etat_jeu", jeu.get_etat_complet(), to=rid)
    for j in jeu.joueurs:
        if not j.est_bot:
            emit("ma_main", {"cartes": jeu.get_main_joueur(j.sid)}, to=j.sid)

def save_game_result(jeu, rid, winner_sid):
    has_bots = any(j.est_bot for j in jeu.joueurs)
    winner_name = next((j.nom for j in jeu.joueurs if j.sid == winner_sid), "Inconnu")
    
    new_hist = GameHistory(room_name=rid, winner_username=winner_name, has_bots=has_bots)
    db.session.add(new_hist)
    
    points_gagne = 5 if has_bots else 20
    points_perdu = -2 if has_bots else -5

    for j in jeu.joueurs:
        if j.est_bot: continue
        user_db = User.query.filter_by(username=j.nom).first()
        if user_db:
            if j.sid == winner_sid: user_db.update_stats(won=True, elo_diff=points_gagne)
            else: user_db.update_stats(won=False, elo_diff=points_perdu)
    db.session.commit()

def check_and_play_bots(rid):
    if rid not in games: return
    jeu = games[rid]["engine"]
    if not jeu.jeu_commence: return
    current = jeu.joueurs[jeu.tour_actuel]
    if current.est_bot:
        socketio.sleep(1.5)
        action = jeu.calculer_coup_bot()
        if action["action"] == "jouer":
            ok, msg = jeu.jouer_coup(current.sid, action["index"], action["couleur"])
        else:
            ok, msg = jeu.action_piocher(current.sid)
        broadcast_etat(rid)
        if "VICTOIRE" in msg: save_game_result(jeu, rid, current.sid); return
        check_and_play_bots(rid)


@socketio.on("rejoindre")
def handle_join(data):
    if not current_user.is_authenticated: return
    rid = data.get("room")
    pwd = data.get("password", "")
    
    if not rid: return emit("erreur", {"message": "Nom requis"}, to=request.sid)

    
    if rid not in games:
        games[rid] = {
            "engine": MoteurUno(),
            "password": pwd,
            "public": (pwd == "")
        }
    else:
        if games[rid]["password"] != "" and games[rid]["password"] != pwd:
            return emit("erreur", {"message": "Mot de passe incorrect !"}, to=request.sid)

    jeu = games[rid]["engine"]
    ok, msg = jeu.ajouter_joueur(current_user.username, request.sid)
    
    if ok:
        join_room(rid); player_rooms[request.sid] = rid
        emit("info", {"message": f"Bienvenue dans {rid}"}, to=request.sid)
        broadcast_etat(rid)
    else: emit("erreur", {"message": msg}, to=request.sid)

@socketio.on("add_bot")
def handle_add_bot():
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.ajouter_bot()
        broadcast_etat(rid)

@socketio.on("remove_bot")
def handle_remove_bot():
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.retirer_dernier_bot()
        if ok: broadcast_etat(rid)
        else: emit("erreur", {"message": msg}, to=request.sid)

@socketio.on("demarrer")
def handle_start(data):
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.demarrer_jeu(data.get("regles", {}))
        if ok: 
            broadcast_etat(rid)
            check_and_play_bots(rid)
        else: emit("erreur", {"message": msg}, to=request.sid)

@socketio.on("jouer_carte")
def handle_play(data):
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.jouer_coup(request.sid, data.get("index"), data.get("couleur"))
        if ok: 
            broadcast_etat(rid)
            if "VICTOIRE" in msg: save_game_result(jeu, rid, request.sid)
            else: check_and_play_bots(rid)
        else: emit("erreur", {"message": msg}, to=request.sid)

@socketio.on("piocher")
def handle_draw():
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.action_piocher(request.sid)
        if ok: broadcast_etat(rid); check_and_play_bots(rid)

@socketio.on("annoncer_uno")
def handle_uno():
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.action_annoncer_uno(request.sid)
        if ok: emit("info", {"message": msg}, to=rid); broadcast_etat(rid)

@socketio.on("contre_uno")
def handle_contre_uno():
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.action_contre_uno(request.sid)
        if ok: emit("info", {"message": msg}, to=rid); broadcast_etat(rid)

@socketio.on("contester_plus4")
def handle_contest():
    jeu, rid = get_game(request.sid)
    if jeu:
        ok, msg = jeu.action_contester_plus4(request.sid)
        if ok: emit("info", {"message": msg}, to=rid); broadcast_etat(rid); check_and_play_bots(rid)
        else: emit("erreur", {"message": msg}, to=request.sid)

@socketio.on("disconnect")
def handle_disconnect():
    rid = player_rooms.get(request.sid)
    if rid:
        del player_rooms[request.sid]
        if rid in games:
            games[rid]["engine"].retirer_joueur(request.sid)
            broadcast_etat(rid)
            if not games[rid]["engine"].joueurs and not games[rid]["engine"].spectateurs:
                del games[rid]

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    socketio.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
        allow_unsafe_werkzeug=True,
    )