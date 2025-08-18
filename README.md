# Azure AI Foundry Plugin for LLM

> **Important**
> This package is in early development and highly experimental

This is a plugin for [llm](https://llm.datasette.io) that uses [Azure AI Foundry Models](https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/create-projects?tabs=ai-foundry&pivots=fdp-project).

Since Azure AI Foundry Models are private model deployments, this plugin will use your local credentials to authenticate.

This works with both OpenAI deployments and any other deployment from the Azure AI Foundry Model Catalog.

## Installation

```default
$ llm install llm-azure-ai-foundry
```

or `pip install llm-azure-ai-foundry`

## Usage

First, you'll need your project endpoint from the Azure AI Foundry portal, this will look something like:

``https://<xxx>.services.ai.azure.com/api/projects/<project-name>``

Set this project endpoint as the `azure.endpoint` key:

```default
$ llm keys set --value https://<xxx>.services.ai.azure.com/api/projects/<project-name> azure.endpoint 
```

Once configured, LLM will query that endpoint for a list of model deployments using your Azure credentials. 
Azure credentials will first attempt to use your Azure CLI credential (`az login`). If that is not set, it will open a browser with a signin request.

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

## Example

```default
$ llm prompt 'top facts about cheese' -m azure/<model-name>
Sure! Here are some top facts about cheese:

1. **Ancient Origins**: Cheese is one of the oldest man-made foods, with evidence of cheese-making dating back over 7,000 years.

2. **Variety**: There are over 1,800 distinct types of cheese worldwide, varying by texture, flavor, milk source, and production methods.
```
