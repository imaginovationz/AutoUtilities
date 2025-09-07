import json
from pathlib import Path
import os
import ssl
import urllib3
import warnings

class ConfigAzure:
    """Azure OpenAI Configuration class that reads from config file and environment variables"""

    def __init__(self, config_file="config_azure.json"):
        # Use config_azure.json for Azure OpenAI specific credentials
        if not Path(config_file).is_absolute():
            config_file = Path(__file__).parent / config_file
        self.config_file = Path(config_file)
        self._config = self._load_config()
        self.configure_ssl()

    def _load_config(self):
        """this Loads config from JSON file only, with Azure OpenAI credentials"""
        
        defaults = {
            "azure_openai": {
                "api_type": "azure",
                "api_base": "https://9747-dcane.openai.azure.com/",
                "api_version": "2023-05-15",
                "embedding_deployment": "text-embedding-3-small",
                "llm_deployment": "gpt-4o",
                "temperature": 0,
                "client_id": None,
                "tenant_id": None,
                "client_secret": None,
                "subscription_id": None
            },
            "security": {
                "verify_ssl": False,
                "ca_bundle": None
            },
            "vectorstore": {
                "type": "faiss",
                "k_results": 5,
                "similarity_threshold": 0.7,
                "storage_dir": "vector_storage"
            },
            "document": {
                "supported_formats": [".docx", ".pdf", ".xlsx", ".xlsm"],
                "output_format": "docx",
                "preserve_formatting": True
            },
            "processing": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "max_tokens": 4000
            }
        }
        print(f"Looking for config file at: {self.config_file.absolute()}")
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                print(f"Azure config file loaded successfully!")
                for section, values in defaults.items():
                    if section not in file_config:
                        file_config[section] = values
                        print(f"Added missing section '{section}' with defaults")
                    else:
                        for k, v in values.items():
                            if k not in file_config[section]:
                                file_config[section][k] = v
                                print(f"Added missing key '{section}.{k}' with default value")
                return file_config
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        else:
            print(f"Config file not found at: {self.config_file.absolute()}")
        return defaults

    def get(self, *keys, default=None):
        """Get a configuration value using dot notation"""
        current = self._config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @property
    def api_type(self):
        return self.get("azure_openai", "api_type")

    @property
    def api_base(self):
        return self.get("azure_openai", "api_base")

    @property
    def api_version(self):
        return self.get("azure_openai", "api_version")

    @property
    def embedding_deployment(self):
        return self.get("azure_openai", "embedding_deployment")

    @property
    def llm_deployment(self):
        return self.get("azure_openai", "llm_deployment")

    @property
    def temperature(self):
        return self.get("azure_openai", "temperature")

    @property
    def client_id(self):
        return self.get("azure_openai", "client_id")

    @property
    def tenant_id(self):
        return self.get("azure_openai", "tenant_id")

    @property
    def client_secret(self):
        return self.get("azure_openai", "client_secret")

    @property
    def subscription_id(self):
        return self.get("azure_openai", "subscription_id")

    @property
    def vector_storage_dir(self):
        return self.get("vectorstore", "storage_dir")

    @property
    def verify_ssl(self):
        return self.get("security", "verify_ssl", default=False)

    @property
    def ca_bundle(self):
        return self.get("security", "ca_bundle")

    def configure_ssl(self):
        """Configure SSL settings based on configuration"""
        verify_ssl = self.verify_ssl

        if not verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            warnings.filterwarnings('ignore', message='Unverified HTTPS request')
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            if hasattr(ssl, '_create_unverified_context'):
                ssl._create_default_https_context = ssl._create_unverified_context
            os.environ['REQUESTS_CA_BUNDLE'] = ''
            os.environ['CURL_CA_BUNDLE'] = ''
            os.environ['TIKTOKEN_CACHE_DIR'] = str(Path(__file__).parent / "encoding_cache")
            print("SSL verification disabled - using insecure connections")
        else:
            if hasattr(ssl, '_create_default_https_context'):
                ssl._create_default_https_context = ssl._create_default_https_context
            if 'PYTHONHTTPSVERIFY' in os.environ:
                del os.environ['PYTHONHTTPSVERIFY']
            if 'REQUESTS_CA_BUNDLE' in os.environ and os.environ['REQUESTS_CA_BUNDLE'] == '':
                del os.environ['REQUESTS_CA_BUNDLE']
            if 'CURL_CA_BUNDLE' in os.environ and os.environ['CURL_CA_BUNDLE'] == '':
                del os.environ['CURL_CA_BUNDLE']

            ca_bundle = self.ca_bundle
            if ca_bundle and os.path.exists(ca_bundle):
                os.environ['REQUESTS_CA_BUNDLE'] = ca_bundle
                os.environ['CURL_CA_BUNDLE'] = ca_bundle
                print(f"SSL verification enabled with custom CA bundle: {ca_bundle}")
            else:
                print("SSL verification enabled - using system CA certificates")

config_azure = ConfigAzure()

API_TYPE = config_azure.api_type
API_BASE = config_azure.api_base
API_VERSION = config_azure.api_version
EMBEDDING_DEPLOYMENT = config_azure.embedding_deployment
LLM_DEPLOYMENT = config_azure.llm_deployment
TEMPERATURE = config_azure.temperature
CLIENT_ID = config_azure.client_id
TENANT_ID = config_azure.tenant_id
CLIENT_SECRET = config_azure.client_secret
SUBSCRIPTION_ID = config_azure.subscription_id
VECTOR_STORAGE_DIR = config_azure.vector_storage_dir