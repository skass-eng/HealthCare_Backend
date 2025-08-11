#!/usr/bin/env python3
"""
WORKER TASKS SIMULÉS - Analyse IA et PDF
Simulation des workers pour l'analyse automatique des plaintes
"""

import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from shared.models import Plainte, AnalyseIA, PrioritePlainte

logger = logging.getLogger(__name__)

async def trigger_analyse_plainte_complete(plainte_id: int, db: Session):
    """
    Déclencher toutes les analyses pour une plainte nouvellement créée.
    Effectue directement l'analyse IA et génère le PDF.
    """
    tasks_results = {}
    
    try:
        # Récupérer l'entrée analyses_ia créée ou la créer
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        if not analyse_ia:
            logger.info(f"Création d'une nouvelle analyse IA pour plainte {plainte_id}")
            analyse_ia = AnalyseIA(plainte_id=plainte_id)
            db.add(analyse_ia)
            db.commit()
            db.refresh(analyse_ia)
        
        # 1. FAIRE L'ANALYSE IA AUTOMATIQUE
        logger.info(f"🔬 Début de l'analyse IA pour plainte {plainte_id}")
        
        # Récupérer les données de la plainte
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            return tasks_results
            
        # Effectuer l'analyse IA (simulation intelligente)
        texte_complet = f"{plainte.titre} {plainte.description}"
        
        # Analyse de sentiment
        if "problème" in texte_complet.lower() or "plainte" in texte_complet.lower():
            sentiment = "négatif"
            confiance_sentiment = 0.8
        elif "merci" in texte_complet.lower() or "satisfait" in texte_complet.lower():
            sentiment = "positif" 
            confiance_sentiment = 0.7
        else:
            sentiment = "neutre"
            confiance_sentiment = 0.6
            
        # Classification par service
        service_suggere = "Service Général"
        if "urgence" in texte_complet.lower():
            service_suggere = "Service d'Urgence"
        elif "consultation" in texte_complet.lower():
            service_suggere = "Service de Consultation"
            
        # Détermination de la priorité
        if plainte.priorite == PrioritePlainte.URGENT:
            priorite_ia = "urgent"
            score_priorite = 0.9
        elif "urgent" in texte_complet.lower() or "grave" in texte_complet.lower():
            priorite_ia = "élevé"
            score_priorite = 0.8
        else:
            priorite_ia = "moyen"
            score_priorite = 0.5
            
        # Génération du résumé
        resume = f"Plainte concernant {service_suggere.lower()}. Sentiment {sentiment}. Priorité {priorite_ia}."
        
        # Génération de la réponse automatique
        reponse = f"Nous avons bien reçu votre plainte #{plainte.numero_plainte}. "
        if priorite_ia == "urgent":
            reponse += "Votre demande sera traitée en priorité dans les 24h. "
        else:
            reponse += "Nous traiterons votre demande dans les meilleurs délais. "
        reponse += "Nous vous contacterons dès qu'une solution sera trouvée."
        
        # Mettre à jour l'analyse IA dans la base
        analyse_ia.sentiment = sentiment
        analyse_ia.confiance_sentiment = confiance_sentiment
        analyse_ia.service_suggere = service_suggere
        analyse_ia.confiance_service = 0.7
        analyse_ia.priorite_ia = priorite_ia
        analyse_ia.score_priorite = score_priorite
        analyse_ia.resume_ia = resume
        analyse_ia.reponse_suggeree = reponse
        analyse_ia.date_analyse = datetime.now()
        
        db.commit()
        
        tasks_results["analyse_ia"] = "completed"
        logger.info(f"✅ Analyse IA terminée pour plainte {plainte_id}")
        
        # 2. GÉNÉRER LE PDF DE LA PLAINTE
        logger.info(f"📄 Génération du PDF pour plainte {plainte_id}")
        
        try:
            # Créer le dossier pour les PDFs s'il n'existe pas
            pdf_dir = os.path.join(os.getcwd(), "data", "pdfs")
            os.makedirs(pdf_dir, exist_ok=True)
            
            # Nom du fichier PDF
            pdf_filename = f"plainte_{plainte.numero_plainte}"
            
            # Contenu HTML pour le PDF
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Plainte {plainte.numero_plainte}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .label {{ font-weight: bold; color: #34495e; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Plainte #{plainte.numero_plainte}</h1>
        <p>Date de création: {plainte.date_creation.strftime('%d/%m/%Y %H:%M')}</p>
    </div>
    
    <div class="section">
        <div class="label">Titre:</div>
        <p>{plainte.titre}</p>
    </div>
    
    <div class="section">
        <div class="label">Description:</div>
        <p>{plainte.description}</p>
    </div>
    
    <div class="section">
        <div class="label">Informations du plaignant:</div>
        <p>Nom: {plainte.nom_plaignant or 'Non renseigné'}</p>
        <p>Email: {plainte.email_plaignant or 'Non renseigné'}</p>
        <p>Téléphone: {plainte.telephone_plaignant or 'Non renseigné'}</p>
    </div>
    
    <div class="section">
        <div class="label">Statut et Priorité:</div>
        <p>Statut: {plainte.statut.value}</p>
        <p>Priorité: {plainte.priorite.value}</p>
    </div>
    
    <div class="section">
        <div class="label">Analyse IA:</div>
        <p>Sentiment: {sentiment}</p>
        <p>Service suggéré: {service_suggere}</p>
        <p>Priorité IA: {priorite_ia}</p>
        <p>Résumé: {resume}</p>
    </div>
    
    <div class="section">
        <div class="label">Réponse suggérée:</div>
        <p>{reponse}</p>
    </div>
</body>
</html>
            """
            
            # Sauvegarder le HTML
            html_path = os.path.join(pdf_dir, f"{pdf_filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Créer aussi un fichier texte simple
            txt_path = os.path.join(pdf_dir, f"{pdf_filename}.txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"PLAINTE #{plainte.numero_plainte}\\n")
                f.write(f"===============================\\n")
                f.write(f"Date: {plainte.date_creation}\\n")
                f.write(f"Titre: {plainte.titre}\\n")
                f.write(f"Description: {plainte.description}\\n")
                f.write(f"Plaignant: {plainte.nom_plaignant}\\n")
                f.write(f"Email: {plainte.email_plaignant}\\n")
                f.write(f"\\nANALYSE IA:\\n")
                f.write(f"Sentiment: {sentiment}\\n")
                f.write(f"Service suggéré: {service_suggere}\\n")
                f.write(f"Priorité: {priorite_ia}\\n")
                f.write(f"Résumé: {resume}\\n")
                f.write(f"\\nRÉPONSE SUGGÉRÉE:\\n")
                f.write(f"{reponse}\\n")
            
            tasks_results["pdf_generation"] = "completed"
            tasks_results["pdf_html_path"] = html_path
            tasks_results["pdf_txt_path"] = txt_path
            logger.info(f"✅ PDF généré: {html_path}")
            
        except Exception as e:
            logger.error(f"Erreur génération PDF: {e}")
            tasks_results["pdf_generation"] = "failed"
        
        return tasks_results
        
    except Exception as e:
        logger.error(f"❌ Erreur lors des analyses: {e}")
        return {"error": str(e)}
