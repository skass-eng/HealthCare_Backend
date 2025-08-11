from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from shared.models import Plainte
from ..db.database import get_db

router = APIRouter()

@router.get("/total", response_model=int)
def get_total_complaints_for_year(year: int, db: Session = Depends(get_db)):
    try:
        total_complaints = db.query(Plainte).filter(Plainte.date_creation.year == year).count()
        return total_complaints
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
def create_plainte(plainte_data: dict, db: Session = Depends(get_db)):
    try:
        new_plainte = Plainte(**plainte_data)
        db.add(new_plainte)
        db.commit()
        db.refresh(new_plainte)
        return new_plainte
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
