"""SDXL-Turbo wrapper — single-step text-to-image at ~5–15 fps on M3 Max MPS.

The model itself is huge (~5GB) and slow to download on first use; everything
behind `load()` is lazy so plain `from apophenia.ai import ...` doesn't
trigger anything beyond module import.

Design notes:
  * SDXL-Turbo is distilled to single-step inference. We pass
    `num_inference_steps=1` and `guidance_scale=0.0` per the model card.
    Anything else degrades quality without a quality bump.
  * Native resolution is 512x512; 1024 is supported but ~3x slower and
    not worth it for a real-time visual where the compositor scales
    everything anyway. Default to 512.
  * MPS / CUDA / CPU autodetect mirrors `ClapEncoder` so the same install
    works on M-series laptops, Linux GPU desktops, and CI.
  * The generator is intentionally stateless between calls — a fresh
    `torch.Generator` is built per inference so seeds are deterministic.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import torch

logger = logging.getLogger(__name__)

SDXL_TURBO_MODEL_NAME = "stabilityai/sdxl-turbo"
DEFAULT_RESOLUTION = 512
DEFAULT_NUM_STEPS = 1
DEFAULT_GUIDANCE = 0.0


def _pick_device() -> torch.device:
    """MPS on Apple Silicon, CUDA on NVIDIA, CPU as fallback."""
    import torch

    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class SDXLTurboGenerator:
    """Lazy-loaded SDXL-Turbo image generator.

    Construct cheaply, call `load()` once before the first `generate()`,
    re-use the same instance for every subsequent call. The pipeline lives
    on `_pipe`; we expose `model_name` and `device` for telemetry.
    """

    def __init__(
        self,
        model_name: str = SDXL_TURBO_MODEL_NAME,
        resolution: int = DEFAULT_RESOLUTION,
    ) -> None:
        self.model_name = model_name
        self.resolution = resolution
        self.device: torch.device | None = None
        self._pipe: Any = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        """Download (if needed) and load the SDXL-Turbo pipeline.

        Blocks for ~5–60s on first call depending on download speed; the
        weights cache to `~/.cache/huggingface` after that and subsequent
        loads take ~3s on M3 Max.
        """
        if self._pipe is not None:
            return  # idempotent
        import torch
        from diffusers import AutoPipelineForText2Image

        self.device = _pick_device()
        # fp16 on CUDA, fp32 elsewhere — MPS fp16 has periodic correctness
        # issues with some diffusers versions; fp32 is safer and the M3
        # Max has plenty of unified memory.
        dtype: torch.dtype
        if self.device.type == "cuda":
            dtype = torch.float16
            variant = "fp16"
        else:
            dtype = torch.float32
            variant = None

        logger.info(
            "loading SDXL-Turbo (%s) on %s with dtype=%s",
            self.model_name,
            self.device,
            dtype,
        )
        t0 = time.monotonic()
        load_kwargs: dict[str, Any] = {
            "torch_dtype": dtype,
            "use_safetensors": True,
        }
        if variant is not None:
            load_kwargs["variant"] = variant
        try:
            self._pipe = AutoPipelineForText2Image.from_pretrained(  # type: ignore[no-untyped-call]
                self.model_name,
                **load_kwargs,
            )
        except Exception:
            # variant may be missing on some mirrors; retry without it.
            load_kwargs.pop("variant", None)
            self._pipe = AutoPipelineForText2Image.from_pretrained(  # type: ignore[no-untyped-call]
                self.model_name,
                **load_kwargs,
            )
        self._pipe = self._pipe.to(self.device)
        # Disable progress bars so the terminal stays clean.
        try:
            self._pipe.set_progress_bar_config(disable=True)
        except Exception:  # noqa: BLE001 — older diffusers versions miss this
            pass
        logger.info(
            "SDXL-Turbo ready (%.2fs to load)",
            time.monotonic() - t0,
        )

    # ------------------------------------------------------------------ #
    # Inference
    # ------------------------------------------------------------------ #

    def generate(
        self,
        prompt: str,
        seed: int | None = None,
        num_inference_steps: int = DEFAULT_NUM_STEPS,
        guidance_scale: float = DEFAULT_GUIDANCE,
        resolution: int | None = None,
    ) -> np.ndarray:
        """Run one inference and return RGB uint8 (H, W, 3).

        `seed=None` picks a random seed each call; pass an int for repeatable
        output. `num_inference_steps` defaults to 1 (Turbo is distilled to
        single-step); higher values waste compute. `guidance_scale=0.0` per
        the model card — Turbo's CFG is baked in.
        """
        import torch

        if self._pipe is None:
            raise RuntimeError("call load() before generate()")
        assert self.device is not None  # set by load()

        if seed is None:
            # 32-bit unsigned random seed; fits comfortably in torch.Generator.
            seed = int(np.random.randint(0, 2**31 - 1))
        gen = torch.Generator(device=self.device).manual_seed(seed)

        side = resolution or self.resolution

        result = self._pipe(
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=side,
            height=side,
            generator=gen,
            output_type="np",  # returns float32 in [0, 1]
        )
        # Diffusers returns a StableDiffusionPipelineOutput-like obj with
        # .images of shape (B, H, W, 3) float32.
        images = result.images if hasattr(result, "images") else result["images"]
        img: np.ndarray = images[0]
        if img.dtype != np.uint8:
            img = (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        return img
