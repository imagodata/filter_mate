# -*- coding: utf-8 -*-
"""What FilterMate asks of a segmentation model.

FilterMate ships no model, no runtime and downloads nothing: a separate plugin
provides this interface (see ``adapters/qgis/coverage_layers/segmentation.py``).
"""
from typing import Any, Optional, Protocol, Sequence, Tuple, runtime_checkable


@runtime_checkable
class SegmentationProvider(Protocol):
    """A promptable segmentation model working on square RGB images."""

    #: Side, in pixels, of the images given to :meth:`embed`.
    input_size: int

    def embed(self, rgb: Any) -> Any:
        """Encode an image. Called from a worker thread.

        Args:
            rgb: ``input_size`` x ``input_size`` x 3 uint8 numpy array.

        Returns:
            An opaque value given back to :meth:`predict`.
        """

    def predict(self, embedding: Any, points: Sequence[Tuple[float, float]], labels: Sequence[int],
                box: Optional[Tuple[float, float, float, float]]) -> Tuple[Any, float]:
        """Mask of the object designated by the prompts. Called from the main thread.

        Args:
            embedding: A result of :meth:`embed`.
            points: ``(column, row)`` in pixels of the image embedded.
            labels: 1 for a point on the object, 0 for a point off it, one per point.
            box: ``(column0, row0, column1, row1)`` around the object, None without one.

        Returns:
            ``(mask, score)``: an ``input_size`` x ``input_size`` boolean numpy
            array and the confidence the model gives it.
        """
