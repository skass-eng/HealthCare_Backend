"""
Service de parsing de documents pour l'extraction de texte
Supporte les PDFs et les images (OCR)
"""
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import PyPDF2
import pytesseract
from PIL import Image
import io

logger = logging.getLogger(__name__)

class DocumentParserService:
    """Service pour extraire le texte des documents PDF et images"""
    
    def __init__(self):
        """Initialise le service de parsing"""
        self.supported_pdf_extensions = ['.pdf']
        self.supported_image_extensions = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    
    def extract_text_from_document(self, file_path: str) -> Dict[str, Any]:
        """
        Extrait le texte d'un document (PDF ou image)
        
        Args:
            file_path: Chemin vers le fichier à analyser
            
        Returns:
            Dict contenant le texte extrait et les métadonnées
        """
        if not os.path.exists(file_path):
            logger.error(f"Fichier non trouvé: {file_path}")
            return {
                "success": False,
                "error": "Fichier non trouvé",
                "text": "",
                "metadata": {}
            }
        
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension in self.supported_pdf_extensions:
                return self._extract_from_pdf(file_path)
            elif file_extension in self.supported_image_extensions:
                return self._extract_from_image(file_path)
            else:
                logger.error(f"Type de fichier non supporté: {file_extension}")
                return {
                    "success": False,
                    "error": f"Type de fichier non supporté: {file_extension}",
                    "text": "",
                    "metadata": {}
                }
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du texte: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "metadata": {}
            }
    
    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """Extrait le texte d'un fichier PDF"""
        logger.info(f"Extraction de texte PDF: {file_path}")
        
        text_content = ""
        metadata = {
            "file_type": "pdf",
            "pages": 0,
            "extraction_method": "PyPDF2"
        }
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata["pages"] = len(pdf_reader.pages)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content += f"\n--- Page {page_num} ---\n{page_text}\n"
                    except Exception as e:
                        logger.warning(f"Erreur extraction page {page_num}: {str(e)}")
                        continue
            
            if not text_content.strip():
                logger.warning("Aucun texte extrait du PDF - le document pourrait être scanné")
                return {
                    "success": False,
                    "error": "PDF scanné ou sans texte - OCR requis",
                    "text": "",
                    "metadata": metadata
                }
            
            logger.info(f"Texte extrait avec succès: {len(text_content)} caractères")
            return {
                "success": True,
                "text": text_content.strip(),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "metadata": metadata
            }
    
    def _extract_from_image(self, file_path: str) -> Dict[str, Any]:
        """Extrait le texte d'une image via OCR"""
        logger.info(f"Extraction de texte par OCR: {file_path}")
        
        metadata = {
            "file_type": "image",
            "extraction_method": "Tesseract OCR"
        }
        
        try:
            # Ouvrir l'image
            image = Image.open(file_path)
            metadata["image_size"] = image.size
            metadata["image_mode"] = image.mode
            
            # Configuration Tesseract pour le français
            custom_config = r'--oem 3 --psm 6 -l fra'
            
            # Extraction du texte
            text_content = pytesseract.image_to_string(image, config=custom_config)
            
            if not text_content.strip():
                logger.warning("Aucun texte détecté dans l'image")
                return {
                    "success": False,
                    "error": "Aucun texte détecté dans l'image",
                    "text": "",
                    "metadata": metadata
                }
            
            logger.info(f"Texte extrait par OCR: {len(text_content)} caractères")
            return {
                "success": True,
                "text": text_content.strip(),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'OCR: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "metadata": metadata
            }
    
    def is_document_parseable(self, file_path: str) -> bool:
        """Vérifie si le fichier peut être traité par ce service"""
        if not os.path.exists(file_path):
            return False
        
        file_extension = Path(file_path).suffix.lower()
        return (file_extension in self.supported_pdf_extensions or 
                file_extension in self.supported_image_extensions)
