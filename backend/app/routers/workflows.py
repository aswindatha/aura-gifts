from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import WorkflowTemplate, User
from app.schemas import (
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
    WorkflowTemplateResponse,
)

router = APIRouter(prefix="/api/workflow-templates", tags=["Workflow Templates"])


async def _require_shopkeeper_or_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [1, 3]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shopkeepers or admins can manage workflow templates"
        )
    return current_user


@router.get("", response_model=List[WorkflowTemplateResponse])
async def list_workflow_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active workflow templates for the shop."""
    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.is_active == True).order_by(WorkflowTemplate.name)
    )
    return result.scalars().all()


@router.post("", response_model=WorkflowTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_template(
    payload: WorkflowTemplateCreate,
    current_user: User = Depends(_require_shopkeeper_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new reusable workflow template."""
    template = WorkflowTemplate(
        name=payload.name,
        created_by=current_user.id,
        steps=[step.model_dump() for step in payload.steps]
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/{template_id}", response_model=WorkflowTemplateResponse)
async def get_workflow_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a single workflow template."""
    result = await db.execute(
        select(WorkflowTemplate).where(
            WorkflowTemplate.id == template_id,
            WorkflowTemplate.is_active == True
        )
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")
    return template


@router.patch("/{template_id}", response_model=WorkflowTemplateResponse)
async def update_workflow_template(
    template_id: UUID,
    payload: WorkflowTemplateUpdate,
    current_user: User = Depends(_require_shopkeeper_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update a workflow template (name, steps, or active status)."""
    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    if payload.name is not None:
        template.name = payload.name
    if payload.steps is not None:
        template.steps = [step.model_dump() for step in payload.steps]
    if payload.is_active is not None:
        template.is_active = payload.is_active

    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow_template(
    template_id: UUID,
    current_user: User = Depends(_require_shopkeeper_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft-delete a workflow template by marking it inactive."""
    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    )
    template = result.scalars().first()
    if not template:
        raise HTTPException(status_code=404, detail="Workflow template not found")

    template.is_active = False
    db.add(template)
    await db.commit()
    return None
