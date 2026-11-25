from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

friends_association = db.Table('friends',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    

    elo = db.Column(db.Integer, default=1000)
    games_played = db.Column(db.Integer, default=0)
    games_won = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    is_admin = db.Column(db.Boolean, default=False)

    friends = db.relationship(
        'User', 
        secondary=friends_association,
        primaryjoin=(friends_association.c.user_id == id),
        secondaryjoin=(friends_association.c.friend_id == id),
        backref=db.backref('friend_of', lazy='dynamic'), 
        lazy='dynamic'
    )

    def update_stats(self, won, elo_diff):
        """Met à jour les stats après une partie"""
        self.games_played += 1
        self.elo += elo_diff
        if won:
            self.games_won += 1
        if self.elo < 0: self.elo = 0

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "elo": self.elo,
            "is_admin": self.is_admin, 
            "games_played": self.games_played,
            "win_rate": round((self.games_won / self.games_played * 100), 1) if self.games_played > 0 else 0
        }

class GameHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    room_name = db.Column(db.String(50))
    winner_username = db.Column(db.String(80))
    has_bots = db.Column(db.Boolean, default=False)