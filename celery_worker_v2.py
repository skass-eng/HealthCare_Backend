#!/usr/bin/env python3
"""
CELERY WORKER TASKS - Version Redis/Celery avec génération PDF
Worker pour traitement automatique des plaintes avec génération PDF
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from celery import Celery
from datetime import datetime
from sqlalchemy.orm import Session
from healthcare_api_server.app.db.database import SessionLocal
from shared.models import Plainte, AnalyseIA, Service, User
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Configuration Celery avec base de données comme broker temporaire
app = Celery('healthcare_worker')
app.conf.update(
    broker_url='sqla+sqlite:///celery.db',
    result_backend='db+sqlite:///results.db',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

def generate_plainte_pdf(plainte_id: int):
    """
    Générer un PDF bien organisé pour une plainte
    Récupère toutes les informations de la base de données
    """
    db = SessionLocal()
    try:
        # Récupérer la plainte avec toutes ses relations
        plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
        if not plainte:
            raise Exception(f"Plainte {plainte_id} non trouvée")
        
        # Récupérer le service associé
        service = db.query(Service).filter(Service.id == plainte.service_id).first()
        
        # Récupérer l'utilisateur assigné (si existe)
        assigned_user = None
        if plainte.assignee_a_id:
            assigned_user = db.query(User).filter(User.id == plainte.assignee_a_id).first()
        
        # Récupérer l'analyse IA (si existe)
        analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
        
        # Créer le répertoire de destination
        pdf_dir = "data/pdf_reports"
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Nom du fichier PDF
        pdf_filename = f"plainte_{plainte_id}_rapport_complet.pdf"
        pdf_path = os.path.join(pdf_dir, pdf_filename)
        
        # Créer le document PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 11
        normal_style.spaceAfter = 8
        
        # En-tête du document
        story.append(Paragraph("RAPPORT DE PLAINTE", title_style))
        story.append(Paragraph(f"Numéro: {plainte.numero_plainte}", styles['Heading3']))
        story.append(Spacer(1, 20))
        
        # Informations générales de la plainte
        story.append(Paragraph("📋 INFORMATIONS GÉNÉRALES", heading_style))
        
        info_data = [
            ['Numéro de plainte:', plainte.numero_plainte or 'N/A'],
            ['Titre:', plainte.titre or 'N/A'],
            ['Date de création:', plainte.date_creation.strftime('%d/%m/%Y %H:%M') if plainte.date_creation else 'N/A'],
            ['Statut:', plainte.statut.value if plainte.statut else 'N/A'],
            ['Priorité:', plainte.priorite.value if plainte.priorite else 'N/A'],
            ['Service concerné:', service.nom if service else 'N/A'],
            ['Mode de réception:', plainte.mode_reception or 'N/A'],
        ]
        
        if plainte.date_incident:
            info_data.append(['Date d\'incident:', plainte.date_incident.strftime('%d/%m/%Y')])
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Informations du plaignant
        story.append(Paragraph("👤 INFORMATIONS DU PLAIGNANT", heading_style))
        
        plaignant_data = [
            ['Nom:', plainte.nom_plaignant or 'N/A'],
            ['Prénom:', plainte.prenom_plaignant or 'N/A'],
            ['Email:', plainte.email_plaignant or 'N/A'],
            ['Téléphone:', plainte.telephone_plaignant or 'N/A'],
        ]
        
        plaignant_table = Table(plaignant_data, colWidths=[2*inch, 4*inch])
        plaignant_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(plaignant_table)
        story.append(Spacer(1, 20))
        
        # Description de la plainte
        story.append(Paragraph("📝 DESCRIPTION DE LA PLAINTE", heading_style))
        if plainte.description:
            # Traiter le texte pour éviter les problèmes d'encodage
            description_text = plainte.description.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(description_text, normal_style))
        else:
            story.append(Paragraph("Aucune description fournie.", normal_style))
        story.append(Spacer(1, 20))
        
        # Circonstances (si renseignées)
        if plainte.circonstances:
            story.append(Paragraph("📋 CIRCONSTANCES", heading_style))
            circonstances_text = plainte.circonstances.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(circonstances_text, normal_style))
            story.append(Spacer(1, 20))
        
        # Conséquences (si renseignées)
        if plainte.consequences:
            story.append(Paragraph("⚠️ CONSÉQUENCES", heading_style))
            consequences_text = plainte.consequences.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(consequences_text, normal_style))
            story.append(Spacer(1, 20))
        
        # Demande du plaignant (si renseignée)
        if plainte.demande_plaignant:
            story.append(Paragraph("🎯 DEMANDE DU PLAIGNANT", heading_style))
            demande_text = plainte.demande_plaignant.replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(demande_text, normal_style))
            story.append(Spacer(1, 20))
        
        # Analyse IA (si disponible)
        if analyse_ia:
            story.append(Paragraph("🤖 ANALYSE AUTOMATIQUE (IA)", heading_style))
            
            analyse_data = [
                ['Sentiment détecté:', analyse_ia.sentiment or 'N/A'],
                ['Confiance sentiment:', f"{analyse_ia.confiance_sentiment:.2f}" if analyse_ia.confiance_sentiment else 'N/A'],
                ['Service suggéré:', analyse_ia.service_suggere or 'N/A'],
                ['Priorité recommandée:', analyse_ia.priorite_ia or 'N/A'],
                ['Score priorité:', f"{analyse_ia.score_priorite:.2f}" if analyse_ia.score_priorite else 'N/A'],
                ['Urgence détectée:', 'Oui' if analyse_ia.urgence_detectee else 'Non'],
                ['Date d\'analyse:', analyse_ia.date_analyse.strftime('%d/%m/%Y %H:%M') if analyse_ia.date_analyse else 'N/A'],
            ]
            
            analyse_table = Table(analyse_data, colWidths=[2*inch, 4*inch])
            analyse_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(analyse_table)
            story.append(Spacer(1, 15))
            
            # Résumé IA
            if analyse_ia.resume_ia:
                story.append(Paragraph("📊 Résumé automatique:", heading_style))
                resume_text = analyse_ia.resume_ia.replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(resume_text, normal_style))
                story.append(Spacer(1, 15))
            
            # Réponse suggérée
            if analyse_ia.reponse_suggeree:
                story.append(Paragraph("💬 Réponse suggérée:", heading_style))
                reponse_text = analyse_ia.reponse_suggeree.replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(reponse_text, normal_style))
                story.append(Spacer(1, 20))
        
        # Informations de traitement
        story.append(Paragraph("⚙️ INFORMATIONS DE TRAITEMENT", heading_style))
        
        traitement_data = [
            ['Assigné à:', assigned_user.nom if assigned_user else 'Non assigné'],
            ['Date de modification:', plainte.date_modification.strftime('%d/%m/%Y %H:%M') if plainte.date_modification else 'N/A'],
        ]
        
        if plainte.date_resolution:
            traitement_data.append(['Date de résolution:', plainte.date_resolution.strftime('%d/%m/%Y %H:%M')])
        
        traitement_table = Table(traitement_data, colWidths=[2*inch, 4*inch])
        traitement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgreen),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(traitement_table)
        story.append(Spacer(1, 30))
        
        # Pied de page
        story.append(Paragraph("_" * 80, normal_style))
        story.append(Paragraph(f"Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", 
                              ParagraphStyle('Footer', parent=normal_style, fontSize=9, textColor=colors.grey)))
        
        # Construire le PDF
        doc.build(story)
        
        print(f"✅ PDF généré avec succès: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération PDF: {e}")
        raise
    finally:
        db.close()

@app.task(bind=True)
def analyse_plainte_task(self, plainte_id: int):
    """
    Tâche Celery pour analyser une plainte avec IA
    """
    try:
        print(f"🔬 Début analyse IA pour plainte {plainte_id}")
        
        db = SessionLocal()
        try:
            # Récupérer la plainte
            plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
            if not plainte:
                raise Exception(f"Plainte {plainte_id} non trouvée")
            
            # Simuler l'analyse IA
            import time
            time.sleep(2)  # Simuler le temps de traitement
            
            # Créer ou mettre à jour l'analyse IA
            analyse_ia = db.query(AnalyseIA).filter(AnalyseIA.plainte_id == plainte_id).first()
            if not analyse_ia:
                analyse_ia = AnalyseIA(plainte_id=plainte_id)
                db.add(analyse_ia)
            
            # Analyse intelligente basée sur le contenu
            texte_complet = f"{plainte.titre} {plainte.description}"
            
            # Analyse de sentiment
            if any(word in texte_complet.lower() for word in ['problème', 'mauvais', 'inacceptable', 'colère']):
                sentiment = 'négatif'
                confiance_sentiment = 0.8
            elif any(word in texte_complet.lower() for word in ['merci', 'satisfait', 'bien', 'excellent']):
                sentiment = 'positif' 
                confiance_sentiment = 0.7
            else:
                sentiment = 'neutre'
                confiance_sentiment = 0.6
            
            # Classification de service
            if any(word in texte_complet.lower() for word in ['urgence', 'urgent', 'grave']):
                service_suggere = "Service d'Urgence"
                priorite_ia = 'urgent'
                score_priorite = 0.9
            elif any(word in texte_complet.lower() for word in ['consultation', 'rendez-vous']):
                service_suggere = "Service de Consultation"
                priorite_ia = 'moyen'
                score_priorite = 0.5
            else:
                service_suggere = "Service Général"
                priorite_ia = 'bas'
                score_priorite = 0.3
            
            # Mettre à jour l'analyse
            analyse_ia.sentiment = sentiment
            analyse_ia.confiance_sentiment = confiance_sentiment
            analyse_ia.service_suggere = service_suggere
            analyse_ia.priorite_ia = priorite_ia
            analyse_ia.score_priorite = score_priorite
            analyse_ia.resume_ia = f"Plainte concernant {service_suggere.lower()}. Sentiment {sentiment}. Priorité {priorite_ia}."
            analyse_ia.reponse_suggeree = f"Nous avons bien reçu votre plainte #{plainte.numero_plainte}. Nous traiterons votre demande dans les meilleurs délais. Nous vous contacterons dès qu'une solution sera trouvée."
            analyse_ia.date_analyse = datetime.now()
            analyse_ia.date_mise_a_jour = datetime.now()
            
            db.commit()
            
        finally:
            db.close()
        
        # Résultats d'analyse
        analyse_result = {
            'plainte_id': plainte_id,
            'sentiment': sentiment,
            'confiance_sentiment': confiance_sentiment,
            'service_suggere': service_suggere,
            'priorite_ia': priorite_ia,
            'task_id': self.request.id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ Analyse IA terminée pour plainte {plainte_id}")
        return analyse_result
        
    except Exception as e:
        print(f"❌ Erreur analyse IA: {e}")
        self.retry(countdown=60, max_retries=3)

@app.task(bind=True)
def generate_pdf_task(self, plainte_id: int):
    """
    Tâche Celery pour générer un PDF depuis la base de données
    """
    try:
        print(f"📄 Début génération PDF pour plainte {plainte_id}")
        
        # Générer le PDF en récupérant les données de la BD
        pdf_path = generate_plainte_pdf(plainte_id)
        
        pdf_result = {
            'plainte_id': plainte_id,
            'pdf_path': pdf_path,
            'task_id': self.request.id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ PDF généré pour plainte {plainte_id}: {pdf_path}")
        return pdf_result
        
    except Exception as e:
        print(f"❌ Erreur génération PDF: {e}")
        self.retry(countdown=60, max_retries=3)

@app.task(bind=True)
def process_plainte_complete(self, plainte_id: int):
    """
    Tâche Celery pour traitement complet d'une plainte
    Orchestre l'analyse IA et la génération PDF
    """
    try:
        print(f"🚀 Début traitement complet plainte {plainte_id}")
        
        # Lancer les sous-tâches
        analyse_job = analyse_plainte_task.delay(plainte_id)
        pdf_job = generate_pdf_task.delay(plainte_id)
        
        # Attendre les résultats
        analyse_result = analyse_job.get(timeout=60)
        pdf_result = pdf_job.get(timeout=60)
        
        complete_result = {
            'plainte_id': plainte_id,
            'analyse': analyse_result,
            'pdf': pdf_result,
            'status': 'completed',
            'task_id': self.request.id,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"✅ Traitement complet terminé pour plainte {plainte_id}")
        return complete_result
        
    except Exception as e:
        print(f"❌ Erreur traitement complet: {e}")
        self.retry(countdown=60, max_retries=3)

def trigger_plainte_analysis(plainte_id: int):
    """
    Déclencher l'analyse d'une plainte (fonction appelée depuis l'API)
    """
    print(f"🎯 Déclenchement analyse pour plainte {plainte_id}")
    
    # Lancer la tâche principale
    job = process_plainte_complete.delay(plainte_id)
    
    return {
        'task_id': job.id,
        'status': 'PENDING',
        'plainte_id': plainte_id,
        'message': 'Analyse en cours...'
    }

if __name__ == "__main__":
    print("🚀 CELERY WORKER - HealthCare AI")
    print("Démarrage du worker...")
    app.worker_main()
