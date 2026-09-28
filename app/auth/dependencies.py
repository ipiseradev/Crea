import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models import User

bearer = HTTPBearer()


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials.strip().strip('"')  # por si se pegó con comillas
    try:
        user_id = uuid.UUID(decode_access_token(token))
    except jwt.ExpiredSignatureError:
        raise _unauthorized("El token venció, volvé a iniciar sesión")
    except jwt.InvalidSignatureError:
        raise _unauthorized("Firma inválida: el token se generó con otro JWT_SECRET")
    except jwt.DecodeError:
        raise _unauthorized("Token mal formado: revisá que esté completo y sin 'Bearer' adelante")
    except (jwt.InvalidTokenError, ValueError):
        raise _unauthorized("Token inválido")

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("El usuario del token ya no existe")
    return user


def get_user_today(user: User = Depends(get_current_user)) -> date:
    """El "hoy" según la zona horaria del usuario, no la del servidor."""
    return datetime.now(ZoneInfo(user.timezone)).date()
