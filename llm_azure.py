from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

import logging

import llm
from llm.errors import NeedsKeyException
from llm.default_plugins.openai_models import AsyncChat, Chat

logging.basicConfig(level=logging.WARNING)


@llm.hookimpl
def register_models(register):

    endpoint = llm.get_key("azure.endpoint")
    if not endpoint:
        raise NeedsKeyException("Configure the azure.endpoint to the URL of your project endpoint, e.g. https://<xxx>.services.ai.azure.com/api/projects/<project-name>")

    with DefaultAzureCredential(exclude_interactive_browser_credential=False) as credential:
        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            for deployment in project_client.deployments.list():
                register(
                    AzureAIFoundryModel(
                        deployment_name=deployment["name"],
                        client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                    ),
                    AsyncAzureAIFoundryModel(
                        deployment_name=deployment["name"],
                        client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                    ),
                )


class AzureAIFoundryModel(Chat):
    needs_key = None

    def __init__(self, deployment_name: str, client):
        self._client = client
        self.model_name = deployment_name
        self.model_id = "azure/" + deployment_name
        super().__init__(
            model_id=self.model_id,
            model_name=self.model_name,
            # Turn on everything, if it doesn't work handle later
            vision=True,
            reasoning=True,
            supports_schema=True,
            supports_tools=True,
        )

    def __str__(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return f"Azure AI Foundry: {self.model_id}"

    def get_client(self, key, *, async_=False):
        return self._client


class AsyncAzureAIFoundryModel(AsyncChat):
    needs_key = None

    def __init__(self, deployment_name: str, client):
        self._client = client
        self.model_name = deployment_name
        self.model_id = "azure/" + deployment_name
        super().__init__(
            model_id=self.model_id,
            model_name=self.model_name,
            # Turn on everything, if it doesn't work handle later
            vision=True,
            reasoning=True,
            supports_schema=True,
            supports_tools=True,
        )

    def __str__(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return f"Azure AI Foundry: {self.model_id}"

    def get_client(self, key, *, async_=False):
        return self._client
