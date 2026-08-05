from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import Role, Permission, RolePermission, User, UserRole, AuditLog
from app.core.security import hash_password

PERMISSIONS_LIST = [
    ("view_dashboard", "View main marketing analytics dashboard"),
    ("view_reports", "View executive and operational reports"),
    ("generate_reports", "Generate and export PDF/Excel/CSV reports"),
    ("manage_campaigns", "Create and modify Meta campaigns"),
    ("pause_campaigns", "Pause active Meta campaigns"),
    ("resume_campaigns", "Resume paused Meta campaigns"),
    ("edit_budgets", "Update campaign daily and lifetime budgets"),
    ("run_meta_sync", "Trigger Meta Marketing API data sync"),
    ("manage_users", "Create, edit, and delete organization users"),
    ("manage_settings", "Update workspace and company settings"),
    ("manage_api_keys", "Manage Meta API tokens and credentials"),
    ("view_audit_logs", "Access system security and operational audit logs"),
]

ROLE_PERMISSIONS_MAP = {
    "Owner": [p[0] for p in PERMISSIONS_LIST],
    "Admin": [p[0] for p in PERMISSIONS_LIST],
    "Manager": [
        "view_dashboard", "view_reports", "generate_reports",
        "manage_campaigns", "pause_campaigns", "resume_campaigns",
        "edit_budgets", "run_meta_sync", "view_audit_logs"
    ],
    "Analyst": [
        "view_dashboard", "view_reports", "generate_reports", "view_audit_logs"
    ],
    "Viewer": [
        "view_dashboard", "view_reports"
    ]
}

async def seed_rbac_data(db: AsyncSession):
    """Seed default permissions, roles, role_permissions, and admin user."""
    # 1. Permissions
    perm_objs = {}
    for perm_name, desc in PERMISSIONS_LIST:
        stmt = select(Permission).where(Permission.name == perm_name)
        res = await db.execute(stmt)
        p_obj = res.scalar_one_or_none()
        if not p_obj:
            p_obj = Permission(name=perm_name, description=desc)
            db.add(p_obj)
            await db.flush()
        perm_objs[perm_name] = p_obj.id

    # 2. Roles & RolePermissions
    role_objs = {}
    for role_name, perms in ROLE_PERMISSIONS_MAP.items():
        stmt = select(Role).where(Role.name == role_name)
        res = await db.execute(stmt)
        r_obj = res.scalar_one_or_none()
        if not r_obj:
            r_obj = Role(name=role_name, description=f"{role_name} enterprise system role")
            db.add(r_obj)
            await db.flush()
        role_objs[role_name] = r_obj.id

        # Bind Role Permissions
        for perm_name in perms:
            p_id = perm_objs.get(perm_name)
            if p_id:
                stmt_rp = select(RolePermission).where(
                    RolePermission.role_id == r_obj.id,
                    RolePermission.permission_id == p_id
                )
                res_rp = await db.execute(stmt_rp)
                if not res_rp.scalar_one_or_none():
                    db.add(RolePermission(role_id=r_obj.id, permission_id=p_id))

    # 3. Seed Default Admin User
    admin_email = "admin@volzad.com"
    stmt_usr = select(User).where(User.email == admin_email)
    res_usr = await db.execute(stmt_usr)
    admin_usr = res_usr.scalar_one_or_none()
    if not admin_usr:
        hashed_pw = hash_password("AdminSecret123!")
        admin_usr = User(
            id="usr_admin",
            email=admin_email,
            hashed_password=hashed_pw,
            full_name="Enterprise System Administrator",
            role="Owner",
            company_name="Volzad Tech and Service",
            plan="Enterprise",
            is_active=True
        )
        db.add(admin_usr)
        await db.flush()

        # Assign Owner role
        owner_role_id = role_objs.get("Owner")
        if owner_role_id:
            db.add(UserRole(user_id=admin_usr.id, role_id=owner_role_id))

    await db.commit()

async def get_user_permissions(user_id: str, db: AsyncSession) -> list[str]:
    """Retrieve all permission names for a specific user based on assigned roles."""
    stmt = (
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    res = await db.execute(stmt)
    perms = res.scalars().all()
    return list(set(perms))
