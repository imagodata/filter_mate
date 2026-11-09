# -*- coding: utf-8 -*-
"""SAM 2.1 through onnxruntime: the provider FilterMate asks for (see ``core/ports/segmentation_port.py``)."""
import os
import threading
from typing import Any, Optional, Sequence, Tuple

import numpy as np

INPUT_SIZE = 1024
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
# Measured on an ortho window (2026-11-09): 1.1 s at 4 threads, 1.8 s at 24. More threads is slower.
MAX_THREADS = 4


def upsample(logits: Any, size: int) -> Any:
    """Bilinear enlargement of a square grid (pixel centres aligned, edges clamped), numpy only."""
    grid = np.asarray(logits, dtype=np.float32)
    source = grid.shape[0]
    positions = (np.arange(size, dtype=np.float32) + 0.5) * source / size - 0.5
    low = np.clip(np.floor(positions).astype(int), 0, source - 1)
    high = np.clip(low + 1, 0, source - 1)
    weight = np.clip(positions - low, 0.0, 1.0)
    rows = grid[low] * (1.0 - weight)[:, None] + grid[high] * weight[:, None]
    return rows[:, low] * (1.0 - weight)[None, :] + rows[:, high] * weight[None, :]


class SamOnnxProvider:
    """Encoder and decoder of a quantized SAM 2.1 export."""

    input_size = INPUT_SIZE

    def __init__(self, directory: str, threads: Optional[int] = None) -> None:
        """Nothing is loaded here: the models open at the first :meth:`embed`, in the worker thread."""
        self._directory = directory
        self._threads = threads or min(MAX_THREADS, os.cpu_count() or 1)
        self._lock = threading.Lock()
        self._encoder: Any = None
        self._decoder: Any = None

    def _open(self) -> None:
        """Open the two models, once.

        Raises:
            ImportError: Without onnxruntime.
            Exception: From onnxruntime, for files it cannot load (tried again at the next call).
        """
        with self._lock:
            if self._encoder is not None:
                return
            import onnxruntime
            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = self._threads
            options.inter_op_num_threads = 1
            providers = ['CPUExecutionProvider']
            decoder = onnxruntime.InferenceSession(
                os.path.join(self._directory, 'prompt_encoder_mask_decoder_quantized.onnx'), options, providers=providers)
            self._encoder = onnxruntime.InferenceSession(
                os.path.join(self._directory, 'vision_encoder_quantized.onnx'), options, providers=providers)
            self._decoder = decoder

    def embed(self, rgb: Any) -> Any:
        self._open()
        pixels = (np.asarray(rgb, dtype=np.float32) / 255.0 - MEAN) / STD
        outputs = self._encoder.run(None, {'pixel_values': pixels.transpose(2, 0, 1)[None]})
        return {f'image_embeddings.{index}': value for index, value in enumerate(outputs)}

    def predict(self, embedding: Any, points: Sequence[Tuple[float, float]], labels: Sequence[int],
                box: Optional[Tuple[float, float, float, float]]) -> Tuple[Any, float]:
        coordinates = [[float(x), float(y)] for x, y in points]
        kinds = [int(label) for label in labels]
        feeds = dict(embedding)
        feeds['input_points'] = (np.array([[coordinates]], dtype=np.float32) if coordinates
                                 else np.zeros((1, 1, 0, 2), dtype=np.float32))
        feeds['input_labels'] = (np.array([[kinds]], dtype=np.int64) if kinds
                                 else np.zeros((1, 1, 0), dtype=np.int64))
        feeds['input_boxes'] = (np.array([[box]], dtype=np.float32) if box is not None
                                else np.zeros((1, 0, 4), dtype=np.float32))
        scores, masks = self._decoder.run(['iou_scores', 'pred_masks'], feeds)
        best = int(np.argmax(scores[0, 0]))
        return upsample(masks[0, 0, best], self.input_size) > 0, float(scores[0, 0, best])
