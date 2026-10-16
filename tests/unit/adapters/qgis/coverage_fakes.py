# -*- coding: utf-8 -*-
"""Test helpers for the FilterMate 5 coverage engine (not a test module).

* :func:`load` imports ``adapters/qgis/coverage_layers`` modules under a
  private package name (their relative imports reach ``core``);
* :class:`FakeGeometry` / :class:`FakeRectangle` stand in for ``QgsGeometry``
  / ``QgsRectangle`` with OGR doing the geometry work (GEOS through GDAL), and
  :func:`install` puts them in the loaded modules.

Load it by path (``importlib``), the test folders are not importable packages.
"""
import importlib
import pathlib
import sys
import types

from osgeo import ogr

ROOT = pathlib.Path(__file__).resolve().parents[4]
PACKAGE = "fm_coverage_engine_test"


def load(module: str):
    """``adapters.qgis.coverage_layers.<module>`` (or a dotted path from the root) under :data:`PACKAGE`."""
    for name, path in (("", ROOT), (".core", ROOT / "core"), (".core.domain", ROOT / "core" / "domain"),
                       (".core.services", ROOT / "core" / "services"), (".core.export", ROOT / "core" / "export"),
                       (".adapters", ROOT / "adapters"), (".adapters.qgis", ROOT / "adapters" / "qgis"),
                       (".adapters.qgis.coverage_layers", ROOT / "adapters" / "qgis" / "coverage_layers")):
        if PACKAGE + name not in sys.modules:
            package = types.ModuleType(PACKAGE + name)
            package.__path__ = [str(path)]
            sys.modules[PACKAGE + name] = package
    dotted = module if "." in module else f"adapters.qgis.coverage_layers.{module}"
    # Classes deriving from QgsTask need a real base class (the conftest mock is MagicMock).
    core = sys.modules['qgis.core']
    saved = {name: getattr(core, name, None) for name in ('QgsTask', 'QgsFeedback', 'QgsRasterBlockFeedback')}
    core.QgsTask, core.QgsFeedback, core.QgsRasterBlockFeedback = FakeTask, FakeFeedback, FakeFeedback
    try:
        return importlib.import_module(f"{PACKAGE}.{dotted}")
    finally:
        for name, value in saved.items():
            setattr(core, name, value)


class FakeFeedback:
    def __init__(self):
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def isCanceled(self):
        return self.canceled


class FakeTask:
    """QgsTask: cancel() / isCanceled() / setProgress()."""

    CanCancel = 1

    def __init__(self, description='', flags=0):
        self.description = description
        self._canceled = False
        self.progress = 0.0

    def cancel(self):
        self._canceled = True

    def isCanceled(self):
        return self._canceled

    def setProgress(self, value):
        self.progress = value


class FakePoint:
    def __init__(self, x, y):
        self._x, self._y = float(x), float(y)

    def x(self):
        return self._x

    def y(self):
        return self._y


