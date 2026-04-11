from app import app, db

"""
Script de reset de la base de données.

Fonctionnement :
- Supprime toutes les tables
- Les recrée vides
- À utiliser uniquement en développement
"""

with app.app_context():
    db.drop_all()
    db.create_all()

    print("Base de données réinitialisée.")
