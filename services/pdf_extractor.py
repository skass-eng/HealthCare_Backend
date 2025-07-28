"""
Service d'extraction de texte à partir de fichiers PDF
"""

import PyPDF2
import pdfplumber
import os
from typing import Dict, Optional, Tuple
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFExtractor:
    """Extracteur de texte pour fichiers PDF"""
    
    def __init__(self):
        self.supported_formats = ['.pdf']
    
    def extract_text_pypdf2(self, file_path: str) -> Dict[str, any]:
        """Extraire le texte avec PyPDF2 (méthode de base)"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                num_pages = len(pdf_reader.pages)
                
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
                
                return {
                    'success': True,
                    'text': text.strip(),
                    'num_pages': num_pages,
                    'method': 'PyPDF2',
                    'confidence': 0.7 if text.strip() else 0.1
                }
        except Exception as e:
            logger.error(f"Erreur PyPDF2 pour {file_path}: {e}")
            return {
                'success': False,
                'text': "",
                'error': str(e),
                'method': 'PyPDF2',
                'confidence': 0.0
            }
    
    def extract_text_pdfplumber(self, file_path: str) -> Dict[str, any]:
        """Extraire le texte avec pdfplumber (méthode avancée)"""
        try:
            text = ""
            num_pages = 0
            
            with pdfplumber.open(file_path) as pdf:
                num_pages = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                return {
                    'success': True,
                    'text': text.strip(),
                    'num_pages': num_pages,
                    'method': 'pdfplumber',
                    'confidence': 0.9 if text.strip() else 0.2
                }
        except Exception as e:
            logger.error(f"Erreur pdfplumber pour {file_path}: {e}")
            return {
                'success': False,
                'text': "",
                'error': str(e),
                'method': 'pdfplumber',
                'confidence': 0.0
            }
    
    def extract_text(self, file_path: str) -> Dict[str, any]:
        """Extraire le texte avec la meilleure méthode disponible"""
        if not os.path.exists(file_path):
            return {
                'success': False,
                'text': "",
                'error': f"Fichier non trouvé: {file_path}",
                'confidence': 0.0
            }
        
        # Essayer d'abord pdfplumber (plus robuste)
        result_plumber = self.extract_text_pdfplumber(file_path)
        
        # Si pdfplumber échoue ou donne un résultat vide, essayer PyPDF2
        if not result_plumber['success'] or not result_plumber['text'].strip():
            logger.info(f"pdfplumber a échoué, essai avec PyPDF2 pour {file_path}")
            result_pypdf2 = self.extract_text_pypdf2(file_path)
            
            # Prendre le meilleur résultat
            if result_pypdf2['success'] and result_pypdf2['text'].strip():
                return result_pypdf2
            else:
                return result_plumber  # Retourner le résultat pdfplumber même s'il a échoué
        
        return result_plumber
    
    def get_pdf_info(self, file_path: str) -> Dict[str, any]:
        """Obtenir les métadonnées du PDF"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                metadata = pdf_reader.metadata or {}
                
                return {
                    'num_pages': len(pdf_reader.pages),
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'creation_date': str(metadata.get('/CreationDate', '')),
                    'modification_date': str(metadata.get('/ModDate', ''))
                }
        except Exception as e:
            logger.error(f"Erreur métadonnées pour {file_path}: {e}")
            return {}
    
    def process_pdf(self, file_path: str) -> Dict[str, any]:
        """Traiter complètement un fichier PDF"""
        logger.info(f"🔍 Traitement PDF: {file_path}")
        
        # Extraction du texte
        text_result = self.extract_text(file_path)
        
        # Métadonnées
        metadata = self.get_pdf_info(file_path)
        
        # Statistiques du texte
        text = text_result.get('text', '')
        word_count = len(text.split()) if text else 0
        char_count = len(text) if text else 0
        
        result = {
            'file_path': file_path,
            'extraction_success': text_result['success'],
            'text_content': text,
            'num_pages': text_result.get('num_pages', metadata.get('num_pages', 0)),
            'word_count': word_count,
            'char_count': char_count,
            'extraction_method': text_result.get('method', 'unknown'),
            'confidence': text_result.get('confidence', 0.0),
            'metadata': metadata,
            'error': text_result.get('error', None)
        }
        
        logger.info(f"✅ PDF traité: {word_count} mots, {char_count} caractères, confiance: {result['confidence']}")
        
        return result

# Instance globale
pdf_extractor = PDFExtractor() 