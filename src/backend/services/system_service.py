"""
System manifest parsing and deployment service.

Handles YAML parsing, validation, agent naming, and deployment orchestration.
"""
import yaml
import re
import logging
from typing import Dict, List, Tuple, Optional

from models import SystemManifest, SystemAgentConfig, SystemPermissions
from database import db
from db_models import ScheduleCreate

logger = logging.getLogger(__name__)


def parse_manifest(yaml_str: str) -> SystemManifest:
    """
    Parse YAML string into SystemManifest.

    Raises:
        ValueError: If YAML is invalid or missing required fields
    """
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error: {str(e)}")

    if not data:
        raise ValueError("Empty manifest")

    if not isinstance(data, dict):
        raise ValueError("Manifest must be a YAML object")

    # Validate required fields
    if "name" not in data:
        raise ValueError("Missing required field: name")
    if "agents" not in data or not data["agents"]:
        raise ValueError("Missing required field: agents (must have at least 1)")

    # Parse agents
    agents = {}
    for agent_name, agent_config in data["agents"].items():
        if not isinstance(agent_config, dict):
            raise ValueError(f"Agent '{agent_name}' config must be an object")
        if "template" not in agent_config:
            raise ValueError(f"Agent '{agent_name}' missing required field: template")

        agents[agent_name] = SystemAgentConfig(
            template=agent_config["template"],
            resources=agent_config.get("resources"),
            folders=agent_config.get("folders"),
            schedules=agent_config.get("schedules")
        )

    # Parse permissions
    permissions = None
    if "permissions" in data:
        perm_data = data["permissions"]
        permissions = SystemPermissions(
            preset=perm_data.get("preset"),
            explicit=perm_data.get("explicit")
        )

    return SystemManifest(
        name=data["name"],
        description=data.get("description"),
        prompt=data.get("prompt"),
        agents=agents,
        permissions=permissions
    )


def validate_manifest(manifest: SystemManifest) -> List[str]:
    """
    Validate manifest and return warnings.

    Returns:
        List of warning messages (empty if all valid)

    Raises:
        ValueError: If validation fails
    """
    warnings = []

    # Validate system name
    if not re.match(r'^[a-z0-9][a-z0-9-]{0,48}[a-z0-9]$|^[a-z0-9]{1,2}$', manifest.name):
        raise ValueError(
            f"Invalid system name '{manifest.name}': must be 1-50 chars, "
            "lowercase alphanumeric and hyphens, start/end with alphanumeric"
        )

    # Validate agent names
    for agent_name in manifest.agents.keys():
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$', agent_name):
            raise ValueError(
                f"Invalid agent name '{agent_name}': must be lowercase alphanumeric and hyphens"
            )

    # Validate template references
    for agent_name, config in manifest.agents.items():
        template = config.template
        if not (template.startswith("github:") or template.startswith("local:")):
            raise ValueError(
                f"Agent '{agent_name}': template must start with 'github:' or 'local:'"
            )

    # Validate permissions
    if manifest.permissions:
        if manifest.permissions.preset and manifest.permissions.explicit:
            raise ValueError("Cannot specify both preset and explicit permissions")

        if manifest.permissions.preset:
            valid_presets = ["full-mesh", "orchestrator-workers", "none"]
            if manifest.permissions.preset not in valid_presets:
                raise ValueError(
                    f"Invalid permission preset '{manifest.permissions.preset}': "
                    f"must be one of {valid_presets}"
                )

            # Warn if orchestrator-workers but no orchestrator agent
            if manifest.permissions.preset == "orchestrator-workers":
                if "orchestrator" not in manifest.agents:
                    warnings.append(
                        "Permission preset 'orchestrator-workers' specified but no "
                        "'orchestrator' agent defined. No permissions will be granted."
                    )

        if manifest.permissions.explicit:
            agent_names = set(manifest.agents.keys())
            for source, targets in manifest.permissions.explicit.items():
                if source not in agent_names:
                    raise ValueError(f"Unknown agent in permissions: {source}")
                for target in targets:
                    if target not in agent_names:
                        raise ValueError(f"Unknown agent in permissions: {target}")

    # Validate schedules (if any)
    for agent_name, config in manifest.agents.items():
        if config.schedules:
            for i, schedule in enumerate(config.schedules):
                if "name" not in schedule:
                    raise ValueError(f"Agent '{agent_name}' schedule {i}: missing 'name'")
                if "cron" not in schedule:
                    raise ValueError(f"Agent '{agent_name}' schedule {i}: missing 'cron'")
                if "message" not in schedule:
                    raise ValueError(f"Agent '{agent_name}' schedule {i}: missing 'message'")

    return warnings


