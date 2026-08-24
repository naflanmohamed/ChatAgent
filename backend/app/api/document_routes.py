from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, Document, DocumentChunk
from app.services.document_service import extract_text, chunk_text
from app.agents.embeddings import embed_documents
from app.core.errors import classify_ai_error

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("")
async def upload_document(
    conversation_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user["user_id"])
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    file_bytes = await file.read()

    try:
        text = extract_text(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=400, detail="No readable text found in this file.")

    # Create the Document record
    document = Document(user_id=current_user["user_id"], conversation_id=conversation_id, filename=file.filename)
    db.add(document)
    db.flush()  

    # this is where embedding happens
    try:
        vectors = embed_documents(chunks)
    except Exception as e:
        db.rollback()
        print(f"[document_routes] embedding failed: {e}")
        status_code, friendly_message = classify_ai_error(e)
        raise HTTPException(status_code=status_code, detail=friendly_message)

    # Pair each chunk with its vector
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        db.add(DocumentChunk(document_id=document.id, chunk_index=i, content=chunk, embedding=vector))

    db.commit()
    db.refresh(document)

    return {"id": document.id, "filename": document.filename, "chunk_count": len(chunks)}


@router.get("")
def list_documents(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = (
        db.query(Document)
        .filter(
            Document.user_id == current_user["user_id"],
            Document.conversation_id == conversation_id,
        )
        .order_by(Document.uploaded_at.desc())
        .all()
    )
    return [{"id": d.id, "filename": d.filename, "uploaded_at": d.uploaded_at} for d in docs]


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user["user_id"])
        .first()
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)  # cascades to its chunks, see the relationship in models.py
    db.commit()
    return {"status": "deleted"}
