from pa import database as db
from datetime import datetime


class Plugins(db.Model):
    __tablename__ = 'plugin'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(500), nullable=False)
    version = db.Column(db.String(100), nullable=False)
    installed = db.Column(db.Integer, nullable=False, default=0)
    install_datetime = db.Column(db.DateTime, nullable=False, default=datetime.now())
