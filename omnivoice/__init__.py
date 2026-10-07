import warnings
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

warnings.filterwarnings("ignore", module="torchaudio")
warnings.filterwarnings(
    "ignore",
    category=SyntaxWarning,
    message="invalid escape sequence",
    module="pydub.utils",
)
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="torch.distributed.algorithms.ddp_comm_hooks",
)

try:
    __version__ = version("omnivoice")
except PackageNotFoundError:
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from omnivoice.models.omnivoice import (
        OmniVoice,
        OmniVoiceConfig,
        OmniVoiceGenerationConfig,
        VoiceClonePrompt,
    )

__all__ = [
    "OmniVoice",
    "OmniVoiceConfig",
    "OmniVoiceGenerationConfig",
    "VoiceClonePrompt",
]


def __getattr__(name: str):
    """Load the model implementation only when a public model class is used.

    This keeps lightweight utilities and the desktop UI importable before the
    optional runtime/model dependencies have been installed.
    """
    if name in __all__:
        from omnivoice.models import omnivoice as model_module

        value = getattr(model_module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
