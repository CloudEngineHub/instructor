from __future__ import annotations
from typing import Any, Union, Literal, overload
from instructor.client import AsyncInstructor, Instructor
import instructor
from instructor.models import KnownModelName
from instructor.cache import BaseCache
import warnings

# Type alias for the return type
InstructorType = Union[Instructor, AsyncInstructor]


# List of supported providers
supported_providers = [
    "openai",
    "azure_openai",
    "anthropic",
    "google",
    "generative-ai",
    "vertexai",
    "mistral",
    "cohere",
    "perplexity",
    "groq",
    "writer",
    "bedrock",
    "cerebras",
    "fireworks",
    "ollama",
    "xai",
]


@overload
def from_provider(
    model: KnownModelName,
    async_client: Literal[True] = True,
    cache: BaseCache | None = None,  # noqa: ARG001
    **kwargs: Any,
) -> AsyncInstructor: ...


@overload
def from_provider(
    model: KnownModelName,
    async_client: Literal[False] = False,
    cache: BaseCache | None = None,  # noqa: ARG001
    **kwargs: Any,
) -> Instructor: ...


@overload
def from_provider(
    model: str,
    async_client: Literal[True] = True,
    cache: BaseCache | None = None,  # noqa: ARG001
    **kwargs: Any,
) -> AsyncInstructor: ...


@overload
def from_provider(
    model: str,
    async_client: Literal[False] = False,
    cache: BaseCache | None = None,  # noqa: ARG001
    **kwargs: Any,
) -> Instructor: ...


