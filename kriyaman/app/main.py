from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.routes import router as api_router
from app.api.schemas import ErrorDetail, ErrorResponse
from domain.errors import (
    BudgetExceededError,
    KriyamanError,
    PolicyViolationError,
    ProviderError,
    ResourceNotFoundError,
    ValidationError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks if needed
    yield
    # Shutdown tasks if needed


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application."""
    app = FastAPI(
        title="Kriyamaan Agentic RAG API",
        version="1.0.0",
        description="Backend-first Agentic RAG application with strict evidence gates and monotonic execution budgets.",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------------------
    # Global Exception Handlers returning standard error envelope
    # ---------------------------------------------------------------------------

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    run_id=getattr(exc, "resource_id", None),
                )
            ).model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                )
            ).model_dump(),
        )

    @app.exception_handler(BudgetExceededError)
    async def budget_exceeded_handler(request: Request, exc: BudgetExceededError):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                )
            ).model_dump(),
        )

    @app.exception_handler(PolicyViolationError)
    async def policy_violation_handler(request: Request, exc: PolicyViolationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                )
            ).model_dump(),
        )

    @app.exception_handler(ProviderError)
    async def provider_error_handler(request: Request, exc: ProviderError):
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                )
            ).model_dump(),
        )

    @app.exception_handler(KriyamanError)
    async def domain_error_handler(request: Request, exc: KriyamanError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                )
            ).model_dump(),
        )

    # Mount API v1 router
    app.include_router(api_router)

    return app


app = create_app()

