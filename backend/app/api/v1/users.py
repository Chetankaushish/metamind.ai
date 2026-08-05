import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.core.security import hash_password
from app.models.models import User, Role, Permission, UserRole, RolePermission, AuditLog
from app.schemas.schemas import (
    UserResponse,
    UserCreate,
    UserUpdate,
    RoleResponse,
    PermissionResponse,
    UserRoleUpdateRequest
)
from app.services.rbac_service import get_user_permissions, seed_rbac_data

router = APIRouter(tags=["RBAC & User Management"])

async def _ensure_rbac_seeded(db: AsyncSession):
    stmt = select(Role)
    res = await db.execute(stmt)
    if not res.scalars().first():
        await seed_rbac_data(db)

@router.get("/users", response_model=List[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    await _ensure_rbac_seeded(db)
    stmt = select(User).order_by(User.created_at.desc())
    res = await db.execute(stmt)
    users = res.scalars().all()

    response_list = []
    for u in users:
        perms = await get_user_permissions(u.id, db)
        
        # Get role names
        stmt_roles = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == u.id)
        res_roles = await db.execute(stmt_roles)
        roles = list(res_roles.scalars().all())
        if not roles and u.role:
            roles = [u.role]

        response_list.append(UserResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role or "Viewer",
            company_name=u.company_name,
            plan=u.plan or "Enterprise",
            is_active=u.is_active,
            roles=roles,
            permissions=perms
        ))
    return response_list

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    await _ensure_rbac_seeded(db)
    # Check duplicate email
    stmt = select(User).where(User.email == user_in.email)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    hashed_pw = hash_password(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        role=user_in.role,
        company_name=user_in.company_name,
        plan=user_in.plan,
        is_active=True
    )
    db.add(new_user)
    await db.flush()

    # Assign role
    stmt_role = select(Role).where(Role.name == user_in.role)
    res_role = await db.execute(stmt_role)
    role_obj = res_role.scalar_one_or_none()
    if role_obj:
        db.add(UserRole(user_id=new_user.id, role_id=role_obj.id))

    # Audit log
    audit = AuditLog(
        user_id="usr_admin",
        action="create_user",
        new_value=f"Created user {user_in.email} with role {user_in.role}",
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(new_user)

    perms = await get_user_permissions(new_user.id, db)
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role,
        company_name=new_user.company_name,
        plan=new_user.plan,
        is_active=new_user.is_active,
        roles=[new_user.role],
        permissions=perms
    )

@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_in: UserUpdate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_val = f"Role: {user.role}, Name: {user.full_name}, Active: {user.is_active}"

    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.email is not None:
        user.email = user_in.email
    if user_in.company_name is not None:
        user.company_name = user_in.company_name
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.role is not None:
        user.role = user_in.role
        # Update user_roles table
        stmt_role = select(Role).where(Role.name == user_in.role)
        res_role = await db.execute(stmt_role)
        role_obj = res_role.scalar_one_or_none()
        if role_obj:
            # Delete old roles
            stmt_del = select(UserRole).where(UserRole.user_id == user_id)
            res_del = await db.execute(stmt_del)
            for ur in res_del.scalars().all():
                await db.delete(ur)
            db.add(UserRole(user_id=user.id, role_id=role_obj.id))

    new_val = f"Role: {user.role}, Name: {user.full_name}, Active: {user.is_active}"

    audit = AuditLog(
        user_id="usr_admin",
        action="update_user",
        old_value=old_val,
        new_value=new_val,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(user)

    perms = await get_user_permissions(user.id, db)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        company_name=user.company_name,
        plan=user.plan,
        is_active=user.is_active,
        roles=[user.role],
        permissions=perms
    )

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    email = user.email
    await db.delete(user)

    audit = AuditLog(
        user_id="usr_admin",
        action="delete_user",
        old_value=email,
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    return None

@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(db: AsyncSession = Depends(get_db)):
    await _ensure_rbac_seeded(db)
    stmt = select(Role)
    res = await db.execute(stmt)
    roles = res.scalars().all()

    out = []
    for r in roles:
        stmt_p = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == r.id)
        )
        res_p = await db.execute(stmt_p)
        perms = list(res_p.scalars().all())
        out.append(RoleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            permissions=perms
        ))
    return out

@router.patch("/users/{user_id}/roles", response_model=UserResponse)
async def update_user_roles(user_id: str, req: UserRoleUpdateRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Clear existing roles
    stmt_del = select(UserRole).where(UserRole.user_id == user_id)
    res_del = await db.execute(stmt_del)
    for ur in res_del.scalars().all():
        await db.delete(ur)

    assigned_role_names = []
    for rname in req.roles:
        stmt_role = select(Role).where(Role.name == rname)
        res_role = await db.execute(stmt_role)
        role_obj = res_role.scalar_one_or_none()
        if role_obj:
            db.add(UserRole(user_id=user.id, role_id=role_obj.id))
            assigned_role_names.append(role_obj.name)

    if assigned_role_names:
        user.role = assigned_role_names[0]

    audit = AuditLog(
        user_id="usr_admin",
        action="update_user_roles",
        new_value=f"Roles updated to {assigned_role_names}",
        result="SUCCESS"
    )
    db.add(audit)

    await db.commit()
    await db.refresh(user)

    perms = await get_user_permissions(user.id, db)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        company_name=user.company_name,
        plan=user.plan,
        is_active=user.is_active,
        roles=assigned_role_names,
        permissions=perms
    )

@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(db: AsyncSession = Depends(get_db)):
    await _ensure_rbac_seeded(db)
    stmt = select(Permission)
    res = await db.execute(stmt)
    perms = res.scalars().all()
    return perms
