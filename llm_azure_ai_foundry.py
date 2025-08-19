import logging
from enum import StrEnum

import llm
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from foundry_local import FoundryLocalManager
from foundry_local.api import FoundryModelInfo
from foundry_local.service import assert_foundry_installed
from llm.default_plugins.openai_models import AsyncChat, Chat
from llm.errors import NeedsKeyException

logging.basicConfig(level=logging.ERROR)

# LLM will call the register_models hook twice for each invocation
# Since we dynamically register models, cache the answer to avoid
# this extra overhead.
_cached_models = {}


@llm.hookimpl
def register_models(register):
    def cached_register(alias, sync_model, async_model=None):
        _cached_models[alias] = (sync_model, async_model)
        register(sync_model, async_model)

    if _cached_models:
        for _, (sync_model, async_model) in _cached_models.items():
            register(sync_model, async_model)
        return

    try:
        assert_foundry_installed()
        FOUNDRY_LOCAL_INSTALLED = True
    except RuntimeError:
        FOUNDRY_LOCAL_INSTALLED = False

    if FOUNDRY_LOCAL_INSTALLED:
        mgr = FoundryLocalManager()

        def register_model(model: FoundryModelInfo, status: FoundryModelStatus):
            if model.task == "chat-completion":
                cached_register(
                    model.alias,
                    FoundryLocalModel(
                        model_id=model.id, alias=model.alias, manager=mgr, status=status
                    ),
                )

        catalog_models = mgr.list_catalog_models()
        # Group by alias
        cached_models = mgr.list_cached_models()
        loaded_models = mgr.list_loaded_models()

        for model in catalog_models:
            if model not in loaded_models and model not in cached_models:
                register_model(model, FoundryModelStatus.Available)

        for model in cached_models:
            if model not in loaded_models:
                register_model(model, FoundryModelStatus.Cached)

        for model in loaded_models:
            register_model(model, FoundryModelStatus.Loaded)

    endpoint = llm.get_key("azure.endpoint")
    if not endpoint:
        raise NeedsKeyException(
            "Configure the azure.endpoint to the URL of your project endpoint, e.g. https://<xxx>.services.ai.azure.com/api/projects/<project-name>"
        )  # noqa: E501

    with DefaultAzureCredential(exclude_interactive_browser_credential=False) as credential:
        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            for deployment in project_client.deployments.list():
                if (
                    "chat_completion" in deployment["capabilities"]
                    and deployment["capabilities"]["chat_completion"]
                ):
                    cached_register(
                        deployment["name"],
                        AzureAIFoundryModel(
                            deployment_name=deployment["name"],
                            client=project_client.get_openai_client(
                                api_version="2025-04-01-preview"
                            ),
                        ),
                        AsyncAzureAIFoundryModel(
                            deployment_name=deployment["name"],
                            client=project_client.get_openai_client(
                                api_version="2025-04-01-preview"
                            ),
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


class FoundryModelStatus(StrEnum):
    Available = "available"
    Cached = "cached"
    Loaded = "loaded"


class FoundryLocalModel(Chat):
    needs_key = "foundry"  # set in constructor

    def __init__(
        self, model_id: str, alias: str, manager: FoundryLocalManager, status: FoundryModelStatus
    ):
        self.model_id = "foundry/" + model_id
        self.foundry_id = model_id
        self.model_name = alias
        self.status = status
        super().__init__(
            model_id=self.model_id,
            model_name=self.foundry_id,
            vision=True,
            reasoning=True,
            supports_schema=True,
            supports_tools=True,
            api_base=manager.endpoint,
            key=manager.api_key,
        )
        self.manager = manager

    def __str__(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return f"Foundry Local: {self.model_id} ({self.status})"

    def execute(self, *args, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        if self.status == FoundryModelStatus.Available:
            logging.warning("Model not cached, downloading from model registry")
            self.manager.download_model(self.foundry_id)
            self.status = FoundryModelStatus.Cached
        if self.status == FoundryModelStatus.Cached:
            logging.warning("Model not loaded, loading from cache")
            self.manager.load_model(self.foundry_id)
            self.status = FoundryModelStatus.Loaded
        return super().execute(*args, **kwargs)


# TODO: Async local, although only the openai SDK is async, the Foundry Local API isn't
