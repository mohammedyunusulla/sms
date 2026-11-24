"""
List every API route with its access rule, and fail if a staff route has no permission.

    python check_route_permissions.py            # summary + routes still missing a permission
    python check_route_permissions.py --all      # every route with its rule

A route must either declare `permission=` in @login_required (the role tick box it needs), or be marked
`self_service=True` (it's about the caller: sign-in, a student's / parent's own pages, bus staff's own GPS ...).
Routes only Super Admin can use, and public routes (no login), are listed but don't need a permission.
Exit code 1 if any staff route has neither - so a new route can't slip through unprotected.
"""
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def access_rule(view):
    """Walk the decorator chain (functools.wraps sets __wrapped__) to find login_required's rule."""
    seen = 0
    while view is not None and seen < 20:
        rule = getattr(view, 'access_rule', None)
        if rule is not None:
            return rule
        view = getattr(view, '__wrapped__', None)
        seen += 1
    return None


def main():
    from app import create_app
    app = create_app()
    show_all = '--all' in sys.argv
    rows, missing = [], []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if not rule.rule.startswith('/api/'):
            continue
        methods = ','.join(sorted(m for m in rule.methods if m not in ('HEAD', 'OPTIONS')))
        access = access_rule(app.view_functions.get(rule.endpoint))
        if access is None:
            kind = 'public (no login)'
        elif access['permissions']:
            kind = 'permission: ' + ' | '.join(access['permissions'])
        elif access.get('full_access_only'):
            kind = 'institution admin only'
        elif access['self_service']:
            kind = 'self-service: ' + ','.join(access['roles'] or ['any signed-in user'])
        elif access['roles'] and set(access['roles']) <= {'SUPER_ADMIN'}:
            kind = 'super admin only'
        else:
            kind = 'MISSING permission (roles: ' + ','.join(access['roles'] or ['any']) + ')'
            missing.append(f"{methods:12} {rule.rule}  [{','.join(access['roles'] or ['any'])}]")
        rows.append((rule.rule, methods, kind))

    if show_all:
        for path, methods, kind in rows:
            print(f"{methods:12} {path:75} {kind}")
        print()
    counts = {}
    for _, _, kind in rows:
        key = kind.split(':')[0].split(' (')[0]
        counts[key] = counts.get(key, 0) + 1
    print(f"{len(rows)} API routes: " + ', '.join(f"{v} {k}" for k, v in sorted(counts.items())))
    if missing:
        print(f"\n{len(missing)} staff routes have no permission yet:")
        for line in missing:
            print("  " + line)
        return 1
    print("Every staff route declares a permission.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