def from_provider(
    model: Union[str, KnownModelName],  # noqa: UP007
    async_client: bool = False,
    cache: BaseCache | None = None,
    mode: Union[instructor.Mode, None] = None,  # noqa: ARG001, UP007
    **kwargs: Any,
) -> Union[Instructor, AsyncInstructor]:  # noqa: UP007
    """Create an Instructor client from a model string.

    Args:
        model: String in format "provider/model-name"
              (e.g., "openai/gpt-4", "anthropic/claude-3-sonnet", "google/gemini-pro")
        async_client: Whether to return an async client
        cache: Optional cache adapter (e.g., ``AutoCache`` or ``RedisCache``)
               to enable transparent response caching. Automatically flows through
               **kwargs to all provider implementations.
        mode: Override the default mode for the provider. If not specified, uses the
              recommended default mode for each provider.
        **kwargs: Additional arguments passed to the provider client functions.
                 This includes the cache parameter and any provider-specific options.

    Returns:
        Instructor or AsyncInstructor instance

    Raises:
        ValueError: If provider is not supported or model string is invalid
        ImportError: If required package for provider is not installed

    Examples:
        >>> import instructor
        >>> from instructor.cache import AutoCache
        >>>
        >>> # Basic usage
        >>> client = instructor.from_provider("openai/gpt-4")
        >>> client = instructor.from_provider("anthropic/claude-3-sonnet")
        >>>
        >>> # With caching
        >>> cache = AutoCache(maxsize=1000)
        >>> client = instructor.from_provider("openai/gpt-4", cache=cache)
        >>>
        >>> # Async clients
        >>> async_client = instructor.from_provider("openai/gpt-4", async_client=True)
    """
    # Add cache to kwargs if provided so it flows through to provider functions
    if cache is not None:
        kwargs["cache"] = cache

    try:
        provider, model_name = model.split("/", 1)
    except ValueError:
        from instructor.exceptions import ConfigurationError

        raise ConfigurationError(
            'Model string must be in format "provider/model-name" '
            '(e.g. "openai/gpt-4" or "anthropic/claude-3-sonnet")'
        ) from None

    if provider == "openai":
        try:
            import openai
            from instructor import from_openai

            client = openai.AsyncOpenAI() if async_client else openai.OpenAI()
            return from_openai(
                client,
                model=model_name,
                mode=mode if mode else instructor.Mode.TOOLS,
                **kwargs,
            )
        except ImportError:
            from instructor.exceptions import ConfigurationError

            raise ConfigurationError(
                "The openai package is required to use the OpenAI provider. "
                "Install it with `pip install openai`."
            ) from None

    elif provider == "azure_openai":
        try:
            import os
            from openai import AzureOpenAI, AsyncAzureOpenAI
            from instructor import from_openai

            # Get required Azure OpenAI configuration from environment
            api_key = kwargs.pop("api_key", os.environ.get("AZURE_OPENAI_API_KEY"))
            azure_endpoint = kwargs.pop(
                "azure_endpoint", os.environ.get("AZURE_OPENAI_ENDPOINT")
            )
            api_version = kwargs.pop("api_version", "2024-02-01")

            if not api_key:
                from instructor.exceptions import ConfigurationError

                raise ConfigurationError(
                    "AZURE_OPENAI_API_KEY is not set. "
                    "Set it with `export AZURE_OPENAI_API_KEY=<your-api-key>` or pass it as kwarg api_key=<your-api-key>"
                )

            if not azure_endpoint:
                from instructor.exceptions import ConfigurationError

                raise ConfigurationError(
                    "AZURE_OPENAI_ENDPOINT is not set. "
                    "Set it with `export AZURE_OPENAI_ENDPOINT=<your-endpoint>` or pass it as kwarg azure_endpoint=<your-endpoint>"
                )

            client = (
                AsyncAzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=azure_endpoint,
                )
                if async_client
                else AzureOpenAI(
                    api_key=api_key,
                    api_version=api_version,
                    azure_endpoint=azure_endpoint,
                )
            )
            return from_openai(
                client,
                model=model_name,
                mode=mode if mode else instructor.Mode.TOOLS,
                **kwargs,
            )
        except ImportError:
            from instructor.exceptions import ConfigurationError

            raise ConfigurationError(
                "The openai package is required to use the Azure OpenAI provider. "
                "Install it with `pip install openai`."
            ) from None

    elif provider == "anthropic":
        try:
            import anthropic
            from instructor import from_anthropic

            client = (
                anthropic.AsyncAnthropic() if async_client else anthropic.Anthropic()
            )
            max_tokens = kwargs.pop("max_tokens", 4096)
            return from_anthropic(
                client,
                model=model_name,
                mode=mode if mode else instructor.Mode.ANTHROPIC_TOOLS,
                max_tokens=max_tokens,
                **kwargs,
            )
        except ImportError:
            import_err = ImportError(
                "The anthropic package is required to use the Anthropic provider. "
                "Install it with `pip install anthropic`."
            )
            raise import_err from None

    elif provider == "google":
        try:
            import google.genai as genai
            from instructor import from_genai
            import os

            # Remove vertexai from kwargs if present to avoid passing it twice
            vertexai_flag = kwargs.pop("vertexai", False)

            # Get API key from kwargs or environment
            api_key = kwargs.pop("api_key", os.environ.get("GOOGLE_API_KEY"))

            # Extract client-specific parameters
            client_kwargs = {}
            for key in [
                "debug_config",
                "http_options",
                "credentials",
                "project",
                "location",
            ]:
                if key in kwargs:
                    client_kwargs[key] = kwargs.pop(key)

            client = genai.Client(
                vertexai=vertexai_flag,
                api_key=api_key,
                **client_kwargs,
            )  # type: ignore
            if async_client:
                return from_genai(client, use_async=True, model=model_name, **kwargs)  # type: ignore
            else:
                return from_genai(client, model=model_name, **kwargs)  # type: ignore
        except ImportError:
            import_err = ImportError(
                "The google-genai package is required to use the Google provider. "
                "Install it with `pip install google-genai`."
            )
            raise import_err from None

    elif provider == "mistral":
        try:
            from mistralai import Mistral
            from instructor import from_mistral
            import os

            if os.environ.get("MISTRAL_API_KEY"):
                client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))
            else:
                raise ValueError(
                    "MISTRAL_API_KEY is not set. "
                    "Set it with `export MISTRAL_API_KEY=<your-api-key>`."
                )

            if async_client:
                return from_mistral(client, model=model_name, use_async=True, **kwargs)
            else:
                return from_mistral(client, model=model_name, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The mistralai package is required to use the Mistral provider. "
                "Install it with `pip install mistralai`."
            )
            raise import_err from None

    elif provider == "cohere":
        try:
            import cohere
            from instructor import from_cohere

            client = cohere.AsyncClient() if async_client else cohere.Client()
            return from_cohere(client, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The cohere package is required to use the Cohere provider. "
                "Install it with `pip install cohere`."
            )
            raise import_err from None

    elif provider == "perplexity":
        try:
            import openai
            from instructor import from_perplexity
            import os

            if os.environ.get("PERPLEXITY_API_KEY"):
                api_key = os.environ.get("PERPLEXITY_API_KEY")
            elif kwargs.get("api_key"):
                api_key = kwargs.get("api_key")
            else:
                raise ValueError(
                    "PERPLEXITY_API_KEY is not set. "
                    "Set it with `export PERPLEXITY_API_KEY=<your-api-key>` or pass it as a kwarg api_key=<your-api-key>"
                )

            client = (
                openai.AsyncOpenAI(
                    api_key=api_key, base_url="https://api.perplexity.ai"
                )
                if async_client
                else openai.OpenAI(
                    api_key=api_key, base_url="https://api.perplexity.ai"
                )
            )
            return from_perplexity(client, model=model_name, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The openai package is required to use the Perplexity provider. "
                "Install it with `pip install openai`."
            )
            raise import_err from None

    elif provider == "groq":
        try:
            import groq
            from instructor import from_groq

            client = groq.AsyncGroq() if async_client else groq.Groq()
            return from_groq(client, model=model_name, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The groq package is required to use the Groq provider. "
                "Install it with `pip install groq`."
            )
            raise import_err from None

    elif provider == "writer":
        try:
            from writerai import AsyncWriter, Writer
            from instructor import from_writer

            client = AsyncWriter() if async_client else Writer()
            return from_writer(client, model=model_name, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The writerai package is required to use the Writer provider. "
                "Install it with `pip install writer-sdk`."
            )
            raise import_err from None

    elif provider == "bedrock":
        try:
            import boto3
            from instructor import from_bedrock

            client = boto3.client("bedrock-runtime")
            return from_bedrock(client, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The boto3 package is required to use the AWS Bedrock provider. "
                "Install it with `pip install boto3`."
            )
            raise import_err from None

    elif provider == "cerebras":
        try:
            from cerebras.cloud.sdk import AsyncCerebras, Cerebras
            from instructor import from_cerebras

            client = AsyncCerebras() if async_client else Cerebras()
            return from_cerebras(client, model=model_name, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The cerebras package is required to use the Cerebras provider. "
                "Install it with `pip install cerebras`."
            )
            raise import_err from None

    elif provider == "fireworks":
        try:
            from fireworks.client import AsyncFireworks, Fireworks
            from instructor import from_fireworks

            client = AsyncFireworks() if async_client else Fireworks()
            return from_fireworks(client, model=model_name, **kwargs)
        except ImportError:
            import_err = ImportError(
                "The fireworks-ai package is required to use the Fireworks provider. "
                "Install it with `pip install fireworks-ai`."
            )
            raise import_err from None

    elif provider == "vertexai":
        warnings.warn(
            "The 'vertexai' provider is deprecated. Use 'google' provider with vertexai=True instead. "
            "Example: instructor.from_provider('google/gemini-pro', vertexai=True)",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            import google.genai as genai  # type: ignore
            from instructor import from_genai
            import os

            # Get project and location from kwargs or environment
            project = kwargs.pop("project", os.environ.get("GOOGLE_CLOUD_PROJECT"))
            location = kwargs.pop(
                "location", os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
            )

            if not project:
                raise ValueError(
                    "Project ID is required for Vertex AI. "
                    "Set it with `export GOOGLE_CLOUD_PROJECT=<your-project-id>` "
                    "or pass it as kwarg project=<your-project-id>"
                )

            client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
                **kwargs,
            )  # type: ignore
            kwargs["model"] = model_name  # Pass model as part of kwargs
            if async_client:
                return from_genai(client, use_async=True, **kwargs)  # type: ignore
            else:
                return from_genai(client, **kwargs)  # type: ignore
        except ImportError:
            import_err = ImportError(
                "The google-genai package is required to use the VertexAI provider. "
                "Install it with `pip install google-genai`."
            )
            raise import_err from None

    elif provider == "generative-ai":
        warnings.warn(
            "The 'generative-ai' provider is deprecated. Use 'google' provider instead. "
            "Example: instructor.from_provider('google/gemini-pro')",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            from google import genai
            from instructor import from_genai
            import os

            # Get API key from kwargs or environment
            api_key = kwargs.pop("api_key", os.environ.get("GOOGLE_API_KEY"))

            client = genai.Client(vertexai=False, api_key=api_key)
            if async_client:
                return from_genai(client, use_async=True, model=model_name, **kwargs)  # type: ignore
            else:
                return from_genai(client, model=model_name, **kwargs)  # type: ignore
        except ImportError:
            import_err = ImportError(
                "The google-genai package is required to use the Google GenAI provider. "
                "Install it with `pip install google-genai`."
            )
            raise import_err from None

    elif provider == "ollama":
        try:
            import openai
            from instructor import from_openai

            # Get base_url from kwargs or use default
            base_url = kwargs.pop("base_url", "http://localhost:11434/v1")
            api_key = kwargs.pop("api_key", "ollama")  # required but unused

            client = (
                openai.AsyncOpenAI(base_url=base_url, api_key=api_key)
                if async_client
                else openai.OpenAI(base_url=base_url, api_key=api_key)
            )

            # Models that support function calling (tools mode)
            tool_capable_models = {
                "llama3.1",
                "llama3.2",
                "llama4",
                "mistral-nemo",
                "firefunction-v2",
                "command-r-plus",
                "qwen2.5",
                "qwen2.5-coder",
                "qwen3",
                "devstral",
            }

            # Check if model supports tools by looking at model name
            supports_tools = any(
                capable_model in model_name.lower()
                for capable_model in tool_capable_models
            )

            default_mode = (
                instructor.Mode.TOOLS if supports_tools else instructor.Mode.JSON
            )

            return from_openai(
                client,
                model=model_name,
                mode=mode if mode else default_mode,
                **kwargs,
            )
        except ImportError:
            from instructor.exceptions import ConfigurationError

            raise ConfigurationError(
                "The openai package is required to use the Ollama provider. "
                "Install it with `pip install openai`."
            ) from None

    elif provider == "xai":
        try:
            from xai_sdk.sync.client import Client as SyncClient
            from xai_sdk.aio.client import Client as AsyncClient
            from instructor import from_xai

            client = AsyncClient() if async_client else SyncClient()
            return from_xai(
                client,
                mode=mode if mode else instructor.Mode.JSON,
                model=model_name,
                **kwargs,
            )
        except ImportError:
            from instructor.exceptions import ConfigurationError

            raise ConfigurationError(
                "The xai-sdk package is required to use the xAI provider. "
                "Install it with `pip install xai-sdk`."
            ) from None

    else:
        from instructor.exceptions import ConfigurationError

        raise ConfigurationError(
            f"Unsupported provider: {provider}. "
            f"Supported providers are: {supported_providers}"
        )
