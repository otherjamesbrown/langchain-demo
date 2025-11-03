"""
Database operations for company research data.

This module provides high-level functions for storing and retrieving
company information, search history, and agent execution records.
"""

import logging
import os
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Session
from src.database.schema import (
    Company,
    SearchHistory,
    ModelConfiguration,
    APICredential,
    AppSetting,
    get_session,
    create_database
)

if TYPE_CHECKING:
    from src.tools.models import CompanyInfo


logger = logging.getLogger(__name__)

GEMINI_ENV_VAR_NAME = "GOOGLE_API_KEY"


def _load_gemini_api_key_from_env() -> Optional[str]:
    """Return the Gemini API key sourced from the environment if configured."""

    # We intentionally source secrets from the environment so they never live in the codebase.
    # See `config/env.example` for instructions on setting the `GOOGLE_API_KEY` variable.
    value = os.getenv(GEMINI_ENV_VAR_NAME)
    if value:
        return value.strip()
    return None


def init_database():
    """Initialize database by creating all tables."""
    create_database()


def _resolve_session(session: Optional[Session]) -> tuple[Session, bool]:
    """Return a session and flag indicating whether it should be closed."""

    if session is None:
        return get_session(), True
    return session, False


def ensure_default_configuration(session: Optional[Session] = None) -> None:
    """Seed the database with default models and API credentials if missing."""

    from src.models.local_registry import list_local_models

    db_session, should_close = _resolve_session(session)
    created = False

    try:
        # Sync local models from registry
        for local_config in list_local_models():
            existing = (
                db_session.query(ModelConfiguration)
                .filter(
                    ModelConfiguration.model_key == local_config.key
                )
                .first()
            )

            metadata_payload = {
                "description": local_config.description,
                "recommended_vram_gb": local_config.recommended_vram_gb,
                "context_window": local_config.context_window,
                "max_output_tokens": max(local_config.context_window // 2, 512),
            }
            if local_config.chat_format:
                metadata_payload["chat_format"] = local_config.chat_format

            if existing is None:
                db_session.add(
                    ModelConfiguration(
                        name=local_config.display_name,
                        provider="local",
                        model_key=local_config.key,
                        model_path=str(local_config.resolve_path()),
                        extra_metadata=metadata_payload,
                    )
                )
                created = True
            else:
                updated = False
                if not existing.model_path:
                    existing.model_path = str(local_config.resolve_path())
                    updated = True
                if existing.extra_metadata is None:
                    existing.extra_metadata = metadata_payload
                    updated = True
                else:
                    for key, value in metadata_payload.items():
                        if existing.extra_metadata.get(key) != value:
                            existing.extra_metadata[key] = value
                            updated = True
                if updated:
                    created = True

        # Ensure at least one model is marked as the last used default
        last_model = get_last_used_model(session=db_session)
        if last_model is None:
            first_model = (
                db_session.query(ModelConfiguration)
                .filter(ModelConfiguration.is_active.is_(True))
                .order_by(ModelConfiguration.id)
                .first()
            )
            if first_model is not None:
                set_last_used_model(first_model.id, session=db_session)
                last_model = first_model

        # Store Gemini API key if missing (only when provided via environment variables)
        existing_gemini = get_api_key("gemini", session=db_session)
        if not existing_gemini:
            env_gemini_key = _load_gemini_api_key_from_env()
            if env_gemini_key:
                upsert_api_key("gemini", env_gemini_key, session=db_session)
                created = True
            else:
                logger.info(
                    "Gemini API key missing; configure %s or use the admin UI to add one.",
                    GEMINI_ENV_VAR_NAME,
                )

        # Create default model configurations for remote providers when API keys are available
        # Gemini
        gemini_key = get_api_key("gemini", session=db_session) or _load_gemini_api_key_from_env()
        if gemini_key:
            existing_gemini_model = (
                db_session.query(ModelConfiguration)
                .filter(
                    ModelConfiguration.provider == "gemini",
                    ModelConfiguration.api_identifier == "gemini-flash-latest"
                )
                .first()
            )
            if existing_gemini_model is None:
                db_session.add(
                    ModelConfiguration(
                        name="Google Gemini Flash Latest",
                        provider="gemini",
                        api_identifier="gemini-flash-latest",
                        extra_metadata={
                            "description": "Google Gemini Flash Latest model via API",
                            "max_output_tokens": 8192,
                            "context_window": 1048576,
                        }
                    )
                )
                created = True

        # OpenAI
        openai_key = get_api_key("openai", session=db_session) or os.getenv("OPENAI_API_KEY")
        if openai_key:
            existing_openai_model = (
                db_session.query(ModelConfiguration)
                .filter(
                    ModelConfiguration.provider == "openai",
                    ModelConfiguration.api_identifier == "gpt-4o-mini"
                )
                .first()
            )
            if existing_openai_model is None:
                db_session.add(
                    ModelConfiguration(
                        name="OpenAI GPT-4o Mini",
                        provider="openai",
                        api_identifier="gpt-4o-mini",
                        extra_metadata={
                            "description": "OpenAI GPT-4o Mini model via API",
                            "max_output_tokens": 16384,
                            "context_window": 128000,
                        }
                    )
                )
                created = True

        # Anthropic
        anthropic_key = get_api_key("anthropic", session=db_session) or os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            existing_anthropic_model = (
                db_session.query(ModelConfiguration)
                .filter(
                    ModelConfiguration.provider == "anthropic",
                    ModelConfiguration.api_identifier == "claude-3-5-sonnet-20241022"
                )
                .first()
            )
            if existing_anthropic_model is None:
                db_session.add(
                    ModelConfiguration(
                        name="Anthropic Claude 3.5 Sonnet",
                        provider="anthropic",
                        api_identifier="claude-3-5-sonnet-20241022",
                        extra_metadata={
                            "description": "Anthropic Claude 3.5 Sonnet model via API",
                            "max_output_tokens": 8192,
                            "context_window": 200000,
                        }
                    )
                )
                created = True

        if created:
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        if should_close:
            db_session.close()


def get_model_configurations(
    provider: Optional[str] = None,
    session: Optional[Session] = None,
) -> List[ModelConfiguration]:
    """Return active model configurations, optionally filtered by provider."""

    db_session, should_close = _resolve_session(session)

    try:
        query = db_session.query(ModelConfiguration).filter(
            ModelConfiguration.is_active.is_(True)
        )
        if provider:
            query = query.filter(ModelConfiguration.provider == provider)
        return query.order_by(ModelConfiguration.name).all()
    finally:
        if should_close:
            db_session.close()


def get_model_configuration_by_id(
    model_id: int,
    session: Optional[Session] = None,
) -> Optional[ModelConfiguration]:
    """Fetch a model configuration by primary key."""

    db_session, should_close = _resolve_session(session)

    try:
        return db_session.query(ModelConfiguration).filter_by(id=model_id).first()
    finally:
        if should_close:
            db_session.close()


def set_last_used_model(model_id: int, session: Optional[Session] = None) -> None:
    """Persist the identifier of the last selected model."""

    db_session, should_close = _resolve_session(session)

    try:
        setting = db_session.query(AppSetting).filter_by(key="last_used_model_id").first()
        if setting is None:
            setting = AppSetting(key="last_used_model_id", value=str(model_id))
            db_session.add(setting)
        else:
            setting.value = str(model_id)
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        if should_close:
            db_session.close()


def get_last_used_model(session: Optional[Session] = None) -> Optional[ModelConfiguration]:
    """Retrieve the last model selected by the user."""

    db_session, should_close = _resolve_session(session)

    try:
        setting = db_session.query(AppSetting).filter_by(key="last_used_model_id").first()
        if setting is None or not setting.value:
            return None
        try:
            model_id = int(setting.value)
        except (TypeError, ValueError):
            return None
        return db_session.query(ModelConfiguration).filter_by(id=model_id).first()
    finally:
        if should_close:
            db_session.close()


def upsert_api_key(provider: str, api_key: str, session: Optional[Session] = None) -> None:
    """Create or update an API credential for a provider."""

    db_session, should_close = _resolve_session(session)

    try:
        record = db_session.query(APICredential).filter_by(provider=provider).first()
        if record is None:
            record = APICredential(provider=provider, api_key=api_key)
            db_session.add(record)
        else:
            record.api_key = api_key
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        if should_close:
            db_session.close()


def get_api_key(provider: str, session: Optional[Session] = None) -> Optional[str]:
    """Fetch the stored API key for a provider if available."""

    db_session, should_close = _resolve_session(session)

    try:
        record = db_session.query(APICredential).filter_by(provider=provider).first()
        return record.api_key if record else None
    finally:
        if should_close:
            db_session.close()
def save_company_info(company_info: "CompanyInfo", session: Optional[Session] = None) -> Company:
    """
    Save company information to the database.
    
    Args:
        company_info: CompanyInfo Pydantic model with company data
        session: Optional existing database session
        
    Returns:
        Company database record
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        # Check if company already exists
        existing = session.query(Company).filter_by(
            company_name=company_info.company_name
        ).first()
        
        if existing:
            # Update existing record
            for key, value in company_info.model_dump().items():
                if key in ["products", "competitors", "key_personas"]:
                    setattr(existing, key, value if value else [])
                else:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            result = existing
        else:
            # Create new record
            company_dict = company_info.model_dump()
            # Handle list fields
            company_dict["products"] = company_dict.get("products", [])
            company_dict["competitors"] = company_dict.get("competitors", [])
            company_dict["key_personas"] = company_dict.get("key_personas", [])
            
            new_company = Company(**company_dict)
            session.add(new_company)
            result = new_company
        
        session.commit()
        return result
        
    except Exception as e:
        session.rollback()
        raise Exception(f"Failed to save company info: {str(e)}")
    finally:
        if should_close:
            session.close()


def get_company(name: str, session: Optional[Session] = None) -> Optional[Company]:
    """
    Retrieve company information from database.
    
    Args:
        name: Company name
        session: Optional existing database session
        
    Returns:
        Company record if found, None otherwise
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        return session.query(Company).filter_by(company_name=name).first()
    finally:
        if should_close:
            session.close()


def list_companies(session: Optional[Session] = None) -> List[Company]:
    """
    List all companies in the database.
    
    Args:
        session: Optional existing database session
        
    Returns:
        List of Company records
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        return session.query(Company).order_by(Company.company_name).all()
    finally:
        if should_close:
            session.close()


def save_search_history(
    query: str,
    company_name: Optional[str] = None,
    search_provider: Optional[str] = None,
    num_results: Optional[int] = None,
    execution_time_ms: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    raw_results: Optional[List[dict]] = None,
    results_summary: Optional[str] = None,
    session: Optional[Session] = None
) -> SearchHistory:
    """
    Save search operation to history.
    
    Args:
        query: Search query string
        company_name: Related company name if applicable
        search_provider: Search provider used ('tavily' or 'serper')
        num_results: Number of results returned
        execution_time_ms: Execution time in milliseconds
        success: Whether search was successful
        error_message: Error message if failed
        raw_results: Optional list of raw search result payloads
        results_summary: Optional human-readable summary of results
        session: Optional existing database session
        
    Returns:
        SearchHistory database record
    """
    if session is None:
        session = get_session()
        should_close = True
    else:
        should_close = False
    
    try:
        search_record = SearchHistory(
            query=query,
            company_name=company_name,
            search_provider=search_provider,
            num_results=num_results,
            execution_time_ms=execution_time_ms,
            success=1 if success else 0,
            error_message=error_message,
            raw_results=raw_results,
            results_summary=results_summary
        )
        session.add(search_record)
        session.commit()
        return search_record
    except Exception as e:
        session.rollback()
        raise Exception(f"Failed to save search history: {str(e)}")
    finally:
        if should_close:
            session.close()



