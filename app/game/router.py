from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.habits.schemas import BuildingResponse, CityResponse
from app.models import Building, City, User

router = APIRouter(prefix="/city", tags=["city"])


def _buildings(db: Session, user: User) -> list[Building]:
    return list(
        db.scalars(
            select(Building)
            .where(Building.user_id == user.id)
            .order_by(Building.built_on, Building.x, Building.y)
        )
    )


@router.get("", response_model=CityResponse)
def get_city(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    city = db.get(City, user.id)
    return CityResponse(
        bricks=city.bricks,
        current_streak=city.current_streak,
        best_streak=city.best_streak,
        buildings=_buildings(db, user),
    )


@router.get("/timeline", response_model=list[BuildingResponse])
def get_timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Edificios en orden de construcción, para armar el timelapse."""
    return _buildings(db, user)