def agent_exists(name: str) -> bool:
    """Check if an agent with this name already exists."""
    # Check database for ownership record
    owner = db.get_agent_owner(name)
    return owner is not None


def get_next_agent_name(base_name: str) -> str:
    """
    Find next available name with _N suffix if base name exists.

    Examples:
        "my-agent" -> "my-agent" (if doesn't exist)
        "my-agent" -> "my-agent_2" (if my-agent exists)
        "my-agent" -> "my-agent_3" (if my-agent and my-agent_2 exist)
    """
    if not agent_exists(base_name):
        return base_name

    n = 2
    while agent_exists(f"{base_name}_{n}"):
        n += 1
    return f"{base_name}_{n}"


def resolve_agent_names(
    system_name: str,
    agents: Dict[str, SystemAgentConfig]
) -> Tuple[Dict[str, str], List[str]]:
    """
    Resolve short agent names to final names, handling conflicts.

    Args:
        system_name: The system name prefix
        agents: Dict of short_name -> agent config

    Returns:
        Tuple of (name_mapping, warnings)
        - name_mapping: {short_name: final_name}
        - warnings: List of conflict warnings
    """
    name_mapping = {}
    warnings = []

    for short_name in agents.keys():
        base_name = f"{system_name}-{short_name}"
        final_name = get_next_agent_name(base_name)
        name_mapping[short_name] = final_name

        if final_name != base_name:
            warnings.append(
                f"Agent '{base_name}' already exists, will create '{final_name}'"
            )

    return name_mapping, warnings


# ============================================================================
# Phase 2: Configuration Functions
# ============================================================================

async def configure_permissions(
    agent_names: Dict[str, str],  # {short_name: final_name}
    permissions: Optional[SystemPermissions],
    created_by: str
) -> int:
    """
    Apply permission configuration based on preset or explicit rules.

    Args:
        agent_names: Mapping of short names to final agent names
        permissions: Permission configuration from manifest
        created_by: Username for audit trail

    Returns:
        Number of permissions configured
    """
    if not permissions:
        return 0

    final_names = list(agent_names.values())
    permissions_count = 0

    if permissions.preset == "full-mesh":
        # Every agent can communicate with every other agent
        for source in final_names:
            targets = [t for t in final_names if t != source]
            if targets:
                db.set_agent_permissions(source, targets, created_by)
                permissions_count += len(targets)
                logger.info(f"Granted {source} permissions to call: {targets}")

    elif permissions.preset == "orchestrator-workers":
        # Only orchestrator can call workers
        # Workers cannot call anyone (clear their default permissions)
        orchestrator_short = "orchestrator"
        if orchestrator_short in agent_names:
            orchestrator = agent_names[orchestrator_short]
            workers = [n for n in final_names if n != orchestrator]
            if workers:
                # Set orchestrator permissions to call all workers
                db.set_agent_permissions(orchestrator, workers, created_by)
                permissions_count = len(workers)
                logger.info(f"Granted {orchestrator} permissions to call workers: {workers}")

                # Clear worker permissions (set to empty list = clear all)
                for worker in workers:
                    db.set_agent_permissions(worker, [], created_by)
                    logger.info(f"Cleared permissions for worker {worker}")

    elif permissions.preset == "none":
        # No permissions - clear all default permissions for all system agents
        for agent in final_names:
            db.set_agent_permissions(agent, [], created_by)
        logger.info(f"Cleared all permissions for {len(final_names)} agents (preset: none)")

    elif permissions.explicit:
        # Apply explicit permission matrix
        # First, clear permissions for all system agents not in explicit config
        for short_name, final_name in agent_names.items():
            if short_name not in permissions.explicit:
                db.set_agent_permissions(final_name, [], created_by)
                logger.info(f"Cleared default permissions for {final_name} (not in explicit config)")

        # Then set explicit permissions
        for source_short, target_shorts in permissions.explicit.items():
            source = agent_names.get(source_short)
            if not source:
                logger.warning(f"Unknown source agent in permissions: {source_short}")
                continue
            targets = [agent_names[t] for t in target_shorts if t in agent_names]
            # set_agent_permissions does a full replacement
            db.set_agent_permissions(source, targets, created_by)
            permissions_count += len(targets)
            if targets:
                logger.info(f"Granted {source} permissions to call: {targets}")
            else:
                logger.info(f"Cleared permissions for {source} (empty target list)")

    return permissions_count


