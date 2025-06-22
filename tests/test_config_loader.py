import pytest
import os
import yaml
from unittest.mock import patch

from mpla.config.loader import load_config, Config

@pytest.fixture
def mock_config_file(tmp_path):
    """Creates a temporary config file for testing."""
    config_content = {
        'agent': {
            'deployment_orchestrator': {'provider': 'gemini'},
            'knowledge_base': {'provider': 'sqlite', 'db_path': '/test.db'},
            'prompt_enhancer': {'provider': 'rule_based'},
            'evaluation_engine': {'provider': 'basic'},
            'learning_refinement_module': {'provider': 'rule_based'},
            'reporting_module': {'provider': 'mock'}
        },
        'api_keys': {
            'google_api_key': '${TEST_GOOGLE_KEY}',
            'openai_api_key': '${TEST_OPENAI_KEY}'
        }
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config_content, f)
    return str(config_path)

def test_load_config_success(mock_config_file):
    """Tests successful loading and validation of a config file."""
    with patch.dict(os.environ, {'TEST_GOOGLE_KEY': 'test_google_value', 'TEST_OPENAI_KEY': 'test_openai_value'}):
        config = load_config(path=mock_config_file)
        
        assert isinstance(config, Config)
        assert config.agent.deployment_orchestrator.provider == 'gemini'
        assert config.agent.knowledge_base.db_path == '/test.db'
        assert config.api_keys.google_api_key == 'test_google_value'
        assert config.api_keys.openai_api_key == 'test_openai_value'

def test_load_config_missing_env_var(mock_config_file):
    """Tests that loading works but API key is None if env var is missing."""
    with patch.dict(os.environ, {}, clear=True):
        config = load_config(path=mock_config_file)
        assert config.api_keys.google_api_key is None
        assert config.api_keys.openai_api_key is None

def test_load_config_invalid_provider(tmp_path):
    """Tests that a config with an invalid provider raises a validation error."""
    invalid_config_content = {
        'agent': {
            'deployment_orchestrator': {'provider': 'invalid_provider'},
            'knowledge_base': {'provider': 'sqlite', 'db_path': '/test.db'},
            'prompt_enhancer': {'provider': 'rule_based'},
            'evaluation_engine': {'provider': 'basic'},
            'learning_refinement_module': {'provider': 'rule_based'},
            'reporting_module': {'provider': 'mock'}
        },
        'api_keys': {}
    }
    config_path = tmp_path / "invalid_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(invalid_config_content, f)
    
    with pytest.raises(Exception): # Pydantic's ValidationError
        load_config(path=str(config_path)) 