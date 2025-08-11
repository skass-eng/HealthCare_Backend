#!/usr/bin/env python3
"""
TÂCHES DE GÉNÉRATION PDF - HealthCare AI Architecture ODYSSEE
Tâches Celery pour la génération de PDFs d'archivage des plaintes
Version: 1.0.0 - Architecture ODYSSEE
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID
import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from ..core.celery_app import healthcare_task
from ....shared.models import Plainte, Organisation, Service, User

logger = logging.getLogger(__name__)

# Import de la base de données (configuration partagée)
def get_database_session():
    """Récupérer une session de base de données pour les workers"""
    from ....healthcare_api_server.app.db.database import SessionLocal
    return SessionLocal()

@healthcare_task(name="healthcare_worker_server.tasks.generate_pdf.generate_plainte_pdf")
def generate_plainte_pdf(self, plainte_id: int):
    """
    Générer un PDF d'archivage pour une plainte
    """
    try:
        logger.info(f"🚀 Début génération PDF pour plainte {plainte_id}")
        
        # Récupérer la session DB
        db = get_database_session()
        
        try:
            # Récupérer la plainte avec toutes les relations
            plainte = db.query(Plainte).options(
                # Inclure les relations nécessaires
            ).filter(Plainte.id == plainte_id).first()
            
            if not plainte:
                raise ValueError(f"Plainte non trouvée: {plainte_id}")
            
            # Créer le dossier de stockage s'il n'existe pas
            pdf_dir = os.path.join(os.getcwd(), "data", "pdfs")
            os.makedirs(pdf_dir, exist_ok=True)
            
            # Générer le nom du fichier
            date_creation = plainte.date_creation.strftime("%Y%m%d")
            filename = f"PL_{plainte.numero_plainte}_{date_creation}.pdf"
            filepath = os.path.join(pdf_dir, filename)
            
            # Générer le PDF
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=20,
                textColor=colors.darkblue
            )
            
            normal_style = styles['Normal']
            
            # En-tête
            story.append(Paragraph("ARCHIVE PLAINTE HOSPITALIÈRE", title_style))
            story.append(Spacer(1, 20))
            
            # Informations de base
            story.append(Paragraph("INFORMATIONS DE BASE", subtitle_style))
            
            basic_info = [
                ["Numéro de plainte:", plainte.numero_plainte],
                ["Date de création:", plainte.date_creation.strftime("%d/%m/%Y à %H:%M")],
                ["Statut:", plainte.statut.value if plainte.statut else "Non défini"],
                ["Priorité:", plainte.priorite.value if plainte.priorite else "Non définie"],
            ]
            
            if plainte.date_incident:
                basic_info.append(["Date de l'incident:", plainte.date_incident.strftime("%d/%m/%Y")])
            
            basic_table = Table(basic_info, colWidths=[2*inch, 4*inch])
            basic_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(basic_table)
            story.append(Spacer(1, 20))
            
            # Contenu de la plainte
            story.append(Paragraph("CONTENU DE LA PLAINTE", subtitle_style))
            
            story.append(Paragraph(f"<b>Titre:</b> {plainte.titre}", normal_style))
            story.append(Spacer(1, 10))
            
            story.append(Paragraph("<b>Description:</b>", normal_style))
            story.append(Paragraph(plainte.description, normal_style))
            story.append(Spacer(1, 20))
            
            # Informations organisationnelles
            if plainte.organisation:
                story.append(Paragraph("INFORMATIONS ORGANISATIONNELLES", subtitle_style))
                
                org_info = [
                    ["Organisation:", plainte.organisation.nom],
                    ["Code établissement:", plainte.organisation.code_etablissement],
                ]
                
                if plainte.service:
                    org_info.append(["Service concerné:", plainte.service.nom])
                    org_info.append(["Code service:", plainte.service.code_service])
                
                org_table = Table(org_info, colWidths=[2*inch, 4*inch])
                org_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(org_table)
                story.append(Spacer(1, 20))
            
            # Analyses IA
            if plainte.analyses:
                story.append(Paragraph("ANALYSES INTELLIGENCE ARTIFICIELLE", subtitle_style))
                
                for analyse in plainte.analyses:
                    story.append(Paragraph(f"<b>Type d'analyse:</b> {analyse.type_analyse.value}", normal_style))
                    story.append(Paragraph(f"<b>Statut:</b> {analyse.statut.value}", normal_style))
                    
                    if analyse.resultats:
                        story.append(Paragraph("<b>Résultats:</b>", normal_style))
                        resultats_text = json.dumps(analyse.resultats, indent=2, ensure_ascii=False)
                        story.append(Paragraph(resultats_text, normal_style))
                    
                    story.append(Spacer(1, 10))
                
                story.append(Spacer(1, 20))
            
            # Métadonnées
            if plainte.analyse_ia:
                story.append(Paragraph("MÉTADONNÉES D'ANALYSE", subtitle_style))
                
                metadata_text = json.dumps(plainte.analyse_ia, indent=2, ensure_ascii=False)
                story.append(Paragraph(metadata_text, normal_style))
                story.append(Spacer(1, 20))
            
            # Pied de page
            story.append(Spacer(1, 30))
            story.append(Paragraph(
                f"Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}",
                ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=8,
                    alignment=TA_CENTER,
                    textColor=colors.grey
                )
            ))
            
            # Construire le PDF
            doc.build(story)
            
            logger.info(f"✅ PDF généré avec succès: {filepath}")
            
            # Mettre à jour la plainte avec le chemin du PDF
            plainte.metadata = {
                **plainte.metadata,
                "pdf_generated": True,
                "pdf_path": filepath,
                "pdf_generated_at": datetime.now().isoformat()
            }
            db.commit()
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "plainte_id": plainte_id
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du PDF: {e}")
        raise

@healthcare_task(name="healthcare_worker_server.tasks.generate_pdf.generate_response_pdf")
def generate_response_pdf(self, plainte_id: int, response_text: str):
    """
    Générer un PDF de réponse pour une plainte
    """
    try:
        logger.info(f"🚀 Début génération PDF de réponse pour plainte {plainte_id}")
        
        # Récupérer la session DB
        db = get_database_session()
        
        try:
            # Récupérer la plainte
            plainte = db.query(Plainte).filter(Plainte.id == plainte_id).first()
            
            if not plainte:
                raise ValueError(f"Plainte non trouvée: {plainte_id}")
            
            # Créer le dossier de stockage s'il n'existe pas
            pdf_dir = os.path.join(os.getcwd(), "data", "reponses")
            os.makedirs(pdf_dir, exist_ok=True)
            
            # Générer le nom du fichier
            date_creation = plainte.date_creation.strftime("%Y%m%d")
            filename = f"REP_{plainte.numero_plainte}_{date_creation}.pdf"
            filepath = os.path.join(pdf_dir, filename)
            
            # Générer le PDF de réponse
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.darkblue
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=20,
                textColor=colors.darkblue
            )
            
            normal_style = styles['Normal']
            
            # En-tête
            story.append(Paragraph("RÉPONSE À LA PLAINTE HOSPITALIÈRE", title_style))
            story.append(Spacer(1, 20))
            
            # Informations de la plainte
            story.append(Paragraph("RÉFÉRENCE DE LA PLAINTE", subtitle_style))
            
            plainte_info = [
                ["Numéro de plainte:", plainte.numero_plainte],
                ["Date de création:", plainte.date_creation.strftime("%d/%m/%Y à %H:%M")],
                ["Titre:", plainte.titre],
            ]
            
            plainte_table = Table(plainte_info, colWidths=[2*inch, 4*inch])
            plainte_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(plainte_table)
            story.append(Spacer(1, 20))
            
            # Réponse
            story.append(Paragraph("RÉPONSE DU RESPONSABLE QUALITÉ", subtitle_style))
            story.append(Paragraph(response_text, normal_style))
            story.append(Spacer(1, 20))
            
            # Pied de page
            story.append(Spacer(1, 30))
            story.append(Paragraph(
                f"Document généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}",
                ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=8,
                    alignment=TA_CENTER,
                    textColor=colors.grey
                )
            ))
            
            # Construire le PDF
            doc.build(story)
            
            logger.info(f"✅ PDF de réponse généré avec succès: {filepath}")
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "plainte_id": plainte_id
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la génération du PDF de réponse: {e}")
        raise 