def configure_folders(
    agent_names: Dict[str, str],  # {short_name: final_name}
    agents_config: Dict[str, SystemAgentConfig]
) -> int:
    """
    Configure shared folder settings for all agents.

    Args:
        agent_names: Mapping of short names to final agent names
        agents_config: Agent configurations from manifest

    Returns:
        Number of folder configs created
    """
    folders_configured = 0

    for short_name, config in agents_config.items():
        final_name = agent_names.get(short_name)
        if not final_name:
            continue

        if config.folders:
            expose = config.folders.get("expose", False)
            consume = config.folders.get("consume", False)

            db.upsert_shared_folder_config(
                agent_name=final_name,
                expose_enabled=expose,
                consume_enabled=consume
            )
            folders_configured += 1
            logger.info(f"Configured folders for {final_name}: expose={expose}, consume={consume}")

    return folders_configured


def create_schedules(
    agent_names: Dict[str, str],  # {short_name: final_name}
    agents_config: Dict[str, SystemAgentConfig],
    owner_username: str
) -> int:
    """
    Create schedules for all agents.

    Args:
        agent_names: Mapping of short names to final agent names
        agents_config: Agent configurations from manifest
        owner_username: Username for schedule ownership

    Returns:
        Number of schedules created
    """
    schedules_count = 0

    for short_name, config in agents_config.items():
        final_name = agent_names.get(short_name)
        if not final_name or not config.schedules:
            continue

        for schedule_data in config.schedules:
            schedule_create = ScheduleCreate(
                name=schedule_data["name"],
                cron_expression=schedule_data["cron"],
                message=schedule_data["message"],
                enabled=schedule_data.get("enabled", True),
                timezone=schedule_data.get("timezone", "UTC"),
                description=schedule_data.get("description")
            )

            # Create schedule in database
            schedule = db.create_schedule(
                agent_name=final_name,
                username=owner_username,
                schedule_data=schedule_create
            )

            if schedule:
                schedules_count += 1
                logger.info(f"Created schedule '{schedule_data['name']}' for {final_name}")
                # Dedicated scheduler syncs from database automatically
            else:
                logger.warning(f"Failed to create schedule '{schedule_data['name']}' for {final_name}")

    return schedules_count


async def start_all_agents(agent_names: List[str]) -> Dict[str, str]:
    """
    Start all created agents.

    This triggers Trinity meta-prompt injection with the updated trinity_prompt.

    Args:
        agent_names: List of agent names to start

    Returns:
        Dict of {agent_name: status} where status is 'started' or error message
    """
    from routers.agents import start_agent_internal

    results = {}
    for agent_name in agent_names:
        try:
            result = await start_agent_internal(agent_name)
            results[agent_name] = "started"
            logger.info(f"Started agent '{agent_name}': {result}")
        except Exception as e:
            results[agent_name] = f"error: {str(e)}"
            logger.warning(f"Failed to start agent '{agent_name}': {e}")
            # Continue starting other agents even if one fails

    return results


