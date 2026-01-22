"""
Data loading utilities for DTC prompts and capability definitions.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load application configuration from YAML file.

    Args:
        config_path: Path to config file. Defaults to config.yaml in project root.

    Returns:
        Configuration dictionary
    """
    if config_path is None:
        config_path = get_project_root() / "config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_capabilities(yaml_path: Optional[str] = None) -> Dict[str, Any]:
    """Load the AI Agent CPT capability definitions.

    Args:
        yaml_path: Path to ai_agent_cpt.yaml. Defaults to data/ai_agent_cpt.yaml

    Returns:
        Capability definitions dictionary
    """
    if yaml_path is None:
        yaml_path = get_project_root() / "data" / "ai_agent_cpt.yaml"
    else:
        yaml_path = Path(yaml_path)

    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    return data


def load_prompt(step: int) -> str:
    """Load a DTC prompt template by step number.

    Args:
        step: Step number (0-3)

    Returns:
        Prompt template content as string
    """
    prompt_files = {
        0: "step_0_use_case_suitability.md",
        1: "step_1_business_requirements.md",
        2: "step_2_agent_design.md",
        3: "step_3_capability_mapping.md",
    }

    if step not in prompt_files:
        raise ValueError(f"Invalid step number: {step}. Must be 0-3.")

    prompt_path = get_project_root() / "prompts" / prompt_files[step]

    with open(prompt_path, 'r') as f:
        return f.read()


def get_capability_by_id(capabilities: Dict[str, Any], cap_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific capability by its ID (e.g., 'PK.OB').

    Args:
        capabilities: Full capabilities dictionary from load_capabilities()
        cap_id: Capability ID like 'PK.OB', 'CG.PL', etc.

    Returns:
        Capability definition dict or None if not found
    """
    parts = cap_id.split('.')
    if len(parts) != 2:
        return None

    category, cap_code = parts

    try:
        category_data = capabilities['capabilities'].get(category, {})
        caps = category_data.get('capabilities', {})
        return caps.get(cap_id)
    except (KeyError, TypeError):
        return None


def get_all_capabilities_flat(capabilities: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Get all capabilities as a flat dictionary keyed by ID.

    Args:
        capabilities: Full capabilities dictionary from load_capabilities()

    Returns:
        Flat dict mapping capability IDs to their definitions
    """
    flat = {}

    for category_id, category_data in capabilities.get('capabilities', {}).items():
        for cap_id, cap_def in category_data.get('capabilities', {}).items():
            flat[cap_id] = {
                'category_id': category_id,
                'category_name': category_data.get('name', ''),
                **cap_def
            }

    return flat


def get_agent_types(capabilities: Dict[str, Any]) -> Dict[str, str]:
    """Extract agent type definitions from capabilities YAML.

    Args:
        capabilities: Full capabilities dictionary from load_capabilities()

    Returns:
        Dict mapping type codes (T0-T4) to descriptions
    """
    return capabilities.get('header', {}).get('category_types', {})
