"""Additive portable verbs; no MCP surface or activation side effects."""

import json

from sparkforge_aws.distribution import service
from sparkforge_aws.workspace import portable


def register(sub, context_sub):
    distribution = sub.add_parser("distribution", help="Inspeção e inicialização portátil offline.")
    actions = distribution.add_subparsers(dest="distribution_action", required=True)
    for action in ("inspect", "init", "status", "doctor"):
        parser = actions.add_parser(action, help=f"Portable distribution {action}.")
        parser.add_argument("--root", default=".")
    workspace = sub.add_parser(
        "workspace", help="Workspace virtual declarado e descoberta limitada."
    )
    actions = workspace.add_subparsers(dest="workspace_action", required=True)
    for action in ("discover", "init", "add", "status"):
        parser = actions.add_parser(action, help=f"Portable workspace {action}.")
        parser.add_argument("--root", default=".")
        if action in ("init", "add"):
            parser.add_argument("--name")
        if action == "add":
            parser.add_argument("repository")
        if action == "discover":
            parser.add_argument("--max-depth", type=int, default=4)
            parser.add_argument("--max-directories", type=int, default=2000)
    parser = context_sub.add_parser(
        "resolve", help="Resolve locality repo/workspace/target sem ler fontes."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--scope", choices=["repo", "workspace", "target"])
    parser.add_argument("--target")
    parser.add_argument("--impact", choices=["direct", "transitive", "all"], default="all")


def dispatch(args):
    if args.command == "distribution":
        action = args.distribution_action
        call = {
            "inspect": service.inspect_distribution,
            "init": service.init_project,
            "status": service.status,
            "doctor": service.doctor,
        }[action]
        payload = call(args.root)
    elif args.command == "workspace":
        action = args.workspace_action
        if action == "discover":
            payload = portable.discover(
                args.root, max_depth=args.max_depth, max_directories=args.max_directories
            )
        elif action == "init":
            payload = portable.init_workspace(args.root, name=args.name)
        elif action == "add":
            payload = portable.add_repository(args.root, args.repository, name=args.name)
        else:
            payload = portable.workspace_status(args.root)
    else:
        payload = service.resolve_context(
            args.root, scope=args.scope, target=args.target, impact=args.impact
        )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if (
        args.command == "distribution"
        and args.distribution_action == "doctor"
        and payload.get("status") == "blocked"
    ):
        return 2
    return 0