def export_manifest(system_name: str, agents: List[Dict]) -> str:
    """
    Export a system as a YAML manifest.

    Args:
        system_name: The system prefix
        agents: List of agent dictionaries from Docker

    Returns:
        YAML string representing the system configuration
    """
    # Extract short names (remove system prefix)
    agent_configs = {}
    for agent in agents:
        full_name = agent['name']
        # Remove system prefix and hyphen
        short_name = full_name[len(system_name) + 1:]

        # Get agent details
        config = {
            "template": agent.get('template', 'local:business-assistant')
        }

        # Get resources (if available from labels)
        if agent.get('resources'):
            config["resources"] = agent['resources']

        # Get folders config from database
        try:
            folder_config = db.get_agent_folder_config(full_name)
            if folder_config and (folder_config['expose_enabled'] or folder_config['consume_enabled']):
                config["folders"] = {
                    "expose": bool(folder_config['expose_enabled']),
                    "consume": bool(folder_config['consume_enabled'])
                }
        except Exception as e:
            logger.warning(f"Failed to get folder config for {full_name}: {e}")

        # Get schedules from database
        try:
            schedules = db.list_agent_schedules(full_name)
            if schedules:
                config["schedules"] = [
                    {
                        "name": s.name,
                        "cron": s.cron_expression,
                        "message": s.message,
                        "enabled": bool(s.enabled),
                        "timezone": s.timezone
                    }
                    for s in schedules
                ]
        except Exception as e:
            logger.warning(f"Failed to get schedules for {full_name}: {e}")

        agent_configs[short_name] = config

    # Build manifest dict
    manifest_dict = {
        "name": system_name,
        "description": f"Exported system configuration for {system_name}",
        "agents": agent_configs
    }

    # Get permissions (try to detect preset pattern)
    try:
        # Check first agent's permissions to infer pattern
        if agents:
            first_agent = agents[0]['name']
            perms = db.get_agent_permissions(first_agent)

            if perms:
                # Try to detect full-mesh pattern
                all_agents_names = [a['name'] for a in agents]
                permitted_targets = [p["target_agent"] for p in perms]

                # Full-mesh: agent can call all other agents
                expected_targets = [n for n in all_agents_names if n != first_agent]
                if set(permitted_targets) == set(expected_targets):
                    # Verify other agents also have full-mesh
                    is_full_mesh = True
                    for agent in agents:
                        agent_perms = db.get_agent_permissions(agent['name'])
                        expected = [n for n in all_agents_names if n != agent['name']]
                        actual = [p["target_agent"] for p in agent_perms]
                        if set(actual) != set(expected):
                            is_full_mesh = False
                            break

                    if is_full_mesh:
                        manifest_dict["permissions"] = {"preset": "full-mesh"}
                    else:
                        # Export explicit permissions
                        explicit_perms = {}
                        for agent in agents:
                            short_name = agent['name'][len(system_name) + 1:]
                            agent_perms = db.get_agent_permissions(agent['name'])
                            targets = [
                                p["target_agent"][len(system_name) + 1:]
                                for p in agent_perms
                            ]
                            if targets:
                                explicit_perms[short_name] = targets

                        if explicit_perms:
                            manifest_dict["permissions"] = {"explicit": explicit_perms}
                else:
                    # Export explicit permissions
                    explicit_perms = {}
                    for agent in agents:
                        short_name = agent['name'][len(system_name) + 1:]
                        agent_perms = db.get_agent_permissions(agent['name'])
                        targets = [
                            p["target_agent"][len(system_name) + 1:]
                            for p in agent_perms
                            if p["target_agent"].startswith(f"{system_name}-")
                        ]
                        if targets:
                            explicit_perms[short_name] = targets

                    if explicit_perms:
                        manifest_dict["permissions"] = {"explicit": explicit_perms}

    except Exception as e:
        logger.warning(f"Failed to export permissions for system {system_name}: {e}")

    # Get global trinity_prompt if it exists
    try:
        trinity_prompt = db.get_setting_value("trinity_prompt")
        if trinity_prompt:
            manifest_dict["prompt"] = trinity_prompt
    except Exception as e:
        logger.warning(f"Failed to get trinity_prompt: {e}")

    # Convert to YAML
    yaml_output = yaml.dump(manifest_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return yaml_output
