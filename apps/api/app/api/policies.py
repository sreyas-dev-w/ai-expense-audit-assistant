"""Policy document ingestion and policy store search endpoints.

Routing-only: handlers parse/validate and delegate to the policy services
(``docs/backend/api-design.md``).
"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.dependencies import (
    get_policy_document_service,
    get_policy_rag_service,
)
from app.schemas.policy import (
    PolicyDocumentSummary,
    PolicyIngestResult,
    PolicySearchRequest,
    PolicySearchResponse,
)
from app.services.policy_document_service import (
    InvalidPdfError,
    PolicyDocumentIngestionError,
    PolicyDocumentService,
)
from app.services.rag_service import PolicyRagService, PolicyRetrievalError

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post(
    "/documents",
    response_model=PolicyIngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a policy PDF into the vector store",
)
async def upload_policy_document(
    file: UploadFile = File(..., description="Policy PDF to chunk and embed"),
    force: bool = Form(
        default=False,
        description="Re-embed an already-ingested policy (same file hash)",
    ),
    service: PolicyDocumentService = Depends(get_policy_document_service),
) -> PolicyIngestResult:
    content = await file.read()
    try:
        return await service.ingest_pdf(
            filename=file.filename or "policy.pdf",
            content=content,
            force=force,
        )
    except InvalidPdfError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except PolicyDocumentIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get(
    "/documents",
    response_model=list[PolicyDocumentSummary],
    summary="List ingested policy documents",
)
async def list_policy_documents(
    limit: int = 100,
    offset: int = 0,
    service: PolicyDocumentService = Depends(get_policy_document_service),
) -> list[PolicyDocumentSummary]:
    return await service.list_documents(limit=limit, offset=offset)


@router.get(
    "/documents/{policy_id}",
    response_model=PolicyDocumentSummary,
    summary="Get a single ingested policy document",
)
async def get_policy_document(
    policy_id: int,
    service: PolicyDocumentService = Depends(get_policy_document_service),
) -> PolicyDocumentSummary:
    document = await service.get_document(policy_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy document {policy_id} not found",
        )
    return document


@router.delete(
    "/documents/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a policy document and its chunks",
)
async def delete_policy_document(
    policy_id: int,
    service: PolicyDocumentService = Depends(get_policy_document_service),
) -> None:
    deleted = await service.delete_document(policy_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy document {policy_id} not found",
        )


@router.post(
    "/search",
    response_model=PolicySearchResponse,
    summary="Search the policy vector store",
)
async def search_policies(
    request: PolicySearchRequest,
    service: PolicyRagService = Depends(get_policy_rag_service),
) -> PolicySearchResponse:
    try:
        results = await service.search(
            query=request.query,
            top_k=request.top_k,
            policy_id=request.policy_id,
            similarity_threshold=request.similarity_threshold,
        )
    except PolicyRetrievalError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return PolicySearchResponse(
        query=request.query,
        top_k=request.top_k,
        count=len(results),
        results=results,
    )