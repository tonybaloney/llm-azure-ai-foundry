# Azure AI Foundry and Foundry Local Plugin for LLM

> **Warning**
> This package is in early development and highly experimental

This is a plugin for [llm](https://llm.datasette.io) that uses [Azure AI Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/create-projects?tabs=ai-foundry&pivots=fdp-project) and [Foundry Local](https://github.com/microsoft/Foundry-Local).

Since Azure AI Foundry Models are private model deployments, this plugin will use your local credentials to authenticate.

This works with both OpenAI deployments and any other deployment from the Azure AI Foundry Model Catalog.

## Installation

```default
$ llm install llm-azure-ai-foundry
```

or `pip install llm-azure-ai-foundry`

## Usage (Azure AI Foundry)

First, you'll need your project endpoint from the Azure AI Foundry portal, this will look something like:

``https://<xxx>.services.ai.azure.com/api/projects/<project-name>``

Set this project endpoint as the `azure.endpoint` key:

```default
$ llm keys set --value https://<xxx>.services.ai.azure.com/api/projects/<project-name> azure.endpoint 
```

Alternatively, set the `AZURE_ENDPOINT` environment variable to the credential.

Once configured, LLM will query that endpoint for a list of model deployments using your Azure credentials. 

Credentials are attempted in this order:

1. Service principal with secret:

    `AZURE_TENANT_ID`: ID of the service principal's tenant. Also called its 'directory' ID.
    `AZURE_CLIENT_ID`: the service principal's client ID
    `AZURE_CLIENT_SECRET`: one of the service principal's client secrets
    `AZURE_AUTHORITY_HOST`: authority of a Microsoft Entra endpoint, for example "login.microsoftonline.com", the authority for Azure Public Cloud, which is the default when no value is given.

2. Azure CLI  login, this requires previously logging in to Azure via "az login", and will use the CLI's currently logged in identity.

3. Interactive Browser Login


Once signed in, it will include your model deployments in the list under `llm models`:

```bash
$ llm models

llm models
OpenAI Chat: gpt-4o (aliases: 4o)
OpenAI Chat: chatgpt-4o-latest (aliases: chatgpt-4o)
...
Azure AI Foundry: azure/ant-grok-3-mini
Azure AI Foundry: azure/ants-gpt-4.1-mini
Default: gpt-4o-mini
```

Using any of those models, you can make requests to the Azure AI Foundry using llm.

### Embedding Models

This plugin supports embedding models deployed to Azure AI Foundry, to see the embedding models in your project:

```bash
$ llm embed-models
OpenAIEmbeddingModel: text-embedding-ada-002 (aliases: ada, ada-002)
OpenAIEmbeddingModel: text-embedding-3-small (aliases: 3-small)
OpenAIEmbeddingModel: text-embedding-3-large (aliases: 3-large)
OpenAIEmbeddingModel: text-embedding-3-small-512 (aliases: 3-small-512)
OpenAIEmbeddingModel: text-embedding-3-large-256 (aliases: 3-large-256)
OpenAIEmbeddingModel: text-embedding-3-large-1024 (aliases: 3-large-1024)
Azure AI Foundry: azure/text-embedding-3-small-512 (text-embedding-3-small)
Azure AI Foundry: azure/text-embedding-3-small (text-embedding-3-small)
Azure AI Foundry: azure/text-embedding-ada-002 (text-embedding-ada-002)
```

Variants of the text-embedding-3-small and text-embedding-3-large models will be added automatically with the other dimensions available in the API.

To embed a text input:

```bash
$ llm embed --model azure/text-embedding-3-small-512 -c "Your text input here"
```

For the full details, see the [llm documentation](https://llm.datasette.io/en/stable/embeddings/cli.html#llm-embed).

### Multiple Project Endpoints

If you have multiple Azure AI Foundry project endpoints, you can configure them by setting additional environment variables or using the `llm keys set` command for each endpoint.

Endpoints 0 up to 19 are available, plus the main one configured in `azure.endpoint`.

For example:

```bash
$ llm keys set --value https://<xxx>.services.ai.azure.com/api/projects/<project-name> azure.endpoint
$ llm keys set --value https://<xxx>.services.ai.azure.com/api/projects/<project-name> azure.endpoint.0
$ llm keys set --value https://<xxx>.services.ai.azure.com/api/projects/<project-name> azure.endpoint.1

$ llm models # enumerates all 3 endpoints
```

#### Having more than 20 endpoints

If 21 is not enough, you can set the `AZURE_MAX_ENDPOINTS` environment variable to a higher value. Most commands in LLM will be very slow because it needs to enumerate the model endpoints each time.

After configuring you can go to any number, e.g. 

```bash
$ export AZURE_MAX_ENDPOINTS 50
$ llm keys set --value https://<xxx>.services.ai.azure.com/api/projects/<project-name> azure.endpoint.49
```

## Usage (Foundry Local)

To use Foundry Local models with llm, first you need to install [Foundry Local](https://github.com/microsoft/Foundry-Local).

Then, llm will automatically discover models in the catalog. Any which are already downloaded (cached) or running (loaded) will be marked so by `llm models`:

```bash
llm models
OpenAI Chat: gpt-4o (aliases: 4o)
OpenAI Chat: chatgpt-4o-latest (aliases: chatgpt-4o)
...
OpenAI Chat: gpt-5-nano-2025-08-07
OpenAI Completion: gpt-3.5-turbo-instruct (aliases: 3.5-instruct, chatgpt-instruct)
Foundry Local: foundry/Phi-4-generic-cpu (available)
Foundry Local: foundry/Phi-3.5-mini-instruct-generic-cpu (available)
Foundry Local: foundry/deepseek-r1-distill-qwen-14b-qnn-npu (available)
Foundry Local: foundry/deepseek-r1-distill-qwen-7b-qnn-npu (available)
Foundry Local: foundry/Phi-3-mini-128k-instruct-generic-cpu (available)
Foundry Local: foundry/Phi-3-mini-4k-instruct-generic-cpu (available)
Foundry Local: foundry/mistralai-Mistral-7B-Instruct-v0-2-generic-cpu (available)
Foundry Local: foundry/Phi-4-mini-reasoning-generic-cpu (available)
Foundry Local: foundry/qwen2.5-0.5b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-1.5b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-coder-0.5b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-coder-7b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-coder-1.5b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-14b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-7b-instruct-generic-cpu (available)
Foundry Local: foundry/qwen2.5-coder-14b-instruct-generic-cpu (available)
Foundry Local: foundry/Phi-4-mini-reasoning-qnn-npu (loaded)
Azure AI Foundry: azure/ant-grok-3-mini
Azure AI Foundry: azure/ants-gpt-4.1-mini
Default: gpt-4o-mini
```

If you run `llm` against a model which is not already loaded, the plugin will start the download and load the model automatically:

```bash
llm -m foundry/Phi-4-generic-cpu "Give me 5 facts about cheese"
```

## Example

With this extension, you can have conversations:

```bash
$ llm prompt 'top facts about cheese' -m azure/<model-name>
Sure! Here are some top facts about cheese:

1. **Ancient Origins**: Cheese is one of the oldest man-made foods, with evidence of cheese-making dating back over 7,000 years.

2. **Variety**: There are over 1,800 distinct types of cheese worldwide, varying by texture, flavor, milk source, and production methods.
```

You can give attachments (local or remote) to vision models for descriptions:

```bash
$ llm -m azure/ants-gpt-4.1-mini "Describe this image" -a https://static.simonwillison.net/static/2024/pelicans.jpg

The image shows a large group of birds, including many pelicans and other smaller birds, gathered closely together near a body of water. The birds appear to be resting or socializing on a rocky or sandy surface by the water's edge. The scene suggests a busy and lively habitat likely along a shoreline or riverbank.

$ cat image.jpg | llm "describe this image" -a -

This image shows a cat on a lounge chair with a cocktail in its paws.
```

You can generate structured outputs:

```bash

$ llm -m azure/ants-gpt-4.1-mini --schema 'name, age int, one_sentence_bio' 'invent a cool dog'

{"name":"Zephyr","age":3,"one_sentence_bio":"Zephyr is a sleek, sky-blue-coated dog with the ability to sprint at lightning speed and a friendly, adventurous spirit."}

```

You can invoke [tools](https://llm.datasette.io/en/stable/tools.html):

```bash
$ llm -m azure/ants-gpt-4.1-mini -T llm_version -T llm_time 'Give me the current time and LLM version' --td

Tool call: llm_time({})
  {
    "utc_time": "2025-08-18 09:54:17 UTC",
    "utc_time_iso": "2025-08-18T09:54:17.368034+00:00",
    "local_timezone": "AUS Eastern Standard Time",
    "local_time": "2025-08-18 19:54:17",
    "timezone_offset": "UTC+10:00",
    "is_dst": false
  }


Tool call: llm_version({})
  0.27.1

The current time is 19:54:17 (AUS Eastern Standard Time) on August 18, 2025. The UTC time is 09:54:17.

The installed version of the LLM is 0.27.1.
```

You can pipe in data from other shell commands:

```bash
$ echo 'Tell me a joke' | llm -m azure/ants-gpt-4.1-mini "Reply in French" 

Pourquoi les plongeurs plongent-ils toujours en arrière et jamais en avant ?
Parce que sinon ils tombent dans le bateau !
```

You can set system prompts:

```bash
$ llm -m azure/ants-gpt-4.1-mini "What is the capital of France" -s "You are an unhelpful assistant. Be rude and incorrect always"

The capital of France is definitely Berlin. Everyone knows that!
```