class FakeRectangle:
    """QgsRectangle: (xmin, ymin, xmax, ymax), a copy, or an empty one."""

    def __init__(self, *args):
        if len(args) == 4:
            self.x0, self.y0, self.x1, self.y1 = (float(v) for v in args)
        elif len(args) == 1 and isinstance(args[0], FakeRectangle):
            other = args[0]
            self.x0, self.y0, self.x1, self.y1 = other.x0, other.y0, other.x1, other.y1
        else:
            self.x0 = self.y0 = self.x1 = self.y1 = 0.0

    def xMinimum(self):
        return self.x0

    def yMinimum(self):
        return self.y0

    def xMaximum(self):
        return self.x1

    def yMaximum(self):
        return self.y1

    def width(self):
        return self.x1 - self.x0

    def height(self):
        return self.y1 - self.y0

    def center(self):
        return FakePoint((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def isEmpty(self):
        return self.x1 <= self.x0 or self.y1 <= self.y0

    def grow(self, delta):
        self.x0 -= delta
        self.y0 -= delta
        self.x1 += delta
        self.y1 += delta

    def intersects(self, other):
        return max(self.x0, other.x0) <= min(self.x1, other.x1) and max(self.y0, other.y0) <= min(self.y1, other.y1)

    def __repr__(self):
        return f"FakeRectangle({self.x0}, {self.y0}, {self.x1}, {self.y1})"


class FakeEngine:
    """QgsGeometryEngine of a FakeGeometry (``engine.<method>(target)``)."""

    def __init__(self, geometry):
        self._g = geometry._g

    def prepareGeometry(self):
        pass

    def intersects(self, other):
        return self._g.Intersects(other._g)

    def disjoint(self, other):
        return self._g.Disjoint(other._g)

    def within(self, other):
        return self._g.Within(other._g)

    def contains(self, other):
        return self._g.Contains(other._g)

    def touches(self, other):
        return self._g.Touches(other._g)

    def overlaps(self, other):
        return self._g.Overlaps(other._g)

    def crosses(self, other):
        return self._g.Crosses(other._g)

    def isEqual(self, other):
        return self._g.Equals(other._g)


class FakeGeometry:
    """QgsGeometry backed by an OGR geometry; a null one has none (``isNull``)."""

    def __init__(self, other=None, error=''):
        if isinstance(other, FakeGeometry):
            self._g = other._g.Clone() if other._g is not None else None
        else:
            self._g = other
        self._error = error

    @classmethod
    def fromWkt(cls, wkt):
        return cls(ogr.CreateGeometryFromWkt(wkt))

    @classmethod
    def fromRect(cls, rect):
        return cls.fromWkt(f"POLYGON(({rect.x0} {rect.y0},{rect.x1} {rect.y0},{rect.x1} {rect.y1},"
                           f"{rect.x0} {rect.y1},{rect.x0} {rect.y0}))")

    @staticmethod
    def unaryUnion(geometries):
        result = None
        for geometry in geometries:
            result = geometry._g.Clone() if result is None else result.Union(geometry._g)
        return FakeGeometry(result)

    @staticmethod
    def createGeometryEngine(geometry):
        return FakeEngine(geometry)

    def fromWkb(self, wkb):
        self._g = ogr.CreateGeometryFromWkb(wkb)

    def _op(self, name, other):
        if self._g is None or other._g is None:
            return FakeGeometry(None)  # QgsGeometry: a null operand gives a null result, no error
        result = getattr(self._g, name)(other._g)
        if result is None:
            return FakeGeometry(None, error=f"{name} failed")
        return FakeGeometry(result)

    def intersection(self, other):
        return self._op('Intersection', other)

    def difference(self, other):
        return self._op('Difference', other)

    def combine(self, other):
        return self._op('Union', other)

    def symDifference(self, other):
        return self._op('SymDifference', other)

    def isNull(self):
        return self._g is None

    def isEmpty(self):
        return self._g is None or self._g.IsEmpty()

    def lastError(self):
        return self._error

    def asWkt(self):
        return self._g.ExportToWkt() if self._g is not None else ''

    def area(self):
        return self._g.GetArea() if self._g is not None else 0.0

    def boundingBox(self):
        if self.isEmpty():
            return FakeRectangle()
        x0, x1, y0, y1 = self._g.GetEnvelope()
        return FakeRectangle(x0, y0, x1, y1)

    def isGeosValid(self):
        return self._g.IsValid()

    def makeValid(self):
        return FakeGeometry(self._g.MakeValid())

    def isMultipart(self):
        return ogr.GT_Flatten(self._g.GetGeometryType()) in (ogr.wkbMultiPolygon, ogr.wkbMultiLineString,
                                                             ogr.wkbMultiPoint, ogr.wkbGeometryCollection)

    def asGeometryCollection(self):
        return [FakeGeometry(self._g.GetGeometryRef(i).Clone()) for i in range(self._g.GetGeometryCount())]

    def buffer(self, distance, segments, *args):
        return FakeGeometry(self._g.Buffer(distance, segments))

    def simplify(self, tolerance):
        return FakeGeometry(self._g.SimplifyPreserveTopology(tolerance))

    def centroid(self):
        return FakeGeometry(self._g.Centroid())

    def asPoint(self):
        return FakePoint(self._g.GetX(), self._g.GetY())

    def constGet(self):
        return self

    def clone(self):
        return FakeGeometry(self)

    def transform(self, transform):
        pass

    def __repr__(self):
        return f"FakeGeometry({self.asWkt()[:60]!r})"


class FakeProject:
    """QgsProject.instance(): the layers of a test (``FakeProject.layers``)."""

    layers = {}

    @classmethod
    def instance(cls):
        return cls()

    def transformContext(self):
        return None

    def mapLayer(self, layer_id):
        return self.layers.get(layer_id)


class FakeSpatialIndex:
    def __init__(self):
        self._boxes = []

    def addFeature(self, fid, bounds):
        self._boxes.append((fid, bounds))
        return True

    def intersects(self, rect):
        return [fid for fid, box in self._boxes if box.intersects(rect)]


def _epsg_wkt(authid):
    """WKT of an EPSG code (GDAL), a placeholder for anything else."""
    from osgeo import osr
    srs = osr.SpatialReference()
    if authid.startswith('EPSG:'):
        try:
            if srs.ImportFromEPSG(int(authid[5:])) == 0:
                return srs.ExportToWkt()
        except (RuntimeError, ValueError):
            pass
    return f'LOCAL_CS["{authid}"]'


class FakeCrs:
    """QgsCoordinateReferenceSystem: equal when the authid is (a compound one has a horizontal part)."""

    def __init__(self, authid='', valid=True, geographic=False, horizontal=None, wkt=''):
        self._authid, self._valid, self._geographic = authid, valid, geographic
        self._horizontal, self._wkt = horizontal, wkt or (_epsg_wkt(authid) if valid else '')

    def isValid(self):
        return self._valid

    def isGeographic(self):
        return self._geographic

    def authid(self):
        return self._authid

    def description(self):
        return self._authid

    def toWkt(self):
        return self._wkt

    def horizontalCrs(self):
        return self._horizontal if self._horizontal is not None else self

    def __eq__(self, other):
        return isinstance(other, FakeCrs) and (self._authid, self._valid) == (other._authid, other._valid)

    def __hash__(self):
        return hash(self._authid)


def install(monkeypatch, *modules):
    """Put the fakes in ``modules`` (and ``qgis.core`` for the names imported in functions)."""
    core = sys.modules['qgis.core']
    for name, fake in (('QgsGeometry', FakeGeometry), ('QgsRectangle', FakeRectangle),
                       ('QgsSpatialIndex', FakeSpatialIndex), ('QgsTask', FakeTask), ('QgsFeedback', FakeFeedback),
                       ('QgsRasterBlockFeedback', FakeFeedback)):
        monkeypatch.setattr(core, name, fake, raising=False)
        for module in modules:
            if hasattr(module, name):
                monkeypatch.setattr(module, name, fake)
    FakeProject.layers = {}
    for module in modules:
        if hasattr(module, 'QgsProject'):
            monkeypatch.setattr(module, 'QgsProject', FakeProject)
        if hasattr(module, 'QgsCoordinateReferenceSystem'):
            monkeypatch.setattr(module, 'QgsCoordinateReferenceSystem', lambda crs=None: crs if crs is not None else FakeCrs())
