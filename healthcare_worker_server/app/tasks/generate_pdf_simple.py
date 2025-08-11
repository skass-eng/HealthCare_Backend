#!/usr/bin/env python3
"""
TÂCHE SIMPLIFIÉE - GÉNÉRATION PDF DES PLAINTES
Génération de PDF dans le dossier data
Version: 1.0.0 - Architecture ODYSSEE
"""

import logging
import os
import random
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

def generate_plainte_pdf_simple(plainte_id: int):
    """
    Générer un PDF simple pour une plainte
    """
    try:
        # Importer ici pour éviter les imports circulaires
        from healthcare_api_server.app.db.database import SessionLocal
        from shared.models import Plainte, AnalyseIA
        
        db = SessionLocal()
        
        try:
            # Récupérer la plainte
            plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
            if not plainte:
                logger.error(f"Plainte {plainte_id} non trouvée")
                return
            
            # Récupérer l'analyse IA si disponible
            analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
            
            # Créer le dossier PDF s'il n'existe pas
            pdf_dir = Path(os.getcwd()) / "data" / "pdf"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            
            # Nom du fichier PDF
            pdf_filename = f"plainte_{plainte.numero_plainte}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = pdf_dir / pdf_filename
            
            # Générer le contenu HTML simple (à convertir en PDF avec une vraie lib)
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Plainte {plainte.numero_plainte}</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
                    .section {{ margin: 20px 0; }}
                    .label {{ font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>RAPPORT DE PLAINTE</h1>
                    <p><span class="label">Numéro:</span> {plainte.numero_plainte}</p>
                    <p><span class="label">Date de création:</span> {plainte.date_creation.strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                
                <div class="section">
                    <h2>Informations du plaignant</h2>
                    <p><span class="label">Nom:</span> {plainte.nom_plaignant or 'Non spécifié'}</p>
                    <p><span class="label">Prénom:</span> {plainte.prenom_plaignant or 'Non spécifié'}</p>
                    <p><span class="label">Email:</span> {plainte.email_plaignant or 'Non spécifié'}</p>
                    <p><span class="label">Téléphone:</span> {plainte.telephone_plaignant or 'Non spécifié'}</p>
                </div>
                
                <div class="section">
                    <h2>Détails de la plainte</h2>
                    <p><span class="label">Titre:</span> {plainte.titre}</p>
                    <p><span class="label">Description:</span></p>
                    <p>{plainte.description}</p>
                    <p><span class="label">Mode de réception:</span> {plainte.mode_reception}</p>
                    <p><span class="label">Date de l'incident:</span> {plainte.date_incident.strftime('%d/%m/%Y') if plainte.date_incident else 'Non spécifiée'}</p>
                </div>
                
                <div class="section">
                    <h2>Statut</h2>
                    <p><span class="label">Statut actuel:</span> {plainte.statut}</p>
                    <p><span class="label">Priorité:</span> {plainte.priorite}</p>
                </div>
            """
            
            if analyse_ia:
                html_content += f"""
                <div class="section">
                    <h2>Analyse IA</h2>
                    <p><span class="label">Sentiment détecté:</span> {analyse_ia.sentiment} (confiance: {analyse_ia.confidence_sentiment})</p>
                    <p><span class="label">Service suggéré:</span> {analyse_ia.service_predit} (confiance: {analyse_ia.confidence_service})</p>
                    <p><span class="label">Priorité suggérée:</span> {analyse_ia.priorite_suggeree} (confiance: {analyse_ia.confidence_priorite})</p>
                    <p><span class="label">Résumé IA:</span></p>
                    <p>{analyse_ia.resume_ia}</p>
                    <p><span class="label">Réponse suggérée:</span></p>
                    <p>{analyse_ia.reponse_suggeree}</p>
                    <p><span class="label">Date d'analyse:</span> {analyse_ia.date_analyse.strftime('%d/%m/%Y %H:%M') if analyse_ia.date_analyse else 'Non effectuée'}</p>
                </div>
                """
            
            html_content += """
                <div class="section">
                    <hr>
                    <p><small>Document généré automatiquement par le système HealthCare ODYSSEE</small></p>
                    <p><small>Date de génération: """ + datetime.now().strftime('%d/%m/%Y %H:%M:%S') + """</small></p>
                </div>
            </body>
            </html>
            """
            
            # Pour l'instant, sauvegarder comme HTML (à remplacer par une vraie conversion PDF)
            html_path = pdf_dir / f"plainte_{plainte.numero_plainte}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Créer un fichier texte simple en plus
            txt_path = pdf_dir / f"plainte_{plainte.numero_plainte}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"PLAINTE {plainte.numero_plainte}\\n")
                f.write(f"{'='*50}\\n")
                f.write(f"Plaignant: {plainte.prenom_plaignant} {plainte.nom_plaignant}\\n")
                f.write(f"Email: {plainte.email_plaignant}\\n")
                f.write(f"Titre: {plainte.titre}\\n")
                f.write(f"Description: {plainte.description}\\n")
                f.write(f"Date: {plainte.date_creation}\\n")
                if analyse_ia:
                    f.write(f"\\nANALYSE IA:\\n")
                    f.write(f"Sentiment: {analyse_ia.sentiment}\\n")
                    f.write(f"Priorité: {analyse_ia.priorite_suggeree}\\n")
                    f.write(f"Résumé: {analyse_ia.resume_ia}\\n")
            
            logger.info(f"✅ PDF/HTML généré pour plainte {plainte_id}: {html_path}")
            
            return {
                "status": "success",
                "plainte_id": plainte_id,
                "html_path": str(html_path),
                "txt_path": str(txt_path)
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération PDF: {e}")
        return {"status": "error", "error": str(e)}

# Mock pour la fonction delay de Celery
class MockPDFTask:
    def __init__(self, func):
        self.func = func
        self.id = f"pdf_task_{random.randint(1000, 9999)}"
    
    def delay(self, *args, **kwargs):
        # Exécuter immédiatement en mode synchrone pour les tests
        result = self.func(*args, **kwargs)
        return self

# Créer l'instance mock
generate_plainte_pdf = MockPDFTask(generate_plainte_pdf_simple)
