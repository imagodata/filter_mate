"""Temporary raster band renderers, built from statistics computed in a worker."""
import math

from qgis.core import QgsContrastEnhancement, QgsMultiBandColorRenderer, QgsProject, QgsSingleBandGrayRenderer

from .raster_adapter import _address


class RasterBandDisplay:
    """Keep the layer style intact while exploring grey or RGB band combinations.

    No provider values are read here. The caller supplies sampled band ranges
    and clears the selection preview and range link before replacing a renderer.
    """

    def __init__(self):
        self._original = None
        self._layer_id = None
        self._renderer_address = None
        self._project = None

    def apply(self, layer, bands, ranges):
        """Install a grey band or three RGB channels, preserving alpha and opacity."""
        if len(bands) not in (1, 3) or not any(band > 0 for band in bands):
            return False
        provider = layer.dataProvider()
        if any(band > layer.bandCount() or band == 0 or band < -1 for band in bands):
            return False
        current = layer.renderer()
        if current is None:
            return False
        original = self._original
        if self._layer_id != layer.id() or self._renderer_address != _address(current):
            original = current.clone()  # also respect a style edited since the last display
        renderer = (QgsSingleBandGrayRenderer(provider, bands[0]) if len(bands) == 1 else
                    QgsMultiBandColorRenderer(provider, *bands))
        setters = ([renderer.setContrastEnhancement] if len(bands) == 1 else
                   [renderer.setRedContrastEnhancement, renderer.setGreenContrastEnhancement, renderer.setBlueContrastEnhancement])
        for band, setter in zip(bands, setters):
            if band < 1:
                continue
            low, high = ranges.get(band, (None, None))
            if low is None or high is None or not math.isfinite(low) or not math.isfinite(high):
                return False
            if low == high:
                low, high = low - 0.5, high + 0.5
            enhancement = QgsContrastEnhancement(provider.dataType(band))
            enhancement.setMinimumValue(low)
            enhancement.setMaximumValue(high)
            enhancement.setContrastEnhancementAlgorithm(QgsContrastEnhancement.ContrastEnhancementAlgorithm.StretchToMinimumMaximum)
            setter(enhancement)
        renderer.setOpacity(original.opacity())
        renderer.setAlphaBand(current.alphaBand())
        if hasattr(renderer, 'setNodataColor') and hasattr(original, 'nodataColor'):
            renderer.setNodataColor(original.nodataColor())
        self._original = original
        self._layer_id = layer.id()
        layer.setRenderer(renderer)
        self._renderer_address = _address(layer.renderer())
        if self._project is None:
            self._project = QgsProject.instance()
            self._project.writeMapLayer.connect(self._write_original)
        layer.triggerRepaint()
        return True

    def restore(self, layer):
        """Restore the saved style unless the user installed another renderer."""
        try:
            if (self._original is not None and layer is not None and layer.id() == self._layer_id
                    and layer.renderer() is not None and _address(layer.renderer()) == self._renderer_address):
                restored = self._original.clone()
                restored.setInput(layer.dataProvider())
                restored.setAlphaBand(layer.renderer().alphaBand())
                layer.setRenderer(restored)
                layer.triggerRepaint()
        finally:
            self._original = None
            self._layer_id = self._renderer_address = None
            if self._project is not None:
                try:
                    self._project.writeMapLayer.disconnect(self._write_original)
                except (RuntimeError, TypeError):
                    pass
                self._project = None

    def _write_original(self, layer, element, document):
        """Saving a project retains the original style rather than this temporary view."""
        if (self._original is None or layer.id() != self._layer_id or layer.renderer() is None
                or _address(layer.renderer()) != self._renderer_address):
            return
        pipe = element.firstChildElement('pipe')
        written = pipe.firstChildElement('rasterrenderer')
        if written.isNull():
            return
        self._original.writeXml(document, pipe)
        original = pipe.lastChildElement('rasterrenderer')
        if written.hasAttribute('alphaBand'):
            original.setAttribute('alphaBand', written.attribute('alphaBand'))
        pipe.insertBefore(original, written)
        pipe.removeChild(written)
