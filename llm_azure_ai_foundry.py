import logging
import os
from enum import Enum
from typing import Generator, Iterable, Iterator, List, Optional, Union

import llm
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import Deployment
from azure.identity import (
    AzureCliCredential,
    ChainedTokenCredential,
    EnvironmentCredential,
    InteractiveBrowserCredential,
)
from foundry_local import FoundryLocalManager
from foundry_local.api import FoundryModelInfo
from foundry_local.service import assert_foundry_installed
from llm.default_plugins.openai_models import AsyncChat, Chat
from llm.models import EmbeddingModel

if os.environ.get("LLM_AZURE_VERBOSE"):
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.ERROR)

AZURE_MAX_ENDPOINTS = int(os.environ.get("AZURE_MAX_ENDPOINTS", 20))

# LLM will call the register_models hook twice for each invocation
# Since we dynamically register models, cache the answer to avoid
# this extra overhead.
_cached_models = {}
_cached_embedding_models = {}


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

    for suffix, project_client, deployment in get_deployments_from_config("chat_completion"):
        cached_register(
            deployment["name"],
            AzureAIFoundryModel(
                deployment_name=deployment["name"],
                model_name=deployment["modelName"],
                client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                suffix=suffix,
            ),
            AsyncAzureAIFoundryModel(
                deployment_name=deployment["name"],
                model_name=deployment["modelName"],
                client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                suffix=suffix,
            ),
        )


@llm.hookimpl
def register_embedding_models(register):
    def cached_register(alias, model):
        _cached_embedding_models[alias] = model
        register(model)

    if _cached_embedding_models:
        for _, model in _cached_embedding_models.items():
            register(model)
        return

    for suffix, project_client, deployment in get_deployments_from_config("embeddings"):
        if deployment["modelName"] == "text-embedding-3-small":
            cached_register(
                f"{deployment['name']}-512",
                AzureAIFoundryEmbeddingModel(
                    deployment_name=deployment["name"],
                    model_name=deployment["modelName"],
                    client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                    model_id=f"azure{suffix}/{deployment['name']}-512",
                    dimensions=512,
                ),
            )
        elif deployment["modelName"] == "text-embedding-3-large":
            cached_register(
                f"{deployment['name']}-256",
                AzureAIFoundryEmbeddingModel(
                    deployment_name=deployment["name"],
                    model_name=deployment["modelName"],
                    client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                    model_id=f"azure{suffix}/{deployment['name']}-256",
                    dimensions=256,
                ),
            )
            cached_register(
                f"{deployment['name']}-1024",
                AzureAIFoundryEmbeddingModel(
                    deployment_name=deployment["name"],
                    model_name=deployment["modelName"],
                    client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                    model_id=f"azure{suffix}/{deployment['name']}-1024",
                    dimensions=1024,
                ),
            )
        cached_register(
            deployment["name"],
            AzureAIFoundryEmbeddingModel(
                deployment_name=deployment["name"],
                model_name=deployment["modelName"],
                client=project_client.get_openai_client(api_version="2025-04-01-preview"),
                model_id=f"azure{suffix}/" + deployment["name"],
            ),
        )


def get_deployments_from_config(
    required_capability: str,
) -> Generator[tuple[str, AIProjectClient, Deployment], None, None]:
    base_endpoint = llm.get_key("azure.endpoint", env="AZURE_ENDPOINT")
    if not base_endpoint:
        return

    endpoints = [("", base_endpoint)]

    # Extra endpoints
    for i in range(AZURE_MAX_ENDPOINTS):
        # all keys
        all_keys = llm.load_keys()
        if os.environ.get(f"AZURE_ENDPOINT_{i}"):
            endpoints.append((f".{i}", os.environ[f"AZURE_ENDPOINT_{i}"]))
        elif f"azure.endpoint.{i}" in all_keys and all_keys[f"azure.endpoint.{i}"].strip():
            endpoints.append((f".{i}", all_keys[f"azure.endpoint.{i}"]))

    credential_chain = ChainedTokenCredential(
        EnvironmentCredential(), AzureCliCredential(), InteractiveBrowserCredential()
    )

    with credential_chain as credential:
        for suffix, endpoint in endpoints:
            logging.info(f"Checking Azure AI Foundry endpoint: {endpoint}")
            with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
                for deployment in project_client.deployments.list():
                    if (
                        required_capability in deployment["capabilities"]
                        and deployment["capabilities"][required_capability]
                    ):
                        yield suffix, project_client, deployment


class AzureAIFoundryModel(Chat):
    needs_key = None

    def __init__(self, deployment_name: str, model_name: str, client, suffix: str = ""):
        self._client = client
        self.model_name = deployment_name  # the azure deployment name
        self.actual_model_name = model_name  # the name of the actual model (e.g. gpt-4o)
        self.model_id = f"azure{suffix}/" + deployment_name
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
        return f"Azure AI Foundry: {self.model_id} ({self.actual_model_name})"

    def get_client(self, key, *, async_=False):
        return self._client


class AsyncAzureAIFoundryModel(AsyncChat):
    needs_key = None

    def __init__(self, deployment_name: str, model_name: str, client, suffix: str = ""):
        self._client = client
        self.model_name = deployment_name  # the azure deployment name
        self.actual_model_name = model_name  # the name of the actual model (e.g. gpt-4o)
        self.model_id = f"azure{suffix}/" + deployment_name
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
        return f"Azure AI Foundry: {self.model_id} ({self.actual_model_name})"

    def get_client(self, key, *, async_=False):
        return self._client


class AzureAIFoundryEmbeddingModel(EmbeddingModel):
    needs_key = None

    def __init__(
        self,
        deployment_name: str,
        model_name: str,
        client,
        model_id: str,
        dimensions: Optional[int] = None,
    ):
        self._client = client
        self.model_name = deployment_name  # the azure deployment name
        self.actual_model_name = model_name  # the name of the actual model (e.g. gpt-4o)
        self.model_id = model_id
        self.dimensions = dimensions

    def embed_batch(self, items: Iterable[Union[str, bytes]]) -> Iterator[List[float]]:
        kwargs = {
            "input": items,
            "model": self.model_name,
        }
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        results = self._client.embeddings.create(**kwargs).data
        return ([float(r) for r in result.embedding] for result in results)

    def __str__(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        return f"Azure AI Foundry: {self.model_id} ({self.actual_model_name})"


class FoundryModelStatus(Enum):
    Available = "available"
    Cached = "cached"
    Loaded = "loaded"

    def __str__(self):
        return self.value


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
