from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Reponse(db.Model):
    __tablename__ = 'reponses'

    id                  = db.Column(db.Integer, primary_key=True)
    niveau_etudes       = db.Column(db.String(50),  nullable=False)
    appareil            = db.Column(db.String(50),  nullable=False)
    operateur           = db.Column(db.String(50),  nullable=False)
    type_forfait        = db.Column(db.String(50),  nullable=False)
    depenses_mensuelles = db.Column(db.Float,       nullable=False)
    heures_telephone    = db.Column(db.Float,       nullable=False)
    heures_streaming    = db.Column(db.Float,       nullable=False)
    apps_utilisees      = db.Column(db.Text,        nullable=False)
    date_reponse        = db.Column(db.DateTime,    default=datetime.utcnow)

    def __repr__(self):
        return f'<Reponse {self.id} | {self.niveau_etudes} | {self.operateur}>'
