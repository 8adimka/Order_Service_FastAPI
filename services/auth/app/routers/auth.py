import logging
import os
import secrets
from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..config import settings
from ..crud import (
    create_user_from_google,
    get_user_by_google_id,
    link_google_to_existing_user,
)
from ..database import get_db
from ..dependencies import create_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register/", response_model=dict)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    created_user = crud.create_user(db=db, user=user)
    return {"msg": "User created", "user_id": created_user.id}


@router.post("/token/", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/google/login")
def google_login(request: Request):
    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("OAUTH_GOOGLE_CLIENT_ID")
    redirect_uri = (
        os.getenv("GOOGLE_REDIRECT_URI")
        or os.getenv("OAUTH_GOOGLE_REDIRECT_URI")
        or "http://localhost:8001/auth/callback/google"
    )
    if not client_id:
        raise HTTPException(status_code=500, detail="Google client id not configured")

    state = secrets.token_urlsafe(32)
    logger.info("Generated OAuth state for CSRF protection")

    scope = "openid email profile"
    authorization_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope.replace(' ', '%20')}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )

    response = JSONResponse({"login_url": authorization_url})
    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return response


@router.get("/callback/google", response_model=schemas.TokenResponse)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    state_from_query = request.query_params.get("state")
    state_from_cookie = request.cookies.get("oauth_state")

    if not state_from_query or not state_from_cookie:
        logger.warning("CSRF state check failed: missing state")
        raise HTTPException(status_code=400, detail="Missing state parameter")

    if state_from_query != state_from_cookie:
        logger.warning(
            f"CSRF state mismatch: query_state={state_from_query[:10]}..., "
            f"cookie_state={state_from_cookie[:10] if state_from_cookie else 'None'}..."
        )
        raise HTTPException(
            status_code=400, detail="Invalid state parameter (CSRF check failed)"
        )

    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        error_description = request.query_params.get(
            "error_description", "Unknown error"
        )
        logger.warning(f"Google OAuth error: {error} - {error_description}")
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("OAUTH_GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv(
        "OAUTH_GOOGLE_CLIENT_SECRET"
    )
    redirect_uri = (
        os.getenv("GOOGLE_REDIRECT_URI")
        or os.getenv("OAUTH_GOOGLE_REDIRECT_URI")
        or "http://localhost:8001/auth/callback/google"
    )

    if not client_id or not client_secret:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    token_url = "https://oauth2.googleapis.com/token"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                token_url,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
    except Exception as e:
        logger.error(f"Failed to connect to Google token endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect to Google")

    if resp.status_code != 200:
        logger.error(f"Google token response error: {resp.status_code} - {resp.text}")
        raise HTTPException(
            status_code=400, detail="Failed to fetch tokens from Google"
        )

    tokens = resp.json()
    id_token_str = tokens.get("id_token")
    if not id_token_str:
        logger.error("No id_token returned by Google")
        raise HTTPException(status_code=400, detail="No id_token returned by Google")

    try:
        id_info = id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), client_id
        )
    except ValueError as e:
        logger.error(f"Invalid Google id_token: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid Google id_token")

    google_sub = id_info.get("sub")
    email = id_info.get("email")
    name = id_info.get("name")
    picture = id_info.get("picture")

    if not google_sub or not email:
        logger.warning("Incomplete token info from Google")
        raise HTTPException(status_code=400, detail="Incomplete token info")

    logger.info(f"Verified Google user: {email}")

    user = get_user_by_google_id(db, google_sub)
    if not user:
        user_by_email = crud.get_user_by_email(db, email)
        if user_by_email:
            logger.info(f"Linking Google account to existing user: {email}")
            user = link_google_to_existing_user(
                db, user_by_email, google_sub, tokens.get("refresh_token")
            )
        else:
            logger.info(f"Creating new user from Google: {email}")
            user = create_user_from_google(
                db,
                email=email,
                google_id=google_sub,
                full_name=name,
                picture_url=picture,
                refresh_token=tokens.get("refresh_token"),
            )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    logger.info(f"User authenticated via Google: user_id={user.id}")

    response = JSONResponse(
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "picture_url": user.picture_url,
            "auth_provider": user.auth_provider,
            "access_token": access_token,
            "token_type": "bearer",
        }
    )

    response.delete_cookie("oauth_state")
    return response